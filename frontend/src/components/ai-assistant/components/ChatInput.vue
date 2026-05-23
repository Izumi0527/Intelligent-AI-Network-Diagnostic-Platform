<template>
  <div class="p-4 border-t border-border/60 bg-transparent rounded-b-xl">
    <div class="flex gap-2 items-end">
      <div class="flex-1 relative">
        <label for="chat-message-input" class="sr-only">输入消息</label>
        <textarea
          id="chat-message-input"
          ref="messageInput"
          v-model="message"
          name="message"
          :disabled="isLocked"
          :placeholder="placeholder"
          autocomplete="off"
          class="w-full resize-none rounded-lg border border-border/85 bg-background/50 px-3 py-2 text-sm min-h-[40px] max-h-[120px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[oklch(var(--primary)/0.5)] focus-visible:border-primary dark:focus-visible:ring-[oklch(var(--primary)/0.7)] disabled:bg-muted/30 disabled:border-muted disabled:text-muted-foreground input-glow transition-colors placeholder:text-muted-foreground/60"
          :class="{
            'cursor-not-allowed': isLocked,
            'pr-10': hasError
          }"
          :aria-invalid="hasError ? 'true' : 'false'"
          :aria-describedby="hasError ? 'chat-message-input-error' : undefined"
          @keydown="handleKeyDown"
          @input="handleInput"
        />

        <!-- 字数进度条：底部 1px 条，颜色随占比阶梯切换 -->
        <div
          class="absolute left-0 right-0 -bottom-px h-px overflow-hidden rounded-b-lg pointer-events-none"
          aria-hidden="true"
        >
          <div
            class="h-full transition-[width,background-color] duration-[var(--dur-fast)]"
            :class="progressColorClass"
            :style="{ width: `${Math.min(progressPercent, 100)}%` }"
          ></div>
        </div>

        <!-- 错误提示 -->
        <div
          v-if="hasError"
          id="chat-message-input-error"
          class="absolute right-2 top-2 text-destructive"
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

      <shimmer-button
        :disabled="!canSend"
        class="flex items-center justify-center w-11 h-11 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed text-white shadow-glow-sm ring-1 ring-primary/40"
        background="oklch(var(--primary))"
        shimmer-color="oklch(1 0 0 / 0.6)"
        border-radius="0.5rem"
        title="发送消息"
        aria-label="发送消息"
        @click="handleSend"
      >
        <send-icon class="w-4 h-4" />
      </shimmer-button>
    </div>

    <!-- 字符计数和提示 -->
    <div class="flex flex-wrap justify-between items-center mt-2 text-xs text-muted-foreground gap-x-4 gap-y-1">
      <div class="flex items-center gap-4">
        <span :class="counterColorClass">{{ message.length }}/{{ maxLength }} 字符</span>
        <span v-if="disabled" class="text-orange-700 dark:text-orange-300">{{ statusText }}</span>
      </div>
      <div class="text-[10px] text-foreground/70">Shift+Enter 换行 · Enter 发送 · Esc 清空 · Ctrl+L 跳到底</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { SendIcon } from '@/components/common/icons';
import ShimmerButton from '@/components/ui/ShimmerButton.vue';
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
  placeholder: '输入你的问题...(Shift+Enter 换行 · Enter 发送 · Esc 清空)'
});

const emit = defineEmits<{
  send: [message: string]
  input: [message: string]
}>();

const message = ref('');
const { textareaRef: messageInput, resize: adjustTextareaHeight } = useAutoResizeTextarea({ maxHeight: 120 });

// 字数占比（可超过 100% 用于触发主动锁定）
const progressPercent = computed<number>(() =>
  props.maxLength > 0 ? (message.value.length / props.maxLength) * 100 : 0
);

// 进度条颜色阶梯：< 80% primary / 80-100% 橙黄 / ≥ 100% 红
const progressColorClass = computed<string>(() => {
  const p = progressPercent.value;
  if (p >= 100) { return 'bg-[oklch(0.6_0.22_27)]'; }
  if (p >= 80) { return 'bg-[oklch(0.7_0.15_60)]'; }
  return 'bg-primary';
});

const counterColorClass = computed<string>(() => {
  const p = progressPercent.value;
  if (p >= 100) { return 'text-destructive font-medium'; }
  if (p >= 80) { return 'text-orange-700 dark:text-orange-300'; }
  return '';
});

const hasError = computed(() => message.value.length > props.maxLength);

// 主动锁定：超出 maxLength 时禁用输入框（plan P5 第 263 行要求），
// 不依赖 disabled prop（disabled 是外部"AI 正在响应"控制的语义）
const isLocked = computed<boolean>(() =>
  props.disabled || message.value.length > props.maxLength
);

const canSend = computed(() => {
  return !props.disabled && message.value.trim().length > 0 && message.value.length <= props.maxLength;
});

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
  // Escape：清空当前输入，不影响对话历史。仅在 textarea 内监听，
  // 避免全局 Escape 干扰对话框、菜单等
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

defineExpose({ focus, clear, fillText });
</script>

<style scoped>
textarea { field-sizing: content; }
</style>
