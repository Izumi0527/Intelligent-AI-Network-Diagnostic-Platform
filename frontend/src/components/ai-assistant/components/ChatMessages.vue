<template>
  <div
    ref="containerRef"
    role="log"
    aria-live="polite"
    aria-label="AI 对话消息列表"
    class="chat-messages relative flex-1 overflow-y-auto p-4 space-y-6 bg-transparent"
    style="min-height: 400px;"
  >
    <!-- 模型切换骨架占位：避免 conversation 列表瞬间替换导致的闪烁，最小 200ms -->
    <div
      v-if="isModelLoading"
      role="status"
      aria-busy="true"
      aria-label="正在切换模型"
      class="space-y-3 px-1"
    >
      <div class="skeleton-bar h-3 w-1/3"></div>
      <div class="skeleton-bar h-12 w-3/4"></div>
      <div class="skeleton-bar h-3 w-1/4 ml-auto"></div>
      <div class="skeleton-bar h-16 w-2/3 ml-auto"></div>
    </div>

    <!-- 空状态：示例 prompt 引导卡 -->
    <empty-state
      v-else-if="messages.length === 0"
      @select="onSelectPrompt"
    />

    <!-- 消息列表：MessageBubble 取代旧 80 行内联模板，ThinkingBlock 由 MessageBubble 内部聚合 -->
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

    <!-- 实时思考流：AI 正在思考时显示 -->
    <thinking-block
      v-if="streamState.isThinking && streamState.currentThinkingContent !== ''"
      :thinking="liveThinking"
      :is-streaming="true"
    />

    <!-- 非流式模式下接收中提示（非消息，状态指示器） -->
    <div
      v-if="streamState.isStreamingContent && !streamState.streamingEnabled"
      role="status"
      aria-live="polite"
      aria-busy="true"
      class="message-assistant group transition-[transform,opacity,background-color] duration-[var(--dur-base)] ease-[var(--ease-out)] fade-in"
    >
      <div class="font-medium text-xs mb-1.5 opacity-70 flex items-center gap-2 text-muted-foreground">
        <span class="inline-block w-5 h-5 rounded-full overflow-hidden flex items-center justify-center" aria-hidden="true">
          <span class="text-xs">🤖</span>
        </span>
        <span class="text-foreground/80">AI助手</span>
        <span class="text-muted-foreground/70 text-[10px]">正在回复...</span>
      </div>
      <div class="rounded-lg px-3 py-2 ml-7 border border-border/60 bubble-assistant-bg">
        <div class="flex items-center gap-1">
          <div class="w-2 h-2 bg-green-400 rounded-full animate-pulse" aria-hidden="true"></div>
          <span class="text-sm text-muted-foreground ml-2">正在接收内容中...</span>
        </div>
      </div>
    </div>

    <!-- 非流式模式下打字气泡（非消息，状态指示器） -->
    <div
      v-if="streamState.isTyping && !streamState.isStreamingContent && !streamState.streamingEnabled"
      role="status"
      aria-live="polite"
      aria-busy="true"
      class="message-assistant group transition-[transform,opacity,background-color] duration-[var(--dur-base)] ease-[var(--ease-out)] fade-in"
    >
      <div class="font-medium text-xs mb-1.5 opacity-70 flex items-center gap-2 text-muted-foreground">
        <span class="inline-block w-5 h-5 rounded-full overflow-hidden flex items-center justify-center" aria-hidden="true">
          <span class="text-xs">🤖</span>
        </span>
        <span class="text-foreground/80">AI助手</span>
        <span class="text-muted-foreground/70 text-[10px]">正在输入...</span>
      </div>
      <div class="rounded-lg px-3 py-2 ml-7 border border-border/60 bubble-assistant-bg">
        <div class="flex items-center gap-1">
          <div class="flex space-x-1" aria-hidden="true">
            <div class="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></div>
            <div class="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style="animation-delay: 0.1s"></div>
            <div class="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
          </div>
          <span class="text-sm text-muted-foreground ml-2">AI助手正在思考中...</span>
        </div>
      </div>
    </div>

    <!-- 悬浮"停止生成"按钮：覆盖在消息列表底部居中，仅在流式接收中或思考中显示 -->
    <stop-generation-button :visible="canStop" @stop="onStop" />

    <!-- 悬浮"回到最新"按钮：用户向上翻看历史时显示 -->
    <scroll-to-bottom-button :visible="showScrollToBottom" @scroll="onScrollToBottom" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useChatScroll } from '@/composables';
import type { ChatMessage, ThinkingContent } from '@/types/chat';
import { useAiAssistantStore } from '@/stores/ai-assistant';
import { logger } from '@/utils/logger';
import MessageBubble from './MessageBubble.vue';
import ThinkingBlock from './ThinkingBlock.vue';
import StopGenerationButton from './StopGenerationButton.vue';
import EmptyState from './EmptyState.vue';
import ScrollToBottomButton from './ScrollToBottomButton.vue';

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

// 模型切换骨架占位：watch selectedModel，最小 200ms 显示骨架避免列表瞬间替换闪烁
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

// 是否紧凑 meta：上一条同 role 且时间差 < 60s 时折叠头像/角色名，仅显时间
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

// 实时思考流 ThinkingBlock 的 prop：包一层让接口与历史态统一
const liveThinking = computed<ThinkingContent>(() => ({
  content: props.streamState.currentThinkingContent,
  isComplete: false,
  timestamp: Date.now()
}));

// 当前是否在响应中（透传给 MessageBubble 控制 retry 按钮可用性）
const isResponding = computed<boolean>(() =>
  store.isAIResponding || store.isStreamingContent
);

// "停止生成"按钮可见性：思考中 或 流式接收中 或 打字气泡中
const canStop = computed<boolean>(() =>
  props.streamState.isThinking
  || props.streamState.isStreamingContent
  || props.streamState.isTyping
);

// "回到最新"按钮可见性：仅在用户向上翻看（非底部）且有消息时显示
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

defineExpose({ scrollToBottom });
</script>

<style scoped>
.message-assistant {
  margin-bottom: 1.5rem;
}

.bubble-assistant-bg {
  background: var(--bubble-assistant-bg);
}

/* 模型切换骨架占位 */
.skeleton-bar {
  border-radius: var(--radius-sm);
  background: linear-gradient(
    90deg,
    color-mix(in oklch, oklch(var(--muted)) 60%, transparent),
    color-mix(in oklch, oklch(var(--muted)) 80%, transparent),
    color-mix(in oklch, oklch(var(--muted)) 60%, transparent)
  );
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.2s var(--ease-out) infinite;
}

@keyframes skeleton-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@media (prefers-reduced-motion: reduce) {
  .skeleton-bar { animation: none !important; }
}

.chat-messages::-webkit-scrollbar {
  width: 6px;
}

.chat-messages::-webkit-scrollbar-track {
  background: transparent;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: color-mix(in oklch, oklch(var(--muted)), oklch(var(--foreground)) 18%);
  border-radius: 3px;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background: color-mix(in oklch, oklch(var(--muted)), oklch(var(--foreground)) 32%);
}
</style>
