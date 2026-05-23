<template>
  <div
    v-if="thinking.content !== ''"
    role="log"
    aria-live="polite"
    :aria-busy="isBusy ? 'true' : 'false'"
    class="thinking-block ml-7 mb-2 p-3 rounded-lg border border-blue-200 dark:border-blue-800"
  >
    <div class="flex items-center gap-2 mb-2">
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
      </template>
    </div>
    <div class="thinking-content text-sm whitespace-pre-wrap leading-relaxed">
      {{ thinking.content }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ThinkingContent } from '@/types/chat';

interface Props {
  thinking: ThinkingContent
  isStreaming?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isStreaming: false
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
.thinking-content {
  color: var(--thinking-fg);
}
.thinking-title {
  color: color-mix(in oklch, var(--thinking-fg) 85%, oklch(var(--primary)) 15%);
}
.thinking-meta {
  color: color-mix(in oklch, var(--thinking-fg) 60%, transparent);
}
</style>
