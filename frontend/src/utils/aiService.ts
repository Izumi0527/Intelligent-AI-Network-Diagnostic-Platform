import axios, { AxiosHeaders, AxiosResponse } from 'axios';
import type { ChatMessage, FormattedMessage, MessageHistoryItem } from '@/types';
import type { ApiError } from '@/types/chat';
import type {
  ChatCompletionResponse,
  ClaudeStreamChunk,
  ModelStatusResponse,
  ModelsListResponse,
  OpenAIStreamChunk,
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
  // 安全检查：确保messages是非空数组
  if (!Array.isArray(messages) || messages.length === 0) {
    logger.warn('formatMessages接收到空消息列表，这可能导致请求失败');
    return [];
  }

  return messages.map(msg => {
    // 类型保证 msg 是对象，role 是 'user' | 'assistant' | 'system'，content 是 string；
    // 此处只做空内容兜底，不做运行时 null/类型检查（dead code）。
    const role = msg.role;
    // 确保content不为空或仅包含空白字符
    const content = msg.content && typeof msg.content === 'string'
      ? msg.content.trim()
      : '内容为空';

    // 只对用户消息警告空内容，助手消息在流式对话时可能初始为空
    if ((!msg.content || msg.content.trim() === '') && role === 'user') {
      logger.warn(`发现空内容用户消息，role=${role}`);
    }

    return {
      role,
      content
    };
  }).filter(msg => msg.content !== ''); // 过滤掉无效消息
}

export const aiService = {
  async checkModelConnection(model: string): Promise<AxiosResponse<ModelStatusResponse>> {
    return api.get<ModelStatusResponse>(`/ai/models/${model}/status`);
  },

  async getAvailableModels(): Promise<AxiosResponse<ModelsListResponse>> {
    return api.get<ModelsListResponse>('/ai/models');
  },

  async sendMessageStream(params: SendMessageParams): Promise<StreamSendResult> {
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

      // 使用不同的方式处理流式响应
      const response = await api.post<string>('/ai/chat/stream', formattedParams, {
        responseType: 'text', // 使用文本类型接收响应
        timeout: 120000 // 增加超时时间以处理长对话
      });

      // 创建一个可读流，用于处理SSE格式的数据
      const stream = new ReadableStream<Uint8Array>({
        start(controller): void {
          const encoder = new TextEncoder();

          try {
            // 处理单行SSE数据
            const processLine = (line: string): void => {
              if (line === 'data: [DONE]' || line === '[DONE]') {
                logger.debug('接收到流结束标记');
                return;
              }

              // 处理可能存在的多层嵌套data:前缀问题
              let contentLine = line;
              // 持续清除所有的data:前缀
              while (contentLine.startsWith('data:')) {
                contentLine = contentLine.substring(5).trim();
              }

              // 检查是否为空
              if (!contentLine) { return; }

              try {
                // 尝试解析为JSON
                if (contentLine.startsWith('{') || contentLine.startsWith('[')) {
                  const parsed: unknown = JSON.parse(contentLine);

                  // 优先处理后端返回的 StreamEvent 格式
                  if (isStreamEvent(parsed)) {
                    logger.debug(`[StreamEvent] 接收到事件类型: ${parsed.type}`, parsed.data);

                    if (parsed.type === 'thinking' && parsed.data.thinking !== undefined && parsed.data.thinking !== '') {
                      // 处理思考内容
                      const thinkingChunk = `🤔思考: ${parsed.data.thinking}`;
                      controller.enqueue(encoder.encode(thinkingChunk));
                      return;
                    } else if (parsed.type === 'content' && parsed.data.content !== undefined && parsed.data.content !== '') {
                      // 处理正常内容
                      const content = parsed.data.content;
                      if (content.length > 20) {
                        const chunkSize = Math.min(20, Math.ceil(content.length / 3));
                        for (let i = 0; i < content.length; i += chunkSize) {
                          const chunk = content.substring(i, i + chunkSize);
                          controller.enqueue(encoder.encode(chunk));
                        }
                      } else {
                        controller.enqueue(encoder.encode(content));
                      }
                      return;
                    } else if (parsed.type === 'error' && parsed.data.error !== undefined && parsed.data.error !== '') {
                      // 处理错误
                      const errorContent = `错误: ${parsed.data.error}`;
                      controller.enqueue(encoder.encode(errorContent));
                      return;
                    } else if (parsed.type === 'done' || parsed.type === 'finish') {
                      // 处理完成事件
                      logger.debug('流式响应完成');
                      return;
                    }
                  }

                  // 处理不同AI服务的原始输出格式（保持向后兼容）
                  let content = '';
                  let thinking = '';

                  // 处理Claude/Anthropic事件格式
                  const claude = parsed as ClaudeStreamChunk;
                  if (claude.event === 'content_block_delta' && claude.data?.delta?.text !== undefined && claude.data.delta.text !== '') {
                    content = claude.data.delta.text;
                  } else {
                    // 处理DeepSeek/OpenAI格式
                    const oai = parsed as OpenAIStreamChunk;
                    if (oai.choices && oai.choices.length > 0) {
                      const delta = oai.choices[0]?.delta;
                      if (delta?.content !== undefined && delta.content !== '') {
                        content = delta.content;
                      }
                      // 处理DeepSeek思考内容 - 使用正确的字段名
                      if (delta?.reasoning_content !== undefined && delta.reasoning_content !== '') {
                        thinking = delta.reasoning_content;
                      }
                    } else {
                      // 处理错误信息
                      const err = parsed as StreamErrorChunk;
                      if (err.error !== undefined) {
                        const errText = typeof err.error === 'string'
                          ? err.error
                          : JSON.stringify(err.error);
                        content = `错误: ${errText}`;
                      }
                    }
                  }

                  // 处理思考内容
                  if (thinking) {
                    // 为思考内容添加特殊标记
                    const thinkingChunk = `🤔思考: ${thinking}`;
                    controller.enqueue(encoder.encode(thinkingChunk));
                  }

                  // 只有当提取到实际内容时才传递，按字符或小块分割以提高流畅性
                  if (content) {
                    // 对长内容进行细粒度处理，使显示更流畅
                    if (content.length > 20) {
                      const chunkSize = Math.min(20, Math.ceil(content.length / 3));
                      for (let i = 0; i < content.length; i += chunkSize) {
                        const chunk = content.substring(i, i + chunkSize);
                        controller.enqueue(encoder.encode(chunk));
                      }
                    } else {
                      controller.enqueue(encoder.encode(content));
                    }
                  }
                } else {
                  // 如果不是JSON但仍有内容，则直接传递
                  if (contentLine && !contentLine.includes('[DONE]')) {
                    // 纯文本也进行分块处理
                    if (contentLine.length > 30) {
                      const chunkSize = Math.min(30, Math.ceil(contentLine.length / 4));
                      for (let i = 0; i < contentLine.length; i += chunkSize) {
                        const chunk = contentLine.substring(i, i + chunkSize);
                        controller.enqueue(encoder.encode(chunk));
                      }
                    } else {
                      controller.enqueue(encoder.encode(contentLine));
                    }
                  }
                }
              } catch (e) {
                // 解析失败时，记录原因并直接传递原始内容
                logger.debug('SSE 行解析失败，按原文透传:', e);
                if (contentLine && !contentLine.includes('[DONE]')) {
                  controller.enqueue(encoder.encode(contentLine));
                }
              }
            };

            // 处理文本响应，将其转换为流
            const textData = response.data;
            logger.debug('收到文本响应，长度：', textData.length);

            // 将文本按行分割
            if (typeof textData === 'string') {
              const lines = textData.split('\n');
              for (const line of lines) {
                if (line.trim()) {
                  processLine(line.trim());
                }
              }
            } else {
              throw new Error(`响应数据类型意外：${typeof textData}`);
            }

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
          let errorMessage = '错误: 无法连接到服务器';

          // 使用类型安全的错误处理
          if (isApiError(error)) {
            errorMessage = `错误: 服务器返回${error.response.status}错误`;
            if (error.response.data) {
              // data 是结构化对象（含 detail 等字段），用 JSON.stringify 避免 [object Object]
              errorMessage += ` - ${JSON.stringify(error.response.data)}`;
            }
          } else {
            errorMessage = `错误: ${extractErrorMessage(error)}`;
          }

          controller.enqueue(encoder.encode(errorMessage));
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
