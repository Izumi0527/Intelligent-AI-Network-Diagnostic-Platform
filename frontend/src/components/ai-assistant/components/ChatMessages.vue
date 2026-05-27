<template>
  <div
    ref="containerRef"
    role="log"
    aria-live="polite"
    aria-label="AI 对话消息列表"
    class="chat-messages"
  >
    <div
      v-if="isModelLoading"
      role="status"
      aria-busy="true"
      aria-label="正在切换模型"
      class="chat-messages__skeleton"
    >
      <div class="skeleton-bar skeleton-bar--xs" />
      <div class="skeleton-bar skeleton-bar--lg" />
      <div class="skeleton-bar skeleton-bar--xs skeleton-bar--right" />
      <div class="skeleton-bar skeleton-bar--md skeleton-bar--right" />
    </div>

    <empty-state
      v-else-if="messages.length === 0"
      @select="onSelectPrompt"
    />

    <template v-else>
      <message-bubble
        v-for="(message, index) in messages"
        :key="message.id ?? index"
        :message="message"
        :compact-meta="isCompactMeta(index)"
        :is-responding="isResponding"
        @copy="onCopy"
        @retry="onRetry"
      />
    </template>

    <!-- 非流式模式接收中提示 -->
    <div
      v-if="streamState.isStreamingContent && !streamState.streamingEnabled"
      role="status"
      aria-live="polite"
      aria-busy="true"
      class="stream-hint fade-in"
    >
      <div class="stream-hint__head">
        <span class="stream-hint__role">AI</span>
        <span class="stream-hint__meta">正在回复…</span>
      </div>
      <div class="stream-hint__body">
        <packet-signal mode="sending" />
        <span class="stream-hint__text">正在接收内容中…</span>
      </div>
    </div>

    <!-- 非流式模式打字气泡 -->
    <div
      v-if="streamState.isTyping && !streamState.isStreamingContent && !streamState.streamingEnabled"
      role="status"
      aria-live="polite"
      aria-busy="true"
      class="stream-hint fade-in"
    >
      <div class="stream-hint__head">
        <span class="stream-hint__role">AI</span>
        <span class="stream-hint__meta">正在思考…</span>
      </div>
      <div class="stream-hint__body">
        <packet-signal mode="sending" />
        <span class="stream-hint__text">AI 正在思考中…</span>
      </div>
    </div>

    <stop-generation-button :visible="canStop" @stop="onStop" />

    <scroll-to-bottom-button :visible="showScrollToBottom" @scroll="onScrollToBottom" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted, onUnmounted } from 'vue';
import { useChatScroll } from '@/composables';
import type { ChatMessage } from '@/types/chat';
import { useAiAssistantStore } from '@/stores/ai-assistant';
import { logger } from '@/utils/logger';
import MessageBubble from './MessageBubble.vue';
import StopGenerationButton from './StopGenerationButton.vue';
import EmptyState from './EmptyState.vue';
import ScrollToBottomButton from './ScrollToBottomButton.vue';
import PacketSignal from '@/components/decoration/PacketSignal.vue';

export interface StreamState {
  isTyping: boolean
  isStreamingContent: boolean
  isThinking: boolean
  currentThinkingContent: string
  streamingEnabled: boolean
}

const props = defineProps<{
  messages: ChatMessage[]
  streamState: StreamState
}>();

const emit = defineEmits<{
  'select-prompt': [prompt: string]
}>();

const store = useAiAssistantStore();

const { containerRef, scrollToBottom, isAtBottom } = useChatScroll({
  messageCount: () => props.messages.length,
  isTyping: () => props.streamState.isTyping,
  isStreamingContent: () => props.streamState.isStreamingContent
});

const isModelLoading = ref<boolean>(false);
let modelLoadingTimer: ReturnType<typeof setTimeout> | null = null;
watch(() => store.selectedModel, (next, prev) => {
  if (next === prev || prev === undefined) { return; }
  isModelLoading.value = true;
  if (modelLoadingTimer !== null) { clearTimeout(modelLoadingTimer); }
  modelLoadingTimer = setTimeout(() => {
    isModelLoading.value = false;
    modelLoadingTimer = null;
  }, 200);
});

const isCompactMeta = (index: number): boolean => {
  if (index === 0) { return false; }
  const prev = props.messages[index - 1];
  const curr = props.messages[index];
  if (prev === undefined || curr === undefined) { return false; }
  if (prev.role !== curr.role) { return false; }
  const prevTs = prev.timestamp ?? 0;
  const currTs = curr.timestamp ?? 0;
  if (prevTs === 0 || currTs === 0) { return false; }
  const dt = currTs - prevTs;
  return dt >= 0 && dt < 60_000;
};

const isResponding = computed<boolean>(() =>
  store.isAIResponding || store.isStreamingContent
);

const canStop = computed<boolean>(() =>
  props.streamState.isThinking
  || props.streamState.isStreamingContent
  || props.streamState.isTyping
);

const showScrollToBottom = computed<boolean>(() =>
  props.messages.length > 0 && !isAtBottom.value
);

const onStop = (): void => {
  logger.debug('[ChatMessages] 用户点击停止生成');
  store.stopGeneration();
};

const onRetry = (): void => {
  logger.debug('[ChatMessages] 用户点击重试');
  void store.retryLastMessage();
};

const onCopy = (id: string): void => {
  logger.debug('[ChatMessages] 用户复制消息', { id });
  store.copyMessage(id);
};

const onScrollToBottom = (): void => {
  void scrollToBottom();
};

const onSelectPrompt = (prompt: string): void => {
  emit('select-prompt', prompt);
};

/** 监听命令面板的 ai-scroll-to-bottom 事件 */
const onGlobalScrollToBottom = (): void => { void scrollToBottom(); };
onMounted(() => window.addEventListener('ai-scroll-to-bottom', onGlobalScrollToBottom));
onUnmounted(() => window.removeEventListener('ai-scroll-to-bottom', onGlobalScrollToBottom));

defineExpose({ scrollToBottom });
</script>

<style scoped>
.chat-messages {
  position: relative;
  flex: 1;
  overflow-y: auto;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 0;
  min-height: 300px;
  background: transparent;
}

.chat-messages__skeleton {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 4px;
}

.skeleton-bar {
  height: 12px;
  border-radius: calc(var(--radius) - 2px);
  background: linear-gradient(
    90deg,
    color-mix(in oklch, var(--muted) 60%, transparent),
    color-mix(in oklch, var(--muted) 85%, transparent),
    color-mix(in oklch, var(--muted) 60%, transparent)
  );
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.4s var(--ease-standard) infinite;
}

.skeleton-bar--xs { width: 33%; height: 8px; }
.skeleton-bar--md { width: 66%; height: 36px; }
.skeleton-bar--lg { width: 75%; height: 48px; }
.skeleton-bar--right { margin-left: auto; }

@keyframes skeleton-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@media (prefers-reduced-motion: reduce) {
  .skeleton-bar { animation: none !important; }
}

.stream-hint {
  margin-left: 0;
  margin-bottom: 16px;
}

.stream-hint__head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  margin-left: 28px;
  font-size: 10px;
  color: var(--muted-foreground);
}

.stream-hint__role {
  font-family: var(--app-font-mono);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: color-mix(in oklch, var(--foreground) 70%, transparent);
}

.stream-hint__meta {
  font-size: 10px;
  color: color-mix(in oklch, var(--muted-foreground) 80%, transparent);
}

.stream-hint__body {
  margin-left: 28px;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bubble-assistant-bg);
}

.stream-hint__text {
  font-size: 12px;
  color: var(--muted-foreground);
}

.chat-messages::-webkit-scrollbar {
  width: 6px;
}

.chat-messages::-webkit-scrollbar-track {
  background: transparent;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: color-mix(in oklch, var(--muted-foreground) 30%, transparent);
  border-radius: 3px;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background: color-mix(in oklch, var(--muted-foreground) 55%, transparent);
}
</style>
