import { defineStore } from 'pinia'
import { reactive, toRefs } from 'vue'
import { initialState } from './state'
import { createMessagingActions } from './actions/messaging'
import { createConnectionActions } from './actions/connection'
import { createStorageActions } from './actions/storage'
import { createUtilActions } from './actions/utils'

export type { ChatMessage } from '@/types/chat'

export const useAiAssistantStore = defineStore('aiAssistant', () => {
  // 使用reactive创建响应式状态
  const state = reactive(initialState())

  // 创建各个模块的actions
  const connectionActions = createConnectionActions(state)
  const storageActions = createStorageActions(state)
  const utilActions = createUtilActions(state)
  const messagingActions = createMessagingActions(state, utilActions, storageActions)

  // 工具方法
  const toggleStreamingMode = () => {
    state.streamingEnabled = !state.streamingEnabled
  }

  const setSelectedModel = (modelValue: string) => {
    state.selectedModel = modelValue
  }

  const changeModel = (modelValue: string) => {
    state.selectedModel = modelValue
    storageActions.loadConversationFromStorage()
    connectionActions.checkModelConnection()
  }

  // 使用toRefs进行响应式解构，避免computed包装导致的更新延迟
  const stateRefs = toRefs(state)

  // 返回所有状态和方法
  return {
    // 状态 - 使用toRefs直接暴露响应式属性
    selectedModel: stateRefs.selectedModel,
    availableModels: stateRefs.availableModels,
    isModelConnected: stateRefs.isModelConnected,
    streamingEnabled: stateRefs.streamingEnabled,
    isAIResponding: stateRefs.isAIResponding,
    isStreamingContent: stateRefs.isStreamingContent,
    isThinking: stateRefs.isThinking, // 新增：思考状态
    currentThinkingContent: stateRefs.currentThinkingContent, // 新增：当前思考内容
    chatMessages: stateRefs.chatMessages,
    isLoading: stateRefs.isLoading,
    error: stateRefs.error,
    conversationId: stateRefs.conversationId,
    modelConnections: stateRefs.modelConnections,
    connectionStatus: stateRefs.connectionStatus,

    // 连接管理
    ...connectionActions,

    // 存储管理
    ...storageActions,

    // 消息处理
    ...messagingActions,

    // 工具方法
    ...utilActions,
    toggleStreamingMode,
    setSelectedModel,
    changeModel,
  }
})