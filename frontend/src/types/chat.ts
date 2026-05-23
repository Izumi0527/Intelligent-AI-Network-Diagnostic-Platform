// 聊天与 AI 助手统一类型定义
// 本文件是 stores/ai-assistant 与组件层共用的类型源头

import type { SearchSource } from './api';

export type { SearchSource };

// ───────────────────────────────── 基础消息类型 ─────────────────────────────────

export interface ThinkingContent {
  content: string
  isComplete: boolean
  timestamp: number
}

// 错误分类：messaging.ts 与 utils.ts 共用
export type ErrorType =
  | 'network'
  | 'timeout'
  | 'rate-limit'
  | 'validation'
  | 'server'
  | 'aborted'
  | 'unknown'

export interface MessageError {
  type: ErrorType
  message: string
  retryable: boolean
}

export type MessageStatus =
  | 'sending'
  | 'streaming'
  | 'done'
  | 'error'
  | 'aborted'

// 标准聊天消息接口 - 用于 stores 和主要逻辑
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp?: number
  thinking?: ThinkingContent // 思考内容（仅限 assistant 角色）
  error?: MessageError // 错误分类（用于 UI 决定是否显示 retry 按钮）
  aborted?: boolean // 用户主动中断
  status?: MessageStatus // 消息生命周期状态
  sources?: SearchSource[] // 联网搜索引用的来源（assistant 消息且 enable_search 启用时）
  searchFailed?: boolean // 联网搜索是否失败（启用但未取到结果或异常时为 true）
}

// 组件兼容的消息接口 - 用于 ChatMessages 组件
export interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp?: number
  id?: string // 可选，向后兼容
}

// API 传输格式消息
export interface FormattedMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
}

// 消息历史项（用于 API 调用）
export interface MessageHistoryItem {
  role: 'user' | 'assistant' | 'system'
  content: string
  id?: string
  timestamp?: number
}

// ───────────────────────────────── API / 错误类型 ─────────────────────────────────

export interface ApiError extends Error {
  code?: string
  status?: number
  response?: {
    data?: {
      detail?: string | Array<{ msg: string; type: string }>
      [key: string]: unknown
    }
    status: number
    statusText: string
  }
  request?: unknown
  validationErrors?: Array<{ msg: string; type: string }>
}

export interface MessageRequest {
  model: string
  messages: Array<{
    role: 'user' | 'assistant' | 'system'
    content: string
  }>
  stream?: boolean
}

export interface APIResponse {
  data?: {
    content?: string
    message?: {
      content: string
    }
    connected?: boolean
    status?: string
  }
}

// ───────────────────────────────── AI 模型与状态 ─────────────────────────────────

export interface AIModel {
  label: string
  value: string
  description?: string
  available: boolean
}

export interface AIAssistantState {
  selectedModel: string
  availableModels: AIModel[]
  isModelConnected: boolean
  streamingEnabled: boolean
  searchEnabled: boolean
  isAIResponding: boolean
  isStreamingContent: boolean // 正在接收流式内容
  isThinking: boolean // 是否正在思考中
  currentThinkingContent: string // 当前思考内容
  chatMessages: ChatMessage[]
  isLoading: boolean
  error: string | null
  conversationId: string
  modelConnections: Record<string, boolean>
  connectionStatus: string
  // AbortController 用于中断进行中的流式请求；null 时表示无在途请求
  abortController: AbortController | null
  // 用户视口是否处于消息列表底部（< 80px 距底视为 true）
  isAtBottom: boolean
}

// ───────────────────────────────── 持久化与 Store ─────────────────────────────────

export interface ChatSettings {
  temperature?: number
  maxTokens?: number
  streamMode?: boolean
  model?: string
}

export interface ChatData {
  id: string
  title: string
  messages: ChatMessage[]
  createdAt: string
  updatedAt: string
  model: string
  settings: ChatSettings
}

export interface StoreActions {
  utilActions: {
    handleMessageError: (error: ApiError | Error, content: string) => void
    updateLastActivity: () => void
    validateMessage: (content: string) => boolean
  }
  storageActions: {
    saveToStorage: (data: ChatData) => void
    loadFromStorage: (id: string) => ChatData | null
    removeFromStorage: (id: string) => void
  }
}

// ───────────────────────────────── 类型守卫与工具函数 ─────────────────────────────────

export function isApiError(error: unknown): error is ApiError {
  return (
    error instanceof Error &&
    'response' in error &&
    typeof (error as { response?: unknown }).response === 'object' &&
    (error as { response?: unknown }).response !== null
  );
}

export function isChatMessage(obj: unknown): obj is ChatMessage {
  if (obj === null || typeof obj !== 'object') { return false; }
  const m = obj as Partial<ChatMessage>;
  return (
    typeof m.id === 'string' &&
    typeof m.content === 'string' &&
    (m.role === 'user' || m.role === 'assistant' || m.role === 'system')
  );
}

export function messageToFormattedMessage(message: ChatMessage | Message): FormattedMessage {
  return {
    role: message.role === 'system' ? 'user' : message.role,
    content: message.content,
  };
}

export function messageToChatMessage(message: Message, generateId: () => string): ChatMessage {
  return {
    id: message.id ?? generateId(),
    role: message.role,
    content: message.content,
    timestamp: message.timestamp ?? Date.now(),
  };
}

export function formatMessagesForAPI(messages: Array<ChatMessage | Message>): FormattedMessage[] {
  if (!Array.isArray(messages)) { return []; }
  return messages.map(messageToFormattedMessage);
}

export function ensureChatMessages(
  messages: Array<Message | ChatMessage>,
  generateId: () => string
): ChatMessage[] {
  if (!Array.isArray(messages)) { return []; }
  return messages.map((msg) => (isChatMessage(msg) ? msg : messageToChatMessage(msg, generateId)));
}
