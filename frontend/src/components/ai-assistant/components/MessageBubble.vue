<template>
  <div
    :class="[
      'message-row',
      isUser ? 'message-row--user' : 'message-row--assistant',
      'fade-in'
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
      :is-streaming="isThinkingStreaming"
      :default-expanded="isLastAssistant ?? false"
    />

    <div
      :class="[
        'bubble',
        isUser ? 'bubble--user' : 'bubble--assistant',
        message.error !== undefined ? 'bubble--error' : ''
      ]"
    >
      <div
        v-if="!isUser"
        class="bubble__content prose prose-sm max-w-none dark:prose-invert
               prose-p:my-2 prose-ul:my-2 prose-ol:my-2 prose-li:my-1
               prose-h1:mb-3 prose-h1:mt-4 prose-h2:mb-2 prose-h2:mt-3
               prose-h3:mb-2 prose-h3:mt-3
               prose-pre:bg-zinc-900 prose-pre:text-zinc-100 prose-pre:border-0
               prose-pre:rounded-md prose-pre:p-3 prose-pre:font-mono prose-pre:text-xs
               prose-code:font-mono prose-code:text-[12px]
               prose-code:bg-muted prose-code:rounded prose-code:px-1.5 prose-code:py-0.5
               prose-code:before:content-none prose-code:after:content-none
               prose-strong:text-foreground
               prose-blockquote:border-l-2 prose-blockquote:border-border
               prose-blockquote:not-italic prose-blockquote:text-muted-foreground"
        v-html="formattedContent"
      />
      <div
        v-else
        class="bubble__user-text"
      >{{ message.content }}</div>
    </div>

    <search-sources-block
      v-if="!isUser && (hasSources || message.searchFailed === true)"
      :sources="message.sources ?? []"
      :search-failed="message.searchFailed ?? false"
    />

    <div v-if="showActions" class="message-actions-wrap">
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
import SearchSourcesBlock from './SearchSourcesBlock.vue';

interface Props {
  message: ChatMessage
  compactMeta?: boolean
  isResponding?: boolean
  isLastAssistant?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  compactMeta: false,
  isResponding: false,
  isLastAssistant: false
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

const isThinkingStreaming = computed<boolean>(() =>
  props.message.role === 'assistant'
  && props.message.status === 'streaming'
  && props.message.thinking !== undefined
  && props.message.thinking.isComplete === false
);

const hasSources = computed<boolean>(() =>
  Array.isArray(props.message.sources) && props.message.sources.length > 0
);

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
.message-row {
  margin-bottom: 20px;
  transition: opacity var(--dur-base) var(--ease-standard);
}

.message-row--user {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.bubble {
  max-width: none;
  padding: 10px 14px;
  border-radius: calc(var(--radius) + 2px);
  word-break: break-word;
  transition:
    border-color var(--dur-base) var(--ease-standard),
    background-color var(--dur-base) var(--ease-standard);
}

.bubble--user {
  background: var(--bubble-user-bg);
  color: var(--bubble-user-fg);
  border: 1px solid color-mix(in oklch, var(--bubble-user-bg), black 12%);
  margin-right: 28px;
  max-width: min(32rem, 82vw);
  border-bottom-right-radius: var(--radius);
}

.bubble--assistant {
  background: var(--bubble-assistant-bg);
  color: var(--bubble-assistant-fg);
  border: 1px solid var(--border);
  border-left: 2px solid color-mix(in oklch, var(--primary) 55%, transparent);
  margin-left: 28px;
  border-bottom-left-radius: var(--radius);
}

.bubble--error {
  border-color: color-mix(in oklch, var(--destructive) 55%, transparent) !important;
  background: color-mix(in oklch, var(--destructive) 6%, var(--background));
}

.bubble__user-text {
  font-size: 13px;
  line-height: 1.55;
  white-space: pre-wrap;
}

.bubble__content {
  font-size: 13px;
  line-height: 1.6;
}

.bubble__content :deep(pre) {
  font-family: var(--app-font-mono);
  font-size: 12px;
  line-height: 1.5;
  overflow-x: auto;
}

.bubble__content :deep(a) {
  color: var(--primary);
  text-decoration: underline;
  text-decoration-thickness: 1px;
  text-underline-offset: 2px;
}

.bubble__content :deep(a:hover) {
  text-decoration-thickness: 2px;
}

.message-actions-wrap {
  margin-left: 28px;
  margin-top: 4px;
}
</style>
