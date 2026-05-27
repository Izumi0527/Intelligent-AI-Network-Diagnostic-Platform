<template>
  <div
    class="message-actions"
    :class="{ 'message-actions--visible': visible }"
  >
    <button
      type="button"
      class="action-btn"
      :class="{ 'action-btn--copied': copied }"
      :aria-label="copied ? '已复制' : '复制此消息'"
      :title="copied ? '已复制' : '复制此消息'"
      @click="onCopy"
    >
      <svg v-if="!copied" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
      </svg>
      <svg v-else width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <polyline points="20 6 9 17 4 12" />
      </svg>
      <span class="action-btn__label">{{ copied ? '已复制' : '复制' }}</span>
    </button>

    <button
      v-if="canRetry"
      type="button"
      class="action-btn action-btn--retry"
      aria-label="重新发送"
      title="重新发送"
      @click="onRetry"
    >
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <polyline points="1 4 1 10 7 10" />
        <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
      </svg>
      <span class="action-btn__label">重试</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import type { ChatMessage } from '@/types/chat';
import { logger } from '@/utils/logger';

interface Props {
  message: ChatMessage
  canRetry: boolean
  visible?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  visible: false
});

const emit = defineEmits<{
  retry: []
  copy: [id: string]
}>();

const copied = ref(false);

const onCopy = async (): Promise<void> => {
  try {
    await navigator.clipboard.writeText(props.message.content);
    copied.value = true;
    setTimeout(() => { copied.value = false; }, 1500);
    if (props.message.id !== undefined) {
      emit('copy', props.message.id);
    }
  } catch (error) {
    logger.warn('复制到剪贴板失败:', error);
  }
};

const onRetry = (): void => {
  emit('retry');
};
</script>

<style scoped>
.message-actions {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  opacity: 0;
  transition: opacity var(--dur-enter) var(--ease-standard);
}

.message-actions--visible,
.message-row:hover .message-actions,
.message-actions:focus-within {
  opacity: 1;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 7px;
  font-size: 11px;
  line-height: 1;
  color: var(--muted-foreground);
  background-color: transparent;
  border: 1px solid var(--border);
  border-radius: calc(var(--radius) - 2px);
  cursor: pointer;
  transition:
    color var(--dur-enter) var(--ease-standard),
    background-color var(--dur-enter) var(--ease-standard),
    border-color var(--dur-enter) var(--ease-standard),
    transform var(--dur-enter) var(--ease-standard);
}

.action-btn:hover {
  color: var(--foreground);
  background-color: var(--muted);
  border-color: color-mix(in oklch, var(--foreground) 16%, transparent);
}

.action-btn:focus-visible {
  outline: 2px solid color-mix(in oklch, var(--primary) 55%, transparent);
  outline-offset: 1px;
}

.action-btn:active {
  transform: scale(0.96);
}

.action-btn--copied {
  color: var(--success);
  border-color: color-mix(in oklch, var(--success) 40%, transparent);
}

.action-btn--retry:hover {
  color: var(--warning);
  border-color: color-mix(in oklch, var(--warning) 45%, transparent);
}

.action-btn__label {
  user-select: none;
}

@media (max-width: 640px) {
  .action-btn__label {
    display: none;
  }
}
</style>
