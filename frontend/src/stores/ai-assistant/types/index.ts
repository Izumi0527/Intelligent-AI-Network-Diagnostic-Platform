export interface ThinkingContent {
  content: string
  isComplete: boolean
  timestamp: number
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp?: number
  thinking?: ThinkingContent // 思考内容（仅限assistant角色）
}

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
  isAIResponding: boolean
  isStreamingContent: boolean  // 新增：正在接收流式内容
  isThinking: boolean // 新增：是否正在思考中
  currentThinkingContent: string // 新增：当前思考内容
  chatMessages: ChatMessage[]
  isLoading: boolean
  error: string | null
  conversationId: string
  modelConnections: Record<string, boolean>
  connectionStatus: string
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

export interface ApiError extends Error {
  code?: string
  status?: number
  response?: {
    data?: unknown
    status: number
    statusText: string
  }
  validationErrors?: unknown[]
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

export interface ChatSettings {
  temperature?: number
  maxTokens?: number
  streamMode?: boolean
  model?: string
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