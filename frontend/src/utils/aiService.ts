import axios, { AxiosHeaders, AxiosResponse } from 'axios';
import type { ChatMessage, FormattedMessage, MessageHistoryItem } from '@/types';
import type { ApiError } from '@/types/chat';
import type {
  ChatCompletionResponse,
  ClaudeStreamChunk,
  ModelStatusResponse,
  ModelsListResponse,
  OpenAIStreamChunk,
  ParsedStreamEvent,
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
    stream?: boolean;
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

      // 使用不同的方式处理流式响应；signal 为 undefined 时不放进 config 以满足
      // axios GenericAbortSignal 的非可空契约（exactOptionalPropertyTypes 严格）。
      const axiosConfig: Parameters<typeof api.post>[2] = {
        responseType: 'text',
        timeout: 120000
      };
      if (options.signal !== undefined) {
        axiosConfig.signal = options.signal;
      }
      const response = await api.post<string>('/ai/chat/stream', formattedParams, axiosConfig);

      // 创建一个可读流，用于处理SSE格式的数据
      const stream = new ReadableStream<Uint8Array>({
        start(controller): void {
          const encoder = new TextEncoder();

          try {
            // 一行一条 JSON 事件输出，messaging.ts 用 buffer+split('\n') 解析。
            // 取代历史上的"层间 magic string"做法（前缀 🤔思考: / 错误:），
            // 让事件类型回到结构化字段，避免 in-band signaling 与内容前缀冲突。
            const enqueueEvent = (type: ParsedStreamEvent['type'], text: string): void => {
              if (text === '') { return; }
              const payload: ParsedStreamEvent = { type, text };
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
                  // T2.2：识别并 log；T2.4 接入 UI 卡片
                  const sources = (parsed as { sources?: unknown }).sources;
                  const searchFailed = (parsed as { search_failed?: unknown }).search_failed;
                  logger.info('收到联网搜索结果事件', {
                    count: Array.isArray(sources) ? sources.length : 0,
                    searchFailed,
                  });
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

            // 处理文本响应。api.post<string> 的泛型已保证 data 为 string。
            const textData = response.data;
            logger.debug('收到文本响应，长度：', textData.length);

            if (typeof textData !== 'string') {
              throw new Error(`响应数据类型意外：${typeof textData}`);
            }

            for (const rawLine of textData.split('\n')) {
              const line = rawLine.replace(/\r$/, '');
              if (line === '') {
                flushEvent();
                continue;
              }
              if (line.startsWith(':')) { continue; }
              if (line.startsWith('event:')) {
                currentEvent = line.slice(6).trim();
                continue;
              }
              if (line.startsWith('data:')) {
                dataBuffer.push(line.slice(5).replace(/^ /, ''));
                continue;
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

  async sendMessage(params: SendMessageParams): Promise<AxiosResponse<ChatCompletionResponse>> {
    // 确保消息格式正确
    const formattedParams = {
      ...params,
      messages: formatMessages(params.messages)
    };

    try {
      return api.post<ChatCompletionResponse>('/ai/chat', formattedParams);
    } catch (error: unknown) {
      logger.error('消息发送错误:', error);
      throw error;
    }
  },

  /**
     * 发送消息，带重试机制
     */
  async sendMessageWithRetry(params: SendMessageParams, maxRetries = 3): Promise<AxiosResponse<ChatCompletionResponse>> {
    // 参数验证
    if (!params.model) {
      const error = new Error('未指定模型参数');
      logger.error('发送消息失败:', error);
      throw error;
    }

    // 确保消息列表不为空
    if (!Array.isArray(params.messages) || params.messages.length === 0) {
      const error = new Error('消息列表不能为空');
      logger.error('发送消息失败:', error);
      throw error;
    }

    // 格式化消息
    const formattedMessages = formatMessages(params.messages);

    // 格式化后的消息列表不能为空
    if (formattedMessages.length === 0) {
      const error = new Error('格式化后的消息列表为空，无法发送请求');
      logger.error('发送消息失败:', error);
      throw error;
    }

    let retries = 0;
    let lastError = null;

    while (retries < maxRetries) {
      try {
        const formattedParams = {
          ...params,
          messages: formattedMessages
        };

        logger.debug(`发送聊天请求 (尝试 ${retries + 1}/${maxRetries}):`, {
          model: formattedParams.model,
          messageCount: formattedParams.messages.length
        });

        const response = await api.post<ChatCompletionResponse>('/ai/chat', formattedParams);

        // 验证响应结构：ChatCompletionResponse schema 已保证 response.data 是对象
        // 优先使用content字段，其次使用message.content结构
        if ((response.data.content === undefined || response.data.content === '')
            && response.data.message?.content !== undefined
            && response.data.message.content !== '') {
          response.data.content = response.data.message.content;
        }

        // 如果仍然没有content，记录响应并标记为错误
        if (response.data.content === undefined || response.data.content === '') {
          logger.error('响应中缺少content字段', response.data);
          throw new Error('响应格式异常：缺少内容');
        }

        return response;
      } catch (error: unknown) {
        lastError = error;

        // 记录详细错误信息
        if (axios.isAxiosError(error) && error.response) {
          const statusCode = error.response.status;
          const data: unknown = error.response.data;

          // 特别处理422错误，详细记录错误信息
          if (statusCode === 422) {
            logger.error('请求参数验证失败 (422错误):', {
              status: statusCode,
              data: data,
              params: {
                model: params.model,
                messageCount: params.messages.length,
                messagesPreview: params.messages.slice(0, 2).map(m => ({ role: m.role, contentLength: m.content.length }))
              }
            });

            // 如果是参数验证错误，不再重试
            throw error;
          }

          logger.error(`请求失败 (尝试 ${retries + 1}/${maxRetries}):`, {
            status: statusCode,
            data: data
          });
        } else {
          logger.error(`请求失败 (尝试 ${retries + 1}/${maxRetries}):`, error);
        }

        // 网络错误或服务器错误才重试
        if (!axios.isAxiosError(error) || !error.response || error.response.status >= 500) {
          retries++;
          if (retries < maxRetries) {
            // 延迟重试，随重试次数增加等待时间
            const delay = 1000 * retries;
            logger.debug(`等待 ${delay}ms 后重试...`);
            await new Promise(resolve => setTimeout(resolve, delay));
            continue;
          }
        }

        throw error;
      }
    }

    throw lastError;
  }
};
