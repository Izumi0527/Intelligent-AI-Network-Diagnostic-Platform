<template>
  <div
    ref="containerRef"
    role="log"
    aria-live="polite"
    aria-label="AI 对话消息列表"
    class="chat-messages relative flex-1 overflow-y-auto p-4 space-y-6 bg-transparent"
    style="min-height: 400px;"
  >
    <!-- 空状态 -->
    <div v-if="messages.length === 0" class="flex h-full items-center justify-center">
      <div class="text-center max-w-sm p-8">
        <div class="text-4xl mb-4 opacity-30" aria-hidden="true">💬</div>
        <p class="mb-2 text-foreground/80 font-medium">与AI助手开始对话获取网络问题的帮助</p>
        <p class="text-sm text-muted-foreground">可以询问网络设备配置、故障排查方法或最佳实践</p>
      </div>
    </div>

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
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useChatScroll } from '@/composables';
import type { ChatMessage, ThinkingContent } from '@/types/chat';
import { useAiAssistantStore } from '@/stores/ai-assistant';
import { logger } from '@/utils/logger';
import MessageBubble from './MessageBubble.vue';
import ThinkingBlock from './ThinkingBlock.vue';
import StopGenerationButton from './StopGenerationButton.vue';

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

const store = useAiAssistantStore();

const { containerRef, scrollToBottom } = useChatScroll({
  messageCount: () => props.messages.length,
  isTyping: () => props.streamState.isTyping,
  isStreamingContent: () => props.streamState.isStreamingContent
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

defineExpose({ scrollToBottom });
</script>

<style scoped>
.message-assistant {
  margin-bottom: 1.5rem;
}

.bubble-assistant-bg {
  background: var(--bubble-assistant-bg);
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
