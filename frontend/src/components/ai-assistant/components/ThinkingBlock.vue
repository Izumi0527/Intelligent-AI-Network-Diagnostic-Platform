<template>
  <div
    v-if="thinking.content !== ''"
    role="log"
    aria-live="polite"
    :aria-busy="isBusy ? 'true' : 'false'"
    class="thinking-block ml-7 mb-2 rounded-lg border border-blue-200 dark:border-blue-800"
  >
    <button
      type="button"
      class="thinking-header w-full flex items-center gap-2 px-3 py-2 text-left rounded-t-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[oklch(var(--primary)/0.5)]"
      :class="isStreaming ? 'cursor-default' : 'cursor-pointer hover:bg-blue-100/40 dark:hover:bg-blue-900/30'"
      :disabled="isStreaming"
      :aria-expanded="isExpanded || isStreaming ? 'true' : 'false'"
      aria-controls="thinking-content-region"
      @click="toggleExpanded"
    >
      <template v-if="isStreaming">
        <span
          class="w-2 h-2 bg-blue-400 rounded-full animate-pulse"
          aria-hidden="true"
        ></span>
        <span class="thinking-title text-xs font-medium">AI助手思考中</span>
        <span class="thinking-meta text-[10px]">正在思考...</span>
      </template>
      <template v-else>
        <span class="thinking-title text-sm" aria-hidden="true">🤔</span>
        <span class="thinking-title text-xs font-medium">AI思考过程</span>
        <span
          v-if="!thinking.isComplete"
          class="thinking-meta text-xs"
        >思考中...</span>
        <span class="flex-1"></span>
        <span
          v-if="!isExpanded && previewText !== ''"
          class="thinking-meta text-[11px] truncate max-w-[55%]"
          :title="previewText"
        >{{ previewText }}</span>
        <chevron-down-icon
          class="thinking-chevron h-4 w-4 transition-transform duration-200"
          :class="isExpanded ? 'rotate-0' : '-rotate-90'"
        />
      </template>
    </button>
    <div
      v-show="isExpanded || isStreaming"
      id="thinking-content-region"
      class="thinking-content text-sm whitespace-pre-wrap leading-relaxed px-3 pb-3"
    >
      {{ thinking.content }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import type { ThinkingContent } from '@/types/chat';
import { ChevronDownIcon } from '@/components/common/icons';

interface Props {
  thinking: ThinkingContent
  isStreaming?: boolean
  defaultExpanded?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isStreaming: false,
  defaultExpanded: true
});

// 完成态可折叠；流式态强制展开（disabled button + 视觉脉冲点）
// eslint-disable-next-line vue/no-setup-props-destructure -- defaultExpanded 仅作初始值，无需响应性
const isExpanded = ref<boolean>(props.defaultExpanded);

// 流式 → 完成态切换时按 defaultExpanded 重置（避免遗留奇怪状态）
watch(() => props.isStreaming, (newStreaming, oldStreaming) => {
  if (oldStreaming === true && newStreaming === false) {
    isExpanded.value = props.defaultExpanded;
  }
});

const toggleExpanded = (): void => {
  if (props.isStreaming) { return; }
  isExpanded.value = !isExpanded.value;
};

// 折叠态预览：思考首行前 80 字符（剥除多余换行）
const previewText = computed<string>(() => {
  const cleaned = props.thinking.content.replace(/\s+/g, ' ').trim();
  if (cleaned.length <= 80) { return cleaned; }
  return `${cleaned.slice(0, 80)}…`;
});

// aria-busy=true 条件：实时流式态，或历史态但 thinking 尚未标记完成
const isBusy = computed<boolean>(() =>
  props.isStreaming || !props.thinking.isComplete
);
</script>

<style scoped>
.thinking-block {
  background: var(--thinking-bg);
}
.thinking-header {
  background: transparent;
  border: none;
  color: inherit;
}
.thinking-header:disabled {
  cursor: default;
}
.thinking-content {
  color: var(--thinking-fg);
}
.thinking-title {
  color: color-mix(in oklch, var(--thinking-fg) 85%, oklch(var(--primary)) 15%);
}
.thinking-meta {
  color: color-mix(in oklch, var(--thinking-fg) 60%, transparent);
}
.thinking-chevron {
  color: color-mix(in oklch, var(--thinking-fg) 70%, transparent);
}
</style>
