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
          class="confirm-btn confirm-btn--cancel"
          @click="onCancel"
        >
          {{ cancelText }}
        </button>
        <button
          type="button"
          class="confirm-btn confirm-btn--danger"
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
  background: oklch(0 0 0 / 0.4);
  backdrop-filter: blur(4px);
}

.confirm-panel {
  padding: 20px 22px 16px;
  background: var(--popover);
  color: var(--popover-foreground);
  border: 1px solid var(--border);
  border-radius: calc(var(--radius) + 4px);
  box-shadow: var(--shadow-popover);
}

.confirm-title {
  margin: 0 0 6px;
  font-size: 15px;
  font-weight: 600;
  color: var(--foreground);
  letter-spacing: -0.01em;
}

.confirm-msg {
  margin: 0 0 18px;
  font-size: 13px;
  line-height: 1.55;
  color: var(--muted-foreground);
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.confirm-btn {
  height: 30px;
  padding: 0 14px;
  font-size: 12px;
  font-weight: 500;
  line-height: 1;
  border-radius: var(--radius);
  border: 1px solid transparent;
  cursor: pointer;
  transition:
    background-color var(--dur-enter) var(--ease-standard),
    color var(--dur-enter) var(--ease-standard),
    border-color var(--dur-enter) var(--ease-standard),
    transform var(--dur-enter) var(--ease-standard);
}

.confirm-btn:focus-visible {
  outline: 2px solid color-mix(in oklch, var(--primary) 55%, transparent);
  outline-offset: 2px;
}

.confirm-btn:active { transform: scale(0.97); }

.confirm-btn--cancel {
  color: var(--muted-foreground);
  background: transparent;
  border-color: var(--border);
}

.confirm-btn--cancel:hover {
  color: var(--foreground);
  background: var(--muted);
}

.confirm-btn--danger {
  color: var(--destructive-foreground);
  background: var(--destructive);
  border-color: color-mix(in oklch, var(--destructive), black 8%);
}

.confirm-btn--danger:hover {
  background: color-mix(in oklch, var(--destructive), white 6%);
}

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

@media (prefers-reduced-motion: reduce) {
  .confirm-dialog[open] {
    animation: none;
  }
}
</style>
