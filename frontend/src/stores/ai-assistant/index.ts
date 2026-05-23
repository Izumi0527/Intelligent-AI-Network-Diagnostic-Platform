import { defineStore } from 'pinia';
import { reactive, toRefs } from 'vue';
import { initialState } from './state';
import { createMessagingActions } from './actions/messaging';
import { createConnectionActions } from './actions/connection';
import { createStorageActions } from './actions/storage';
import { createUtilActions } from './actions/utils';

export type { ChatMessage, AIModel, ChatData, ChatSettings } from '@/types/chat';

export const useAiAssistantStore = defineStore('aiAssistant', () => {
  // 使用 reactive 创建响应式状态
  const state = reactive(initialState());

  // 创建各个模块的 actions
  const connectionActions = createConnectionActions(state);
  const storageActions = createStorageActions(state);
  const utilActions = createUtilActions(state);
  const messagingActions = createMessagingActions(state, utilActions, storageActions);

  // 工具方法
  const toggleStreamingMode = (): void => {
    state.streamingEnabled = !state.streamingEnabled;
  };

  const toggleSearchMode = (): void => {
    state.searchEnabled = !state.searchEnabled;
  };

  const setSelectedModel = (modelValue: string): void => {
    state.selectedModel = modelValue;
  };

  const changeModel = (modelValue: string): void => {
    state.selectedModel = modelValue;
    storageActions.loadConversationFromStorage();
    void connectionActions.checkModelConnection();
  };

  // 使用 toRefs 进行响应式解构，避免 computed 包装导致的更新延迟
  const stateRefs = toRefs(state);

  return {
    // 状态
    selectedModel: stateRefs.selectedModel,
    availableModels: stateRefs.availableModels,
    isModelConnected: stateRefs.isModelConnected,
    streamingEnabled: stateRefs.streamingEnabled,
    searchEnabled: stateRefs.searchEnabled,
    isAIResponding: stateRefs.isAIResponding,
    isStreamingContent: stateRefs.isStreamingContent,
    isThinking: stateRefs.isThinking,
    currentThinkingContent: stateRefs.currentThinkingContent,
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
    toggleSearchMode,
    setSelectedModel,
    changeModel,
  };
});
