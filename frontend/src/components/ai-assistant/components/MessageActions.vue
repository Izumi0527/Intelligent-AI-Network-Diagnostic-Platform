<template>
  <div
    class="message-actions inline-flex items-center gap-1 transition-opacity duration-[var(--dur-base)] ease-[var(--ease-out)]"
    :class="visible ? 'opacity-100' : 'opacity-0 group-hover:opacity-100 focus-within:opacity-100'"
  >
    <button
      type="button"
      class="action-btn"
      :class="{ 'action-btn--copied': copied }"
      :aria-label="copied ? '已复制' : '复制此消息'"
      :title="copied ? '已复制' : '复制此消息'"
      @click="onCopy"
    >
      <svg
        v-if="!copied"
        xmlns="http://www.w3.org/2000/svg"
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
        focusable="false"
      >
        <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
      </svg>
      <svg
        v-else
        xmlns="http://www.w3.org/2000/svg"
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
        focusable="false"
      >
        <polyline points="20 6 9 17 4 12" />
      </svg>
      <span class="action-label">{{ copied ? '已复制' : '复制' }}</span>
    </button>

    <button
      v-if="canRetry"
      type="button"
      class="action-btn action-btn--retry"
      aria-label="重新发送"
      title="重新发送"
      @click="onRetry"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
        focusable="false"
      >
        <polyline points="1 4 1 10 7 10" />
        <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
      </svg>
      <span class="action-label">重试</span>
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
  /** 强制可见（hover 之外的场景，如错误消息常驻显示按钮） */
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
.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  font-size: 11px;
  line-height: 1;
  color: oklch(var(--muted-foreground));
  background: color-mix(in oklch, oklch(var(--background)) 65%, oklch(var(--muted)) 35%);
  border: 1px solid oklch(var(--border) / 0.6);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition:
    background-color var(--dur-fast) var(--ease-out),
    color var(--dur-fast) var(--ease-out),
    border-color var(--dur-fast) var(--ease-out),
    transform var(--dur-fast) var(--ease-out);
}

.action-btn:hover {
  color: oklch(var(--foreground));
  background: color-mix(in oklch, oklch(var(--background)) 50%, oklch(var(--muted)) 50%);
  border-color: oklch(var(--primary) / 0.4);
}

.action-btn:focus-visible {
  outline: 2px solid oklch(var(--primary) / 0.6);
  outline-offset: 2px;
}

.action-btn:active {
  transform: scale(0.96);
}

.action-btn--copied {
  color: oklch(0.55 0.15 150);
  border-color: oklch(0.55 0.15 150 / 0.4);
}

.action-btn--retry {
  color: oklch(0.55 0.18 30);
}

.action-btn--retry:hover {
  border-color: oklch(0.55 0.18 30 / 0.5);
}

.action-label {
  user-select: none;
}

/* 小屏只显示图标，省空间 */
@media (max-width: 640px) {
  .action-label {
    display: none;
  }
}
</style>
