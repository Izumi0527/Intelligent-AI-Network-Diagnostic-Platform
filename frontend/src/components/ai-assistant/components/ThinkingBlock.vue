<template>
  <div
    v-if="thinking.content !== ''"
    role="log"
    aria-live="polite"
    :aria-busy="isBusy ? 'true' : 'false'"
    class="thinking-block ml-7 mb-2 p-3 rounded-lg border bg-gradient-to-r from-blue-50 to-purple-50 border-blue-200 dark:from-blue-950/40 dark:to-purple-950/40 dark:border-blue-800"
  >
    <div class="flex items-center gap-2 mb-2">
      <template v-if="isStreaming">
        <span
          class="w-2 h-2 bg-blue-400 rounded-full animate-pulse"
          aria-hidden="true"
        ></span>
        <span class="text-blue-700 dark:text-blue-200 text-xs font-medium">AI助手思考中</span>
        <span class="text-blue-400 dark:text-blue-300 text-[10px]">正在思考...</span>
      </template>
      <template v-else>
        <span class="text-blue-600 dark:text-blue-300 text-sm" aria-hidden="true">🤔</span>
        <span class="text-blue-700 dark:text-blue-200 text-xs font-medium">AI思考过程</span>
        <span
          v-if="!thinking.isComplete"
          class="text-blue-500 dark:text-blue-300 text-xs"
        >思考中...</span>
      </template>
    </div>
    <div class="text-sm text-blue-800 dark:text-blue-100 whitespace-pre-wrap leading-relaxed">
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
