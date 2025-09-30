import type { AIAssistantState } from './types'
import { generateId } from '../../utils/helpers'

export const initialState = (): AIAssistantState => ({
  selectedModel: 'deepseek-chat',
  availableModels: [], // 移除硬编码预设模型，统一使用后端配置
  isModelConnected: false,
  streamingEnabled: true,
  isAIResponding: false,
  isStreamingContent: false,  // 新增：正在接收流式内容
  isThinking: false, // 新增：是否正在思考中
  currentThinkingContent: '', // 新增：当前思考内容
  chatMessages: [],
  isLoading: false,
  error: null,
  conversationId: generateId(),
  modelConnections: {},
  connectionStatus: 'disconnected'
})