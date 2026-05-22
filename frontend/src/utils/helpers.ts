// 通用工具函数
// 生成时间: 2025-09-07 22:30

import type { ChatMessage, ApiError } from '@/types/chat';

/**
 * 生成唯一ID
 */
export function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * 获取当前时间戳
 */
export function getCurrentTimestamp(): number {
  return Date.now();
}

/**
 * 类型安全的错误检查
 *
 * 守卫返回时进一步收窄 `response` 为非空对象，使消费方可在
 * `if (isApiError(error))` 之后直接访问 `error.response.status` /
 * `error.response.data`，无需 `!` 或 `?.`。
 */
export function isApiError(
  error: unknown
): error is ApiError & { response: NonNullable<ApiError['response']> } {
  return (
    error instanceof Error &&
    'response' in error &&
    typeof (error as { response?: unknown }).response === 'object' &&
    (error as { response?: unknown }).response !== null
  );
}

/**
 * 安全的错误消息提取
 */
export function extractErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === 'string') {
    return error;
  }
  return '未知错误';
}

/**
 * ChatMessage类型守卫
 */
export function isChatMessage(obj: unknown): obj is ChatMessage {
  if (obj === null || typeof obj !== 'object') { return false; }
  const m = obj as { id?: unknown; role?: unknown; content?: unknown };
  return (
    typeof m.id === 'string' &&
    typeof m.content === 'string' &&
    (m.role === 'user' || m.role === 'assistant' || m.role === 'system')
  );
}