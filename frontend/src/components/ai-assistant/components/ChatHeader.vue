<template>
  <div class="chat-header">
    <div class="chat-header__top">
      <div class="chat-header__title-group">
        <span class="chat-header__title">AI 助手</span>
        <span class="chat-header__badge">BETA</span>
      </div>
      <div class="chat-header__actions">
        <button
          type="button"
          class="chat-header__clear-btn"
          title="清空当前对话 (⌘⇧K)"
          aria-label="清空当前对话"
          @click="openConfirm"
        >
          <clear-icon class="w-3.5 h-3.5" aria-hidden="true" />
          <span class="hidden sm:inline">清空</span>
        </button>
      </div>
    </div>

    <slot />

    <confirm-dialog
      :open="confirmOpen"
      title="清空当前对话"
      message="将清除当前模型下的全部聊天记录与缓存，且无法恢复。确定继续吗？"
      confirm-text="清空"
      cancel-text="取消"
      @confirm="onConfirm"
      @cancel="onCancel"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { ClearIcon } from '@/components/common/icons';
import ConfirmDialog from './ConfirmDialog.vue';

const emit = defineEmits<{
  clear: []
}>();

const confirmOpen = ref(false);

const openConfirm = (): void => {
  confirmOpen.value = true;
};

const onConfirm = (): void => {
  confirmOpen.value = false;
  emit('clear');
};

const onCancel = (): void => {
  confirmOpen.value = false;
};
</script>

<style scoped>
.chat-header {
  padding: 10px 14px 12px;
  border-bottom: 1px solid var(--border);
  background: transparent;
  border-top-left-radius: calc(var(--radius) + 4px);
  border-top-right-radius: calc(var(--radius) + 4px);
}

.chat-header__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.chat-header__title-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chat-header__title {
  font-size: 12px;
  font-weight: 500;
  font-family: var(--app-font-mono);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: color-mix(in oklch, var(--foreground) 65%, transparent);
}

.chat-header__badge {
  font-family: var(--app-font-mono);
  font-size: 9px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 3px;
  background-color: color-mix(in oklch, var(--primary) 16%, transparent);
  color: var(--primary);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.chat-header__actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.chat-header__clear-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 26px;
  padding: 0 8px;
  background-color: transparent;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--muted-foreground);
  font-size: 11px;
  cursor: pointer;
  transition:
    color var(--dur-enter) var(--ease-standard),
    border-color var(--dur-enter) var(--ease-standard),
    background-color var(--dur-enter) var(--ease-standard);
}

.chat-header__clear-btn:hover {
  color: var(--destructive);
  border-color: color-mix(in oklch, var(--destructive) 40%, transparent);
  background-color: color-mix(in oklch, var(--destructive) 8%, transparent);
}
</style>
