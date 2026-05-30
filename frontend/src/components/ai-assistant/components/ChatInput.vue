<template>
  <div class="chat-input">
    <div class="chat-input__row">
      <div class="chat-input__textarea-wrap">
        <label for="chat-message-input" class="sr-only">输入消息</label>
        <textarea
          id="chat-message-input"
          ref="messageInput"
          v-model="message"
          name="message"
          :disabled="isLocked"
          :placeholder="placeholder"
          autocomplete="off"
          class="chat-input__textarea ai-input"
          :class="{
            'chat-input__textarea--locked': isLocked,
            'chat-input__textarea--has-error': hasError
          }"
          :aria-invalid="hasError ? 'true' : 'false'"
          :aria-describedby="hasError ? 'chat-message-input-error' : undefined"
          @keydown="handleKeyDown"
          @input="handleInput"
        />

        <div
          class="chat-input__progress"
          aria-hidden="true"
        >
          <div
            class="chat-input__progress-bar"
            :data-state="progressState"
            :style="{ width: `${Math.min(progressPercent, 100)}%` }"
          />
        </div>

        <div
          v-if="hasError"
          id="chat-message-input-error"
          class="chat-input__error"
          :title="errorMessage"
          role="alert"
          aria-live="polite"
        >
          <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
          </svg>
          <span class="sr-only">{{ errorMessage }}</span>
        </div>
      </div>

      <button
        type="button"
        class="chat-input__send-btn btn-primary"
        :disabled="!canSend"
        title="发送消息 (Enter)"
        aria-label="发送消息"
        @click="handleSend"
      >
        <send-icon class="w-4 h-4" />
      </button>
    </div>

    <div class="chat-input__hints">
      <span
        :class="counterColorClass"
        role="status"
        aria-live="polite"
        aria-atomic="true"
      >{{ message.length }}/{{ maxLength }}</span>
      <span v-if="disabled" class="chat-input__status">{{ statusText }}</span>
      <span class="chat-input__shortcut">
        <kbd>Shift</kbd>+<kbd>Enter</kbd> 换行
      </span>
      <span class="chat-input__shortcut">
        <kbd>Enter</kbd> 发送
      </span>
      <span class="chat-input__shortcut">
        <kbd>⌘L</kbd> 跳底
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { SendIcon } from '@/components/common/icons';
import { useAutoResizeTextarea } from '@/composables';

const props = withDefaults(defineProps<{
  disabled?: boolean
  statusText?: string
  maxLength?: number
  placeholder?: string
}>(), {
  disabled: false,
  statusText: '',
  maxLength: 2000,
  placeholder: '问点什么…（Shift+Enter 换行 · Enter 发送 · Esc 清空）'
});

const emit = defineEmits<{
  send: [message: string]
  input: [message: string]
}>();

const message = ref('');
const { textareaRef: messageInput, resize: adjustTextareaHeight } = useAutoResizeTextarea({ maxHeight: 120 });

const progressPercent = computed<number>(() =>
  props.maxLength > 0 ? (message.value.length / props.maxLength) * 100 : 0
);

/** 进度条状态：normal / warning / danger */
const progressState = computed<'normal' | 'warning' | 'danger'>(() => {
  const p = progressPercent.value;
  if (p >= 100) { return 'danger'; }
  if (p >= 80) { return 'warning'; }
  return 'normal';
});

const counterColorClass = computed<string>(() => {
  if (progressState.value === 'danger') { return 'chat-input__counter--danger'; }
  if (progressState.value === 'warning') { return 'chat-input__counter--warning'; }
  return 'chat-input__counter';
});

const hasError = computed(() => message.value.length > props.maxLength);

const isLocked = computed<boolean>(() =>
  props.disabled || message.value.length > props.maxLength
);

const canSend = computed(() =>
  !props.disabled && message.value.trim().length > 0 && message.value.length <= props.maxLength
);

const errorMessage = computed(() => {
  if (hasError.value) {
    return `内容超出限制，最多 ${props.maxLength} 字符`;
  }
  return '';
});

const handleSend = (): void => {
  if (!canSend.value) { return; }
  const content = message.value.trim();
  if (content) {
    emit('send', content);
    message.value = '';
    adjustTextareaHeight();
  }
};

const handleKeyDown = (event: KeyboardEvent): void => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    handleSend();
    return;
  }
  if (event.key === 'Escape' && message.value.length > 0) {
    event.preventDefault();
    clear();
  }
};

const handleInput = (): void => {
  emit('input', message.value);
  adjustTextareaHeight();
};

const focus = (): void => { messageInput.value?.focus(); };
const clear = (): void => { message.value = ''; adjustTextareaHeight(); };
const fillText = (text: string): void => {
  message.value = text;
  adjustTextareaHeight();
  focus();
};

watch(() => props.disabled, (disabled) => { if (!disabled) { focus(); } });

/** 全局自定义事件：命令面板的 chat.focus 命令通过此事件触发 */
const onGlobalFocusInput = (): void => { focus(); };
onMounted(() => window.addEventListener('ai-focus-input', onGlobalFocusInput));
onUnmounted(() => window.removeEventListener('ai-focus-input', onGlobalFocusInput));

defineExpose({ focus, clear, fillText });
</script>

<style scoped>
.chat-input {
  padding: 10px 14px 12px;
  border-top: 1px solid var(--border);
  background: transparent;
  border-bottom-left-radius: calc(var(--radius) + 4px);
  border-bottom-right-radius: calc(var(--radius) + 4px);
}

.chat-input__row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}

.chat-input__textarea-wrap {
  position: relative;
  flex: 1;
  min-width: 0;
}

/* L 角标：左上 + 右下两角标记可交互输入区，:focus-within 点亮 */
.chat-input__textarea-wrap::before,
.chat-input__textarea-wrap::after {
  content: '';
  position: absolute;
  width: 9px;
  height: 9px;
  border: 0 solid var(--hud-bracket);
  pointer-events: none;
  transition: border-color var(--dur-enter) var(--ease-hud);
}

.chat-input__textarea-wrap::before {
  top: -2px;
  left: -2px;
  border-top-width: 1px;
  border-left-width: 1px;
}

.chat-input__textarea-wrap::after {
  bottom: -2px;
  right: -2px;
  border-bottom-width: 1px;
  border-right-width: 1px;
}

.chat-input__textarea-wrap:focus-within::before,
.chat-input__textarea-wrap:focus-within::after {
  border-color: var(--hud-bracket-active);
}

@media (prefers-reduced-motion: reduce) {
  .chat-input__textarea-wrap::before,
  .chat-input__textarea-wrap::after {
    transition: none !important;
  }
}

.chat-input__textarea {
  width: 100%;
  resize: none;
  min-height: 38px;
  max-height: 120px;
  padding: 8px 12px;
  font-size: 13px;
  line-height: 1.5;
  border-radius: var(--radius);
  field-sizing: content;
}

.chat-input__textarea--locked {
  cursor: not-allowed;
  opacity: 0.6;
}

.chat-input__textarea--has-error {
  padding-right: 36px;
  border-color: color-mix(in oklch, var(--destructive) 55%, transparent) !important;
}

.chat-input__progress {
  position: absolute;
  left: 0;
  right: 0;
  bottom: -1px;
  height: 1px;
  overflow: hidden;
  border-bottom-left-radius: var(--radius);
  border-bottom-right-radius: var(--radius);
  pointer-events: none;
}

.chat-input__progress-bar {
  height: 100%;
  transition:
    width var(--dur-enter) var(--ease-standard),
    background-color var(--dur-enter) var(--ease-standard);
}

.chat-input__progress-bar[data-state='normal'] {
  background-color: var(--primary);
}

.chat-input__progress-bar[data-state='warning'] {
  background-color: var(--warning);
}

.chat-input__progress-bar[data-state='danger'] {
  background-color: var(--destructive);
}

.chat-input__error {
  position: absolute;
  right: 10px;
  top: 8px;
  color: var(--destructive);
}

.chat-input__send-btn {
  flex-shrink: 0;
  width: 38px;
  height: 38px;
  padding: 0;
  border-radius: var(--radius);
}

.chat-input__hints {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
  font-size: 11px;
  color: var(--muted-foreground);
}

.chat-input__counter {
  font-family: var(--app-font-mono);
}

.chat-input__counter--warning {
  font-family: var(--app-font-mono);
  color: var(--warning);
  font-weight: 500;
}

.chat-input__counter--danger {
  font-family: var(--app-font-mono);
  color: var(--destructive);
  font-weight: 600;
}

.chat-input__status {
  color: var(--warning);
  font-size: 11px;
}

.chat-input__shortcut {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.chat-input__shortcut kbd {
  font-family: var(--app-font-mono);
  font-size: 10px;
  padding: 1px 4px;
  border-radius: 3px;
  background-color: var(--muted);
  border: 1px solid var(--border);
  color: var(--muted-foreground);
}

@media (max-width: 640px) {
  .chat-input__shortcut {
    display: none;
  }
}
</style>
