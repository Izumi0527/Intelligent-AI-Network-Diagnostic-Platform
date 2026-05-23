<template>
  <div
    class="font-medium text-xs flex items-center gap-2 text-muted-foreground transition-opacity duration-[var(--dur-fast)]"
    :class="[
      role === 'user' ? 'flex-row-reverse' : '',
      compact ? 'mb-0.5 opacity-50' : 'mb-1.5 opacity-70 group-hover:opacity-100'
    ]"
  >
    <template v-if="!compact">
      <span
        class="inline-block w-5 h-5 rounded-full overflow-hidden flex items-center justify-center"
        aria-hidden="true"
      >
        <span class="text-xs">{{ roleEmoji }}</span>
      </span>
      <span class="text-foreground/80">{{ roleLabel }}</span>
    </template>
    <time
      v-if="hasTimestamp"
      :datetime="isoTimestamp"
      class="text-muted-foreground/70 text-[10px] tabular-nums"
    >{{ displayTime }}</time>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

interface Props {
  role: 'user' | 'assistant' | 'system'
  timestamp: number | undefined
  compact: boolean | undefined
}

const props = withDefaults(defineProps<Props>(), {
  compact: false
});

const hasTimestamp = computed<boolean>(() =>
  props.timestamp !== undefined && props.timestamp > 0
);

const isoTimestamp = computed<string>(() =>
  hasTimestamp.value ? new Date(props.timestamp ?? 0).toISOString() : ''
);

const displayTime = computed<string>(() => {
  if (!hasTimestamp.value) { return ''; }
  return new Date(props.timestamp ?? 0).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  });
});

const roleLabel = computed<string>(() => {
  if (props.role === 'user') { return '用户'; }
  if (props.role === 'assistant') { return 'AI助手'; }
  return '系统';
});

const roleEmoji = computed<string>(() => {
  if (props.role === 'user') { return '👤'; }
  if (props.role === 'assistant') { return '🤖'; }
  return '⚙️';
});
</script>
