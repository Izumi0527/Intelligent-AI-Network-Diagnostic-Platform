<template>
  <div
    class="message-meta"
    :class="[
      role === 'user' ? 'message-meta--user' : '',
      compact ? 'message-meta--compact' : ''
    ]"
  >
    <template v-if="!compact">
      <span class="message-meta__avatar" aria-hidden="true">
        <span v-html="roleIcon" />
      </span>
      <span class="message-meta__role">{{ roleLabel }}</span>
    </template>
    <time
      v-if="hasTimestamp"
      :datetime="isoTimestamp"
      class="message-meta__time"
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
  if (props.role === 'user') { return '你'; }
  if (props.role === 'assistant') { return 'AI'; }
  return '系统';
});

const userIconSvg = '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>';
const botIconSvg = '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><line x1="8" y1="16" x2="8" y2="16"/><line x1="16" y1="16" x2="16" y2="16"/></svg>';
const systemIconSvg = '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M12 1v6m0 10v6"/></svg>';

const roleIcon = computed<string>(() => {
  if (props.role === 'user') { return userIconSvg; }
  if (props.role === 'assistant') { return botIconSvg; }
  return systemIconSvg;
});
</script>

<style scoped>
.message-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  font-size: 10px;
  color: var(--muted-foreground);
}

.message-meta--user {
  flex-direction: row-reverse;
  justify-content: flex-start;
  margin-right: 28px;
}

.message-meta--assistant,
.message-meta:not(.message-meta--user) {
  margin-left: 28px;
}

.message-meta--compact {
  margin-bottom: 2px;
  opacity: 0.55;
}

.message-meta__avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 4px;
  background-color: var(--muted);
  color: var(--muted-foreground);
}

.message-meta--user .message-meta__avatar {
  background-color: color-mix(in oklch, var(--primary) 14%, transparent);
  color: var(--primary);
}

.message-meta__role {
  font-family: var(--app-font-mono);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: color-mix(in oklch, var(--foreground) 70%, transparent);
}

.message-meta__time {
  font-family: var(--app-font-mono);
  font-variant-numeric: tabular-nums;
  font-size: 10px;
  color: color-mix(in oklch, var(--muted-foreground) 80%, transparent);
}
</style>
