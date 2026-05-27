<template>
  <div class="flex flex-col h-full w-full ai-assistant-panel">
    <chat-header @clear="handleClear">
      <div class="flex flex-col gap-2 sm:gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
        <model-selector
          :selected-model="store.selectedModel"
          :available-models="modelsForSelector"
          :is-connected="store.isModelConnected"
          @model-change="handleModelChange"
        />
        <div class="flex flex-col gap-2 sm:gap-4 sm:flex-row sm:items-center">
          <search-toggle :enabled="store.searchEnabled" @toggle="handleSearchToggle" />
          <stream-toggle :enabled="store.streamingEnabled" @toggle="store.toggleStreamingMode" />
        </div>
      </div>
    </chat-header>

    <chat-messages
      ref="chatMessagesRef"
      :messages="messagesForDisplay"
      :stream-state="streamState"
      class="ai-chat-gradient"
      @select-prompt="handleSelectPrompt"
    />

    <chat-input
      ref="chatInputRef"
      :disabled="isInputDisabled"
      :status-text="inputStatusText"
      @send="handleSendMessage"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { ChatHeader, ModelSelector, StreamToggle, SearchToggle, ChatMessages, ChatInput } from './components';
import { useAiAssistantStore } from '@/stores/ai-assistant';
import { useAiKeyboard } from '@/composables';
import type { ChatMessage } from '@/types/chat';
import { logger } from '@/utils/logger';

const SEARCH_TOGGLE_STORAGE_KEY = 'ai_assistant_search_enabled';

const store = useAiAssistantStore();
const chatMessagesRef = ref<InstanceType<typeof ChatMessages> | null>(null);
const chatInputRef = ref<InstanceType<typeof ChatInput> | null>(null);
const modelUnavailableStatusText = '当前模型未连接，无法发送消息';

const modelsForSelector = computed(() =>
  store.availableModels.map((model) => ({
    value: String(model.value),
    label: model.label ?? String(model.value),
    // available 由 connection.ts 从后端 /api/ai/models 响应填充；缺省视为可用
    available: model.available !== false
  }))
);

const messagesForDisplay = computed<ChatMessage[]>(() =>
  store.chatMessages.filter((msg) => msg.role === 'user' || msg.role === 'assistant')
);

const streamState = computed(() => ({
  isTyping: store.isAIResponding,
  isStreamingContent: store.isStreamingContent,
  isThinking: store.isThinking,
  currentThinkingContent: store.currentThinkingContent,
  streamingEnabled: store.streamingEnabled
}));

const isInputDisabled = computed<boolean>(() =>
  store.isLoading || store.isAIResponding || !store.isModelConnected
);

const inputStatusText = computed<string>(() => {
  if (store.isAIResponding) { return 'AI 正在响应...'; }
  if (!store.isModelConnected) { return modelUnavailableStatusText; }
  return '';
});

const handleClear = async (): Promise<void> => {
  try {
    await store.clearConversation();
  } catch (error) {
    logger.error('清空对话失败:', error);
  }
};

const handleModelChange = async (value: string): Promise<void> => {
  try {
    store.setSelectedModel(value);
    store.loadConversationFromStorage();
    await store.checkModelConnection();
  } catch (error) {
    logger.error('模型切换失败:', error);
  }
};

// SearchToggle 是用户级偏好，独立 localStorage key 持久化；
// 与 streamingEnabled 的"每对话 settings"不同，搜索开关在跨对话场景应稳定。
const handleSearchToggle = (): void => {
  store.toggleSearchMode();
  try {
    localStorage.setItem(SEARCH_TOGGLE_STORAGE_KEY, String(store.searchEnabled));
  } catch (error) {
    logger.warn('保存 SearchToggle 状态失败:', error);
  }
};

const handleSendMessage = async (content: string): Promise<void> => {
  if (!content || store.isLoading || store.isAIResponding || !store.isModelConnected) { return; }
  try {
    await store.sendMessage(content);
    chatMessagesRef.value?.scrollToBottom();
  } catch (error) {
    logger.error('发送消息失败:', error);
  }
};

// EmptyState 示例 prompt 点击 → 注入到 ChatInput textarea，让用户可改后再发送
const handleSelectPrompt = (prompt: string): void => {
  chatInputRef.value?.fillText(prompt);
};

useAiKeyboard({
  onScrollToBottom: () => { chatMessagesRef.value?.scrollToBottom(); }
});

onMounted(async () => {
  try {
    store.isLoading = true;
    // 恢复用户偏好：联网搜索开关（默认 false；非 'true' 字面量一律视为关闭）
    try {
      const persisted = localStorage.getItem(SEARCH_TOGGLE_STORAGE_KEY);
      if (persisted === 'true' && !store.searchEnabled) {
        store.toggleSearchMode();
      }
    } catch (error) {
      logger.warn('读取 SearchToggle 持久化状态失败:', error);
    }
    await store.loadAvailableModels();
    if (store.selectedModel) {
      await store.checkModelConnection();
    }
  } catch (error) {
    logger.error('AI助手初始化失败:', error);
  } finally {
    store.isLoading = false;
  }
});

watch(
  () => store.selectedModel,
  async (newModel, oldModel) => {
    if (newModel === oldModel) { return; }
    try {
      store.loadConversationFromStorage();
      await store.checkModelConnection();
    } catch (error) {
      logger.error('检查模型连接失败:', error);
    }
  }
);
</script>
