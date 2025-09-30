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
 */
export function isApiError(error: unknown): error is ApiError {
  return error instanceof Error && 'response' in error;
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
  return (
    obj !== null &&
    typeof obj === 'object' &&
    'id' in obj &&
    'role' in obj &&
    'content' in obj &&
    typeof (obj as any).id === 'string' &&
    ['user', 'assistant', 'system'].includes((obj as any).role) &&
    typeof (obj as any).content === 'string'
  );
}