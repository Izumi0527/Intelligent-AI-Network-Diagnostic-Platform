<template>
  <div class="flex flex-col h-full w-full ai-assistant-panel">
    <chat-header @clear="handleClear">
      <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between lg:gap-4">
        <model-selector
          :selected-model="store.selectedModel"
          :available-models="modelsForSelector"
          :is-connected="store.isModelConnected"
          @model-change="handleModelChange"
        />
        <stream-toggle :enabled="store.streamingEnabled" @toggle="store.toggleStreamingMode" />
      </div>
    </chat-header>

    <chat-messages
      ref="chatMessagesRef"
      :messages="messagesForDisplay"
      :stream-state="streamState"
      class="ai-chat-gradient"
    />

    <chat-input
      :disabled="store.isLoading || store.isAIResponding"
      :status-text="store.isAIResponding ? 'AI 正在响应...' : ''"
      @send="handleSendMessage"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { ChatHeader, ModelSelector, StreamToggle, ChatMessages, ChatInput } from './components';
import { useAiAssistantStore } from '@/stores/ai-assistant';
import { useAiKeyboard } from '@/composables';
import type { ChatMessage } from '@/types/chat';
import { logger } from '@/utils/logger';

const store = useAiAssistantStore();
const chatMessagesRef = ref<InstanceType<typeof ChatMessages> | null>(null);

const modelsForSelector = computed(() =>
  store.availableModels.map((model) => ({
    value: String(model.value),
    label: model.label ?? String(model.value)
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

const handleSendMessage = async (content: string): Promise<void> => {
  if (!content || store.isLoading || store.isAIResponding) { return; }
  try {
    await store.sendMessage(content);
    chatMessagesRef.value?.scrollToBottom();
  } catch (error) {
    logger.error('发送消息失败:', error);
  }
};

useAiKeyboard({ onClear: handleClear });

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
