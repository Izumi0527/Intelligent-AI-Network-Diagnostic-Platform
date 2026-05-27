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
import { ChatHeader, ModelSelector, SearchToggle, ChatMessages, ChatInput } from './components';
import { useAiAssistantStore } from '@/stores/ai-assistant';
import { useAiKeyboard } from '@/composables';
import type { ChatMessage } from '@/types/chat';
import { logger } from '@/utils/logger';

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
  currentThinkingContent: store.currentThinkingContent
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

const handleSearchToggle = (): void => {
  store.toggleSearchMode();
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
