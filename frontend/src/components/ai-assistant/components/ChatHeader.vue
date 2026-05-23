<template>
  <div class="p-4 border-b border-border/60 bg-transparent rounded-t-xl">
    <div class="flex items-center justify-between mb-3">
      <h2 class="text-lg font-semibold text-foreground">
        AI智能助手
      </h2>
      <div class="flex gap-2">
        <shimmer-button
          class="flex items-center gap-1 rounded-lg border border-border/40 px-2.5 py-1.5 text-xs font-medium"
          background="oklch(var(--secondary))"
          shimmer-color="oklch(var(--accent-purple) / 0.5)"
          border-radius="0.5rem"
          title="清空当前对话"
          style="color: oklch(var(--secondary-foreground))"
          @click="openConfirm"
        >
          <clear-icon class="w-3.5 h-3.5 relative z-10" aria-hidden="true" />
          <span
            class="hidden sm:inline relative z-10"
            style="color: oklch(var(--secondary-foreground))"
          >清空对话</span>
        </shimmer-button>
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
import ShimmerButton from '@/components/ui/ShimmerButton.vue';
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
