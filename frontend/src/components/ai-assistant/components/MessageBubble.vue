<template>
  <div
    :class="[
      'group transition-[transform,opacity,background-color] duration-[var(--dur-base)] ease-[var(--ease-out)] fade-in',
      isUser ? 'message-user flex flex-col items-end' : 'message-assistant'
    ]"
  >
    <message-meta
      :role="message.role"
      :timestamp="message.timestamp"
      :compact="compactMeta"
    />

    <thinking-block
      v-if="hasThinking && message.thinking"
      :thinking="message.thinking"
      :is-streaming="false"
    />

    <div
      :class="[
        'bubble-base rounded-lg px-4 py-3 max-w-none break-words transition-colors fade-in',
        isUser
          ? 'bubble-user mr-7 border border-primary/80 max-w-[min(28rem,80vw)]'
          : 'bubble-assistant ml-7 border border-border/60',
        message.error !== undefined ? 'message-error-bubble' : ''
      ]"
    >
      <div
        v-if="!isUser"
        class="prose prose-base max-w-none prose-gray dark:prose-invert leading-relaxed prose-p:mb-4 prose-ul:my-3 prose-ol:my-3 prose-li:mb-1 prose-h1:mb-4 prose-h2:mb-3 prose-h3:mb-3 prose-pre:bg-muted prose-pre:border prose-pre:border-border/60 prose-pre:p-3 prose-pre:rounded prose-code:bg-muted prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-blockquote:border-l-4 prose-blockquote:border-border dark:[&_p]:text-foreground/95 dark:[&_li]:text-foreground/95 dark:[&_strong]:text-foreground"
        v-html="formattedContent"
      ></div>
      <div
        v-else
        class="whitespace-pre-wrap text-sm leading-relaxed"
      >{{ message.content }}</div>
    </div>

    <div v-if="showActions" class="ml-7 mt-1.5">
      <message-actions
        :message="message"
        :can-retry="canRetry"
        :visible="message.error !== undefined"
        @retry="onRetry"
        @copy="onCopy"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import DOMPurify from 'dompurify';
import { marked } from 'marked';
import type { ChatMessage } from '@/types/chat';
import { logger } from '@/utils/logger';
import MessageMeta from './MessageMeta.vue';
import ThinkingBlock from './ThinkingBlock.vue';
import MessageActions from './MessageActions.vue';

interface Props {
  message: ChatMessage
  /** 紧凑 meta：上一条同 role 且时间差 < 60s 时由父组件传 true */
  compactMeta?: boolean
  /** 当前 AI 是否在响应中：true 时禁用 retry */
  isResponding?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  compactMeta: false,
  isResponding: false
});

const emit = defineEmits<{
  copy: [id: string]
  retry: []
}>();

const isUser = computed<boolean>(() => props.message.role === 'user');

const hasThinking = computed<boolean>(() =>
  props.message.role === 'assistant'
  && props.message.thinking !== undefined
  && props.message.thinking.content !== ''
);

// 仅在 assistant 消息且非流式态、且内容非空时显示操作按钮
const showActions = computed<boolean>(() => {
  if (props.message.role !== 'assistant') { return false; }
  if (props.message.status === 'streaming' || props.message.status === 'sending') { return false; }
  return props.message.content.trim() !== '';
});

const canRetry = computed<boolean>(() =>
  props.message.error?.retryable === true && !props.isResponding
);

const formattedContent = computed<string>(() => {
  if (isUser.value) { return props.message.content; }
  try {
    const parsed = marked.parse(props.message.content, { async: false });
    const html = typeof parsed === 'string' ? parsed : props.message.content;
    return DOMPurify.sanitize(html, {
      ADD_TAGS: ['pre', 'code', 'table', 'thead', 'tbody', 'tr', 'th', 'td'],
      ADD_ATTR: ['class', 'target', 'rel']
    });
  } catch (error) {
    logger.error('Markdown 渲染错误:', error);
    return DOMPurify.sanitize(props.message.content);
  }
});

const onCopy = (id: string): void => { emit('copy', id); };
const onRetry = (): void => { emit('retry'); };
</script>

<style scoped>
.message-user {
  margin-bottom: 1.5rem;
}
.message-assistant {
  margin-bottom: 1.5rem;
}

.bubble-user {
  background: var(--bubble-user-bg);
  /* 用户气泡文字固定白色：bg 在 light/dark 两种主题下都是深蓝紫，foreground
     不能跟随 --primary-foreground 翻转（dark 下会变深色，contrast 仅 3.1，
     未达 WCAG AA 4.5:1） */
  color: oklch(0.985 0 0);
}
.bubble-assistant {
  background: var(--bubble-assistant-bg);
}

.message-error-bubble {
  border-color: oklch(0.55 0.18 30 / 0.5) !important;
  background: color-mix(in oklch, oklch(0.55 0.18 30 / 0.08), oklch(var(--background)) 70%);
}
</style>
