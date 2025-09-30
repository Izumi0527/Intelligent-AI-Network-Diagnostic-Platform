// 聊天相关统一类型定义
// 生成时间: 2025-09-07 23:35

// 思考内容接口
export interface ThinkingContent {
  content: string
  isComplete: boolean
  timestamp: number
}

// 标准聊天消息接口 - 用于stores和主要逻辑
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp?: number
  thinking?: ThinkingContent // 思考内容（仅限assistant角色）
}

// 组件兼容的消息接口 - 用于ChatMessages组件
export interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp?: number
  id?: string // 可选，为了向后兼容
}

// API传输格式消息
export interface FormattedMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
}

// 消息历史项（用于API调用）
export interface MessageHistoryItem {
  role: 'user' | 'assistant' | 'system'
  content: string
  id?: string
  timestamp?: number
}

// API错误类型
export interface ApiError extends Error {
  response?: {
    data?: {
      detail?: string | Array<{ msg: string; type: string }>
      [key: string]: any
    }
    status: number
    statusText: string
  }
  request?: any
  validationErrors?: Array<{ msg: string; type: string }>
}

// 聊天数据存储格式
export interface ChatData {
  id: string
  title: string
  messages: ChatMessage[]
  createdAt: string
  updatedAt: string
  model: string
  settings: ChatSettings
}

// 聊天设置
export interface ChatSettings {
  temperature?: number
  maxTokens?: number
  streamMode?: boolean
  model?: string
}

// 类型守卫函数
export function isApiError(error: unknown): error is ApiError {
  return (
    error instanceof Error &&
    'response' in error &&
    typeof (error as any).response === 'object' &&
    (error as any).response !== null
  )
}

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
  )
}

// 消息转换工具函数
export function messageToFormattedMessage(message: ChatMessage | Message): FormattedMessage {
  return {
    role: message.role === 'system' ? 'user' : message.role,
    content: message.content
  }
}

export function messageToChatMessage(message: Message, generateId: () => string): ChatMessage {
  return {
    id: message.id || generateId(),
    role: message.role,
    content: message.content,
    timestamp: message.timestamp || Date.now()
  }
}

// 批量转换函数
export function formatMessagesForAPI(messages: (ChatMessage | Message)[]): FormattedMessage[] {
  if (!messages || !Array.isArray(messages)) return []
  
  return messages.map(messageToFormattedMessage)
}

export function ensureChatMessages(messages: (Message | ChatMessage)[], generateId: () => string): ChatMessage[] {
  if (!messages || !Array.isArray(messages)) return []
  
  return messages.map(msg => {
    if (isChatMessage(msg)) {
      return msg
    }
    return messageToChatMessage(msg, generateId)
  })
}