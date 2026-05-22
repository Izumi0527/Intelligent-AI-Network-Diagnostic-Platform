<template>
  <div
    ref="containerRef"
    class="flex-1 overflow-y-auto p-4 space-y-6 bg-transparent"
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

    <!-- 消息列表 -->
    <template v-else>
      <div
        v-for="(message, index) in messages"
        :key="message.id ?? index"
        :class="[
          message.role === 'user' ? 'message-user flex flex-col items-end' : 'message-assistant',
          'group transition-[transform,opacity,background-color] duration-[var(--dur-base)] ease-[var(--ease-out)]'
        ]"
      >
        <div
          :class="[
            'font-medium text-xs mb-1.5 opacity-70 group-hover:opacity-100 flex items-center gap-2 text-muted-foreground',
            message.role === 'user' ? 'flex-row-reverse' : ''
          ]"
        >
          <span class="inline-block w-5 h-5 rounded-full overflow-hidden flex items-center justify-center" aria-hidden="true">
            <span v-if="message.role === 'user'" class="text-xs">👤</span>
            <span v-else class="text-xs">🤖</span>
          </span>
          <span class="text-foreground/80">{{ message.role === 'user' ? '用户' : 'AI助手' }}</span>
          <span class="text-muted-foreground/70 text-[10px]">{{ formatTime(message.timestamp) }}</span>
        </div>

        <!-- 思考内容（仅 AI 助手消息且有思考内容时显示） -->
        <div
          v-if="message.role === 'assistant' && message.thinking && message.thinking.content"
          role="log"
          aria-live="polite"
          class="ml-7 mb-2 p-3 bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg dark:from-blue-950/40 dark:to-purple-950/40 dark:border-blue-800"
        >
          <div class="flex items-center gap-2 mb-2">
            <span class="text-blue-600 dark:text-blue-300 text-sm" aria-hidden="true">🤔</span>
            <span class="text-blue-700 dark:text-blue-200 text-xs font-medium">AI思考过程</span>
            <span
              v-if="!message.thinking.isComplete"
              class="text-blue-500 dark:text-blue-300 text-xs"
              aria-busy="true"
            >思考中...</span>
          </div>
          <div class="text-sm text-blue-800 dark:text-blue-100 whitespace-pre-wrap leading-relaxed">
            {{ message.thinking.content }}
          </div>
        </div>

        <div
          :class="[
            'rounded-lg px-4 py-3 max-w-none break-words transition-colors fade-in',
            message.role === 'user'
              ? 'bg-primary text-primary-foreground mr-7 border border-primary/80 max-w-md'
              : 'bg-muted/40 ml-7 border border-border/60'
          ]"
        >
          <div
            v-if="message.role === 'assistant'"
            class="prose prose-base max-w-none prose-gray dark:prose-invert leading-relaxed prose-p:mb-4 prose-ul:my-3 prose-ol:my-3 prose-li:mb-1 prose-h1:mb-4 prose-h2:mb-3 prose-h3:mb-3 prose-pre:bg-muted prose-pre:border prose-pre:border-border/60 prose-pre:p-3 prose-pre:rounded prose-code:bg-muted prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-blockquote:border-l-4 prose-blockquote:border-border"
            v-html="formatMessage(message.content)"
          ></div>
          <div
            v-else
            class="whitespace-pre-wrap text-sm leading-relaxed text-primary-foreground"
          >{{ message.content }}</div>
        </div>
      </div>
    </template>

    <!-- 实时思考流：AI 正在思考时显示 -->
    <div
      v-if="streamState.isThinking && streamState.currentThinkingContent"
      role="log"
      aria-live="polite"
      aria-busy="true"
      class="message-assistant group transition-[transform,opacity,background-color] duration-[var(--dur-base)] ease-[var(--ease-out)] fade-in"
    >
      <div class="font-medium text-xs mb-1.5 opacity-70 flex items-center gap-2 text-muted-foreground">
        <span class="inline-block w-5 h-5 rounded-full overflow-hidden flex items-center justify-center" aria-hidden="true">
          <span class="text-xs">🤔</span>
        </span>
        <span class="text-blue-700 dark:text-blue-200">AI助手思考中</span>
        <span class="text-blue-400 dark:text-blue-300 text-[10px]">正在思考...</span>
      </div>
      <div class="rounded-lg px-3 py-2 bg-gradient-to-r from-blue-50 to-purple-50 ml-7 border border-blue-200 dark:from-blue-950/40 dark:to-purple-950/40 dark:border-blue-800">
        <div class="flex items-center gap-2 mb-2">
          <div class="w-2 h-2 bg-blue-400 rounded-full animate-pulse" aria-hidden="true"></div>
          <span class="text-xs font-medium text-blue-700 dark:text-blue-200">思考过程</span>
        </div>
        <div class="text-sm text-blue-800 dark:text-blue-100 whitespace-pre-wrap leading-relaxed">
          {{ streamState.currentThinkingContent }}
        </div>
      </div>
    </div>

    <!-- 非流式模式下接收中提示 -->
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
      <div class="rounded-lg px-3 py-2 bg-muted/40 ml-7 border border-border/60">
        <div class="flex items-center gap-1">
          <div class="w-2 h-2 bg-green-400 rounded-full animate-pulse" aria-hidden="true"></div>
          <span class="text-sm text-muted-foreground ml-2">正在接收内容中...</span>
        </div>
      </div>
    </div>

    <!-- 非流式模式下打字气泡 -->
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
      <div class="rounded-lg px-3 py-2 bg-muted/40 ml-7 border border-border/60">
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
  </div>
</template>

<script setup lang="ts">
import DOMPurify from 'dompurify';
import { marked } from 'marked';
import { useChatScroll } from '@/composables';
import type { ChatMessage } from '@/types/chat';

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

const { containerRef, scrollToBottom } = useChatScroll({
  messageCount: () => props.messages.length,
  isTyping: () => props.streamState.isTyping,
  isStreamingContent: () => props.streamState.isStreamingContent
});

const formatMessage = (content: string): string => {
  try {
    const parsed = marked.parse(content, { async: false });
    const html = typeof parsed === 'string' ? parsed : content;
    return DOMPurify.sanitize(html, {
      ADD_TAGS: ['pre', 'code', 'table', 'thead', 'tbody', 'tr', 'th', 'td'],
      ADD_ATTR: ['class', 'target', 'rel']
    });
  } catch (error) {
    console.error('Markdown 渲染错误:', error);
    return DOMPurify.sanitize(content);
  }
};

const formatTime = (timestamp?: number): string => {
  if (!timestamp) { return ''; }
  const date = new Date(timestamp);
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  });
};

defineExpose({ scrollToBottom });
</script>

<style scoped>
.message-user {
  margin-bottom: 1.5rem;
}
.message-assistant {
  margin-bottom: 1.5rem;
}

.flex-1::-webkit-scrollbar {
  width: 6px;
}

.flex-1::-webkit-scrollbar-track {
  background: transparent;
}

.flex-1::-webkit-scrollbar-thumb {
  background: color-mix(in oklch, oklch(var(--muted)), oklch(var(--foreground)) 18%);
  border-radius: 3px;
}

.flex-1::-webkit-scrollbar-thumb:hover {
  background: color-mix(in oklch, oklch(var(--muted)), oklch(var(--foreground)) 32%);
}
</style>
