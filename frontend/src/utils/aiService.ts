import axios, { AxiosHeaders, AxiosResponse } from 'axios';
import type { ChatMessage, FormattedMessage, MessageHistoryItem } from '@/types';
import type { ApiError } from '@/types/chat';
import type {
  ClaudeStreamChunk,
  ModelStatusResponse,
  ModelsListResponse,
  OpenAIStreamChunk,
  ParsedStreamEvent,
  SearchSource,
  StreamErrorChunk,
} from '@/types/api';
import { isStreamEvent } from '@/types/api';
import { extractErrorMessage, isApiError } from './helpers';
import { logger } from './logger';

/** 流式响应的统一返回 shape：data 是 SSE 解析后的 Uint8Array 可读流 */
interface StreamSendResult {
  data: ReadableStream<Uint8Array>;
  status: number;
  headers: unknown;
}

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
});

const internalApiToken = import.meta.env.VITE_INTERNAL_API_TOKEN as string | undefined;

api.interceptors.request.use((config) => {
  if (internalApiToken === undefined || internalApiToken === '') {
    return config;
  }

  config.headers = AxiosHeaders.from(config.headers);
  config.headers.set('Authorization', `Bearer ${internalApiToken}`);

  return config;
});

interface SendMessageParams {
    model: string;
    messages: MessageHistoryItem[] | ChatMessage[];
    enable_search?: boolean;
}

// 控制选项，与业务参数分离
interface SendMessageOptions {
    signal?: AbortSignal;
}

// 添加新的错误处理拦截器
api.interceptors.response.use(
  response => response,
  (error: unknown) => {
    // 使用类型守卫检查ApiError
    if (error !== null && typeof error === 'object' && 'response' in error) {
      const apiError = error as ApiError;
      // 特别处理422错误
      if (apiError.response && apiError.response.status === 422) {
        logger.error('请求参数验证失败:', apiError.response.data);
        // response.data.detail 已由 ApiError schema 描述为 string | Array<{msg,type}>
        const detail = apiError.response.data?.detail;
        apiError.validationErrors = Array.isArray(detail) ? detail : [];
      }
    }
    return Promise.reject(error instanceof Error ? error : new Error(String(error)));
  }
);

/**
 * 格式化消息历史，确保API兼容
 */
export function formatMessages(messages: ChatMessage[] | MessageHistoryItem[]): FormattedMessage[] {
  if (!Array.isArray(messages) || messages.length === 0) {
    logger.warn('formatMessages接收到空消息列表，这可能导致请求失败');
    return [];
  }

  // 空 content / 非字符串 content 直接过滤，**绝不**用 "内容为空" 字面 fallback——
  // 否则会把前端 placeholder assistant 污染到上游 provider 上下文。
  return messages
    .filter(msg => typeof msg.content === 'string' && msg.content.trim() !== '')
    .map(msg => ({
      role: msg.role,
      content: msg.content.trim()
    }));
}

export const aiService = {
  async checkModelConnection(model: string): Promise<AxiosResponse<ModelStatusResponse>> {
    return api.get<ModelStatusResponse>(`/ai/models/${model}/status`);
  },

  async getAvailableModels(): Promise<AxiosResponse<ModelsListResponse>> {
    return api.get<ModelsListResponse>('/ai/models');
  },

  async sendMessageStream(params: SendMessageParams, options: SendMessageOptions = {}): Promise<StreamSendResult> {
    // 确保消息格式正确
    const formattedParams = {
      ...params,
      messages: formatMessages(params.messages),
      stream: true
    };

    try {
      logger.debug('发送流式请求:', {
        model: formattedParams.model,
        messageCount: formattedParams.messages.length
      });

      // 用 fetch + 原生 response.body 拿真流式响应。axios 浏览器端基于 XHR，
      // responseType:'text' 必须等响应完整结束才返回字符串——这会让上游 SSE 的
      // 60+ thinking event 在前端被批处理成"45 秒零渲染→整段突现"。fetch 的
      // response.body 是真 ReadableStream<Uint8Array>，按 TCP 节奏到达即可读。
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream'
      };
      if (internalApiToken !== undefined && internalApiToken !== '') {
        headers.Authorization = `Bearer ${internalApiToken}`;
      }
      const fetchInit: RequestInit = {
        method: 'POST',
        headers,
        body: JSON.stringify(formattedParams)
      };
      if (options.signal !== undefined) {
        fetchInit.signal = options.signal;
      }
      const response = await fetch('/api/ai/chat/stream', fetchInit);
      if (!response.ok || response.body === null) {
        // 走外层 catch 的 errorStream 兜底；构造 ApiError 形态保持日志/UI 一致
        const text = await response.text().catch(() => '');
        const err = new Error(`HTTP ${response.status}: ${text === '' ? response.statusText : text}`) as ApiError;
        err.response = {
          data: text === '' ? { detail: response.statusText } : { detail: text },
          status: response.status,
          statusText: response.statusText
        };
        throw err;
      }
      const responseBody = response.body;

      // 创建一个可读流，用于处理SSE格式的数据
      const stream = new ReadableStream<Uint8Array>({
        async start(controller): Promise<void> {
          const encoder = new TextEncoder();

          try {
            // 一行一条 JSON 事件输出，messaging.ts 用 buffer+split('\n') 解析。
            // 取代历史上的"层间 magic string"做法（前缀 🤔思考: / 错误:），
            // 让事件类型回到结构化字段，避免 in-band signaling 与内容前缀冲突。
            const enqueueEvent = (type: 'thinking' | 'content' | 'error', text: string): void => {
              if (text === '') { return; }
              const payload: ParsedStreamEvent = { type, text };
              controller.enqueue(encoder.encode(`${JSON.stringify(payload)}\n`));
            };

            // search_results 走独立 enqueue：sources/searchFailed 与 text 字段形状不同
            const enqueueSearchResults = (sources: SearchSource[], searchFailed: boolean): void => {
              const payload: ParsedStreamEvent = {
                type: 'search_results',
                sources,
                searchFailed,
              };
              controller.enqueue(encoder.encode(`${JSON.stringify(payload)}\n`));
            };

            // SSE 行驱动状态机：currentEvent 在 event: 行更新，dataBuffer 在 data: 行累积，
            // 空行触发 flushEvent 按 currentEvent 派发。修复 P2.6 b8b88f1 统一 SSE 契约后
            // 前端误把 raw `event: thinking` 当 content 输出的回归。
            let currentEvent: string | null = null;
            let dataBuffer: string[] = [];

            const flushEvent = (): void => {
              if (dataBuffer.length === 0) {
                currentEvent = null;
                return;
              }
              const dataText = dataBuffer.join('\n');
              const eventType = currentEvent;
              dataBuffer = [];
              currentEvent = null;

              if (dataText === '[DONE]') {
                logger.debug('接收到流结束标记');
                return;
              }

              try {
                if (!dataText.startsWith('{') && !dataText.startsWith('[')) {
                  // 非 JSON 兜底文本：按 content 包装下行
                  if (!dataText.includes('[DONE]')) {
                    enqueueEvent('content', dataText);
                  }
                  return;
                }

                const parsed: unknown = JSON.parse(dataText);

                if (eventType === 'thinking') {
                  const thinking = (parsed as { thinking?: string }).thinking;
                  if (thinking !== undefined && thinking !== '') {
                    enqueueEvent('thinking', thinking);
                  }
                  return;
                }
                if (eventType === 'content') {
                  const content = (parsed as { content?: string }).content;
                  if (content !== undefined && content !== '') {
                    enqueueEvent('content', content);
                  }
                  return;
                }
                if (eventType === 'error') {
                  const errVal = (parsed as { error?: unknown }).error;
                  if (errVal !== undefined) {
                    const errText = typeof errVal === 'string' ? errVal : JSON.stringify(errVal);
                    enqueueEvent('error', errText);
                  }
                  return;
                }
                if (eventType === 'done' || eventType === 'finish') {
                  logger.debug('流式响应完成');
                  return;
                }
                if (eventType === 'search_results') {
                  // T2.4：识别后向 messaging.ts 派发结构化事件
                  const raw = parsed as { sources?: unknown; search_failed?: unknown };
                  const sources: SearchSource[] = Array.isArray(raw.sources)
                    ? raw.sources
                      .filter((item): item is { title: string; url: string; description?: string } => {
                        if (item === null || typeof item !== 'object') { return false; }
                        const obj = item as { title?: unknown; url?: unknown };
                        return typeof obj.title === 'string' && typeof obj.url === 'string';
                      })
                      .map((item) => ({
                        title: item.title,
                        url: item.url,
                        description: typeof item.description === 'string' ? item.description : '',
                      }))
                    : [];
                  const searchFailed = raw.search_failed === true;
                  logger.info('收到联网搜索结果事件', { count: sources.length, searchFailed });
                  enqueueSearchResults(sources, searchFailed);
                  return;
                }

                // 兼容：currentEvent === null 时按 isStreamEvent 形态识别
                if (isStreamEvent(parsed)) {
                  if (parsed.type === 'thinking' && parsed.data.thinking !== undefined && parsed.data.thinking !== '') {
                    enqueueEvent('thinking', parsed.data.thinking);
                    return;
                  }
                  if (parsed.type === 'content' && parsed.data.content !== undefined && parsed.data.content !== '') {
                    enqueueEvent('content', parsed.data.content);
                    return;
                  }
                  if (parsed.type === 'error' && parsed.data.error !== undefined && parsed.data.error !== '') {
                    enqueueEvent('error', parsed.data.error);
                    return;
                  }
                  if (parsed.type === 'done' || parsed.type === 'finish') {
                    return;
                  }
                }

                // 兜底：OpenAI / Claude / Deepseek 原始 chunk（未走统一封装的极端场景）
                let content = '';
                let thinking = '';

                const claude = parsed as ClaudeStreamChunk;
                if (claude.event === 'content_block_delta' && claude.data?.delta?.text !== undefined && claude.data.delta.text !== '') {
                  content = claude.data.delta.text;
                } else {
                  const oai = parsed as OpenAIStreamChunk;
                  if (oai.choices && oai.choices.length > 0) {
                    const delta = oai.choices[0]?.delta;
                    if (delta?.content !== undefined && delta.content !== '') {
                      content = delta.content;
                    }
                    if (delta?.reasoning_content !== undefined && delta.reasoning_content !== '') {
                      thinking = delta.reasoning_content;
                    }
                  } else {
                    const err = parsed as StreamErrorChunk;
                    if (err.error !== undefined) {
                      const errText = typeof err.error === 'string' ? err.error : JSON.stringify(err.error);
                      enqueueEvent('error', errText);
                      return;
                    }
                  }
                }

                if (thinking !== '') {
                  enqueueEvent('thinking', thinking);
                }
                if (content !== '') {
                  enqueueEvent('content', content);
                }
              } catch (e) {
                logger.debug('SSE data 解析失败，按 content 兜底:', e);
                if (dataText && !dataText.includes('[DONE]')) {
                  enqueueEvent('content', dataText);
                }
              }
            };

            // fetch 原生流：边接收 chunk 边解码、按 \n 切行、按 SSE 状态机派发
            // (currentEvent / dataBuffer / flushEvent)。不再攒齐完整字符串才处理，
            // 上游每个 thinking / content 事件到达即向下传播，让 messaging.ts 那
            // 端的 reader 真正按时间分布拿到事件，恢复"逐字增长"的流式观感。
            const reader = responseBody.getReader();
            const decoder = new TextDecoder('utf-8');
            let lineBuffer = '';

            const processLine = (rawLine: string): void => {
              const line = rawLine.replace(/\r$/, '');
              if (line === '') {
                flushEvent();
                return;
              }
              if (line.startsWith(':')) { return; }
              if (line.startsWith('event:')) {
                currentEvent = line.slice(6).trim();
                return;
              }
              if (line.startsWith('data:')) {
                dataBuffer.push(line.slice(5).replace(/^ /, ''));
                return;
              }
            };

            for (;;) {
              const { value, done } = await reader.read();
              if (done) { break; }
              lineBuffer += decoder.decode(value, { stream: true });
              const lines = lineBuffer.split('\n');
              lineBuffer = lines.pop() ?? '';
              for (const rawLine of lines) {
                processLine(rawLine);
              }
            }
            // flush decoder 跨字节字符尾部 + 兜底处理末尾不完整行
            lineBuffer += decoder.decode();
            if (lineBuffer !== '') {
              for (const rawLine of lineBuffer.split('\n')) {
                processLine(rawLine);
              }
            }
            // 部分上游不发尾随空行，兜底 flush
            flushEvent();

            // 处理完成后关闭控制器
            controller.close();

          } catch (error: unknown) {
            logger.error('处理流数据时出错:', error);
            controller.error(error);
          }
        }
      });

      return {
        data: stream,
        status: response.status,
        headers: response.headers
      };
    } catch (error: unknown) {
      logger.error('流式请求失败:', error);

      // 错误信息也转换为流返回
      const errorStream = new ReadableStream<Uint8Array>({
        start(controller): void {
          const encoder = new TextEncoder();
          let errorText = '无法连接到服务器';

          // 使用类型安全的错误处理
          if (isApiError(error)) {
            errorText = `服务器返回${error.response.status}错误`;
            if (error.response.data) {
              // data 是结构化对象（含 detail 等字段），用 JSON.stringify 避免 [object Object]
              errorText += ` - ${JSON.stringify(error.response.data)}`;
            }
          } else {
            errorText = extractErrorMessage(error);
          }

          // 统一 JSON 事件格式（与主流 enqueueEvent 对齐），由 messaging.ts 解析后渲染
          const payload: ParsedStreamEvent = { type: 'error', text: errorText };
          controller.enqueue(encoder.encode(`${JSON.stringify(payload)}\n`));
          controller.close();
        }
      });

      return {
        data: errorStream,
        status: isApiError(error) ? error.response.status : 500,
        headers: {}
      };
    }
  },

};
