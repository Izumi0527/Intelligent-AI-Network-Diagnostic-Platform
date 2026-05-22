import type { AIAssistantState, ChatMessage, ApiError, FormattedMessage, MessageError, ErrorType } from '@/types/chat';
import { generateId, isApiError } from '../../../utils/helpers';
import { logger } from '../../../utils/logger';

interface UtilActions {
  formatMessagesForAPI(messages: ChatMessage[]): FormattedMessage[];
  addUserMessage(content: string): ChatMessage;
  addAssistantMessage(content: string): void;
  addMessage(message: ChatMessage): void;
  toggleStreamingMode(): void;
  setSelectedModel(modelValue: string): void;
  classifyError(error: ApiError | Error): MessageError;
  handleMessageError(error: ApiError | Error, _content: string): void;
  updateLastActivity(): void;
  validateMessage(content: string): boolean;
}

// 把 HTTP status / error.name 等映射到统一的 MessageError 分类，
// 决定 UI 是否展示 retry 按钮、用什么文案。集中实现避免在多个调用点重复判定。
const classifyErrorImpl = (error: ApiError | Error): MessageError => {
  // 用户主动中断（AbortController.abort 触发的 AbortError）
  if (error.name === 'AbortError' || error.name === 'CanceledError') {
    return { type: 'aborted', message: '已停止生成', retryable: false };
  }

  if (isApiError(error)) {
    const statusCode = error.response.status;
    const detail = extractDetail(error);

    if (statusCode === 422 || statusCode === 400) {
      return {
        type: 'validation',
        message: detail !== '' ? `请求参数无效：${detail}` : '请求参数无效',
        retryable: false
      };
    }
    if (statusCode === 429) {
      return { type: 'rate-limit', message: '请求过于频繁，请稍后再试', retryable: true };
    }
    if (statusCode >= 500 && statusCode <= 599) {
      return {
        type: 'server',
        message: detail !== '' ? `服务器错误：${detail}` : '服务器内部错误，请稍后再试',
        retryable: true
      };
    }
    return {
      type: 'unknown' as ErrorType,
      message: `服务器返回 ${statusCode} 错误`,
      retryable: false
    };
  }

  // axios timeout：error.code === 'ECONNABORTED' 或 message 含 timeout
  const msg = error.message || '';
  if (msg.toLowerCase().includes('timeout') || (error as { code?: string }).code === 'ECONNABORTED') {
    return { type: 'timeout', message: '请求超时，请重试', retryable: true };
  }
  // 网络错误（Network Error / fetch failed 等）
  if (msg.includes('Network Error') || msg.toLowerCase().includes('network')) {
    return { type: 'network', message: '网络连接失败，请检查网络后重试', retryable: true };
  }

  return {
    type: 'unknown' as ErrorType,
    message: msg !== '' ? msg : '未知错误',
    retryable: true
  };
};

// 从 ApiError.response.data.detail 中安全提取人类可读文本
const extractDetail = (error: ApiError): string => {
  if (error.response === undefined) { return ''; }
  const data = error.response.data;
  if (data === undefined) { return ''; }
  const detail = data.detail;
  if (detail === undefined) { return ''; }
  if (typeof detail === 'string') { return detail; }
  if (Array.isArray(detail) && detail.length > 0) {
    return detail[0]?.msg ?? '';
  }
  return '';
};

export const createUtilActions = (state: AIAssistantState): UtilActions => ({
  formatMessagesForAPI(messages: ChatMessage[]): FormattedMessage[] {
    if (!Array.isArray(messages)) { return []; }

    return messages.map(msg => {
      const role = msg.role === 'user' ? 'user' : 'assistant';
      return {
        role,
        content: msg.content
      };
    });
  },

  addUserMessage(content: string): ChatMessage {
    const userMessage: ChatMessage = {
      id: generateId(),
      role: 'user',
      content,
      timestamp: Date.now(),
      status: 'done'
    };
    state.chatMessages.push(userMessage);
    return userMessage;
  },

  addAssistantMessage(content: string): void {
    const assistantMessage: ChatMessage = {
      id: generateId(),
      role: 'assistant',
      content,
      timestamp: Date.now(),
      status: 'done'
    };
    state.chatMessages.push(assistantMessage);
  },

  addMessage(message: ChatMessage): void {
    state.chatMessages.push(message);
  },

  toggleStreamingMode(): void {
    state.streamingEnabled = !state.streamingEnabled;
  },

  setSelectedModel(modelValue: string): void {
    state.selectedModel = modelValue;
  },

  classifyError: classifyErrorImpl,

  handleMessageError(error: ApiError | Error, _content: string): void {
    // _content: 调用方语义需要，保留参数以兼容接口
    void _content;
    logger.error('消息发送错误:', error);

    const errorInfo = classifyErrorImpl(error);

    // 优先策略：找到最后一条 assistant 消息（理论上是刚 push 进来等待填充的占位）
    // 给它打 error 字段而非新建一条错误消息。UI 据 error.retryable 渲染 retry 按钮。
    const lastIdx = state.chatMessages.length - 1;
    const lastMsg = lastIdx >= 0 ? state.chatMessages[lastIdx] : undefined;
    if (lastMsg !== undefined && lastMsg.role === 'assistant') {
      // 保留可能已经流入的部分内容，附加错误说明
      const prefix = lastMsg.content.trim() !== '' ? `${lastMsg.content}\n\n` : '';
      state.chatMessages[lastIdx] = {
        ...lastMsg,
        content: `${prefix}⚠️ ${errorInfo.message}`,
        error: errorInfo,
        status: errorInfo.type === 'aborted' ? 'aborted' : 'error',
        aborted: errorInfo.type === 'aborted'
      };
      state.chatMessages = [...state.chatMessages];
    } else {
      // 边界情况：发送前就出错（如校验失败），追加一条独立错误消息
      state.chatMessages.push({
        id: generateId(),
        role: 'assistant',
        content: `⚠️ ${errorInfo.message}`,
        timestamp: Date.now(),
        error: errorInfo,
        status: 'error'
      });
    }

    // 重置所有进行中状态
    state.isLoading = false;
    state.isAIResponding = false;
    state.isStreamingContent = false;
    state.isThinking = false;
    state.currentThinkingContent = '';
    state.abortController = null;
  },

  updateLastActivity(): void {
    // 更新最后活动时间
    logger.debug('更新最后活动时间:', new Date().toISOString());
  },

  validateMessage(content: string): boolean {
    // 验证消息内容
    if (!content || typeof content !== 'string') {
      return false;
    }
    return content.trim().length > 0 && content.trim().length <= 4000;
  }
});
