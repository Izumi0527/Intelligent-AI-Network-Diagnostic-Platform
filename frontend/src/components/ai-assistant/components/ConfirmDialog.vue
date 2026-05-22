<template>
  <dialog
    ref="dialogRef"
    class="confirm-dialog"
    :aria-labelledby="`${dialogId}-title`"
    :aria-describedby="`${dialogId}-msg`"
    @close="onCancel"
    @click="onBackdropClick"
  >
    <div class="confirm-panel" @click.stop>
      <h2 :id="`${dialogId}-title`" class="confirm-title">{{ title }}</h2>
      <p :id="`${dialogId}-msg`" class="confirm-msg">{{ message }}</p>
      <div class="confirm-actions">
        <button
          type="button"
          class="btn btn-cancel"
          @click="onCancel"
        >
          {{ cancelText }}
        </button>
        <button
          type="button"
          class="btn btn-confirm"
          autofocus
          @click="onConfirm"
        >
          {{ confirmText }}
        </button>
      </div>
    </div>
  </dialog>
</template>

<script setup lang="ts">
import { ref, watch, useId } from 'vue';

interface Props {
  open: boolean
  title: string
  message: string
  confirmText?: string
  cancelText?: string
}

const props = withDefaults(defineProps<Props>(), {
  confirmText: '确认',
  cancelText: '取消'
});

const emit = defineEmits<{
  confirm: []
  cancel: []
}>();

const dialogRef = ref<HTMLDialogElement | null>(null);
const dialogId = useId();

watch(() => props.open, (isOpen) => {
  const dlg = dialogRef.value;
  if (dlg === null) { return; }
  if (isOpen) {
    if (!dlg.open) { dlg.showModal(); }
  } else if (dlg.open) {
    dlg.close();
  }
}, { immediate: true });

const onConfirm = (): void => {
  emit('confirm');
};

const onCancel = (): void => {
  emit('cancel');
};

// 点击 backdrop 关闭：原生 dialog 的 click 事件 target 为 dialog 本身时即点击在 backdrop
const onBackdropClick = (event: MouseEvent): void => {
  if (event.target === dialogRef.value) {
    onCancel();
  }
};
</script>

<style scoped>
.confirm-dialog {
  padding: 0;
  border: none;
  background: transparent;
  color: inherit;
  max-width: min(28rem, 90vw);
  width: 100%;
}

.confirm-dialog::backdrop {
  background: oklch(0 0 0 / 0.45);
  backdrop-filter: blur(4px);
}

.confirm-panel {
  padding: 20px 24px 16px;
  background: oklch(var(--background));
  color: oklch(var(--foreground));
  border: 1px solid oklch(var(--border));
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-ai-panel);
}

.confirm-title {
  margin: 0 0 8px;
  font-size: 16px;
  font-weight: 600;
  color: oklch(var(--foreground));
}

.confirm-msg {
  margin: 0 0 20px;
  font-size: 14px;
  line-height: 1.6;
  color: oklch(var(--muted-foreground));
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.btn {
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.4;
  border-radius: var(--radius-md);
  border: 1px solid transparent;
  cursor: pointer;
  transition:
    background-color var(--dur-fast) var(--ease-out),
    color var(--dur-fast) var(--ease-out),
    border-color var(--dur-fast) var(--ease-out),
    transform var(--dur-fast) var(--ease-out);
}

.btn:focus-visible {
  outline: 2px solid oklch(var(--primary) / 0.6);
  outline-offset: 2px;
}

.btn:active {
  transform: scale(0.97);
}

.btn-cancel {
  color: oklch(var(--muted-foreground));
  background: transparent;
  border-color: oklch(var(--border));
}

.btn-cancel:hover {
  color: oklch(var(--foreground));
  background: oklch(var(--muted) / 0.4);
}

.btn-confirm {
  color: oklch(0.98 0 0);
  background: oklch(0.55 0.18 30);
  border-color: oklch(0.55 0.18 30);
}

.btn-confirm:hover {
  background: oklch(0.5 0.2 30);
  border-color: oklch(0.5 0.2 30);
}

/* 进出场动画 */
.confirm-dialog[open] {
  animation: confirmIn var(--dur-base) var(--ease-spring);
}

@keyframes confirmIn {
  from {
    opacity: 0;
    transform: translateY(-8px) scale(0.97);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
</style>
