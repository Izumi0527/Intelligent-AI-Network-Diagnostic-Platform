<template>
  <div
    role="log"
    aria-live="polite"
    :aria-busy="isBusy ? 'true' : 'false'"
    class="thinking-block"
    :class="isStreaming ? 'thinking-block--streaming' : 'thinking-block--done'"
  >
    <button
      type="button"
      class="thinking-header"
      :class="{ 'thinking-header--locked': isStreaming }"
      :disabled="isStreaming"
      :aria-expanded="isExpanded || isStreaming ? 'true' : 'false'"
      aria-controls="thinking-content-region"
      @click="toggleExpanded"
    >
      <template v-if="isStreaming">
        <packet-signal mode="sending" />
        <span class="thinking-title">AI 助手正在思考</span>
        <span class="thinking-meta">正在分析…</span>
      </template>
      <template v-else>
        <span class="thinking-icon" aria-hidden="true" v-html="radioIconSvg" />
        <span class="thinking-title">思考过程</span>
        <span
          v-if="!thinking.isComplete"
          class="thinking-meta"
        >未完成</span>
        <span
          v-else-if="formattedTime !== ''"
          class="thinking-meta thinking-meta--time"
          :title="absoluteTime"
        >{{ formattedTime }}</span>
        <transition name="thinking-check">
          <span
            v-if="showCheckmark"
            class="thinking-check"
            aria-hidden="true"
          >✓</span>
        </transition>
        <span class="thinking-spacer" />
        <span
          v-if="!isExpanded && previewText !== ''"
          class="thinking-preview"
          :title="previewText"
        >{{ previewText }}</span>
        <chevron-down-icon
          class="thinking-chevron"
          :class="{ 'thinking-chevron--collapsed': !isExpanded }"
        />
      </template>
    </button>
    <transition
      name="thinking-collapse"
      @enter="onCollapseEnter"
      @after-enter="onCollapseAfterEnter"
      @leave="onCollapseLeave"
    >
      <div
        v-show="isExpanded || isStreaming"
        id="thinking-content-region"
        class="thinking-content"
      >
        {{ thinking.content }}
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import type { ThinkingContent } from '@/types/chat';
import { ChevronDownIcon } from '@/components/common/icons';
import PacketSignal from '@/components/decoration/PacketSignal.vue';

interface Props {
  thinking: ThinkingContent
  isStreaming?: boolean
  defaultExpanded?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isStreaming: false,
  defaultExpanded: true
});

const radioIconSvg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="2"/><path d="M16.24 7.76a6 6 0 0 1 0 8.49m-8.48-.01a6 6 0 0 1 0-8.49m11.31-2.82a10 10 0 0 1 0 14.14m-14.14 0a10 10 0 0 1 0-14.14"/></svg>';

// eslint-disable-next-line vue/no-setup-props-destructure
const isExpanded = ref<boolean>(props.defaultExpanded);

const showCheckmark = ref<boolean>(false);
let checkmarkTimer: ReturnType<typeof setTimeout> | null = null;

watch(() => props.isStreaming, (newStreaming, oldStreaming) => {
  if (oldStreaming === true && newStreaming === false) {
    isExpanded.value = props.defaultExpanded;
    showCheckmark.value = true;
    if (checkmarkTimer !== null) { clearTimeout(checkmarkTimer); }
    checkmarkTimer = setTimeout(() => { showCheckmark.value = false; }, 1500);
  }
});

const toggleExpanded = (): void => {
  if (props.isStreaming) { return; }
  isExpanded.value = !isExpanded.value;
};

const previewText = computed<string>(() => {
  const cleaned = props.thinking.content.replace(/\s+/g, ' ').trim();
  if (cleaned.length <= 80) { return cleaned; }
  return `${cleaned.slice(0, 80)}…`;
});

const isBusy = computed<boolean>(() =>
  props.isStreaming || !props.thinking.isComplete
);

const nowMs = ref<number>(Date.now());
let nowTimer: ReturnType<typeof setInterval> | null = null;

onMounted(() => {
  nowTimer = setInterval(() => { nowMs.value = Date.now(); }, 30_000);
});

onUnmounted(() => {
  if (nowTimer !== null) { clearInterval(nowTimer); nowTimer = null; }
  if (checkmarkTimer !== null) { clearTimeout(checkmarkTimer); checkmarkTimer = null; }
});

const formattedTime = computed<string>(() => {
  const ts = props.thinking.timestamp;
  if (!Number.isFinite(ts) || ts <= 0) { return ''; }
  const diffSec = Math.max(0, Math.floor((nowMs.value - ts) / 1000));
  if (diffSec < 10) { return '刚刚'; }
  if (diffSec < 60) { return `${diffSec}s 前`; }
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) { return `${diffMin}m 前`; }
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) { return `${diffHour}h 前`; }
  const diffDay = Math.floor(diffHour / 24);
  return `${diffDay}d 前`;
});

const absoluteTime = computed<string>(() => {
  const ts = props.thinking.timestamp;
  if (!Number.isFinite(ts) || ts <= 0) { return ''; }
  return new Date(ts).toLocaleString('zh-CN');
});

const onCollapseEnter = (el: Element): void => {
  const node = el as HTMLElement;
  node.style.maxHeight = '0px';
  node.style.opacity = '0';
  void node.offsetHeight;
  node.style.transition = 'max-height var(--dur-slow) var(--ease-standard), opacity var(--dur-base) var(--ease-standard)';
  node.style.maxHeight = `${node.scrollHeight}px`;
  node.style.opacity = '1';
};

const onCollapseAfterEnter = (el: Element): void => {
  const node = el as HTMLElement;
  node.style.maxHeight = '';
  node.style.transition = '';
  node.style.opacity = '';
};

const onCollapseLeave = (el: Element): void => {
  const node = el as HTMLElement;
  node.style.maxHeight = `${node.scrollHeight}px`;
  node.style.opacity = '1';
  void node.offsetHeight;
  node.style.transition = 'max-height var(--dur-base) var(--ease-exit), opacity var(--dur-exit) var(--ease-exit)';
  node.style.maxHeight = '0px';
  node.style.opacity = '0';
};
</script>

<style scoped>
.thinking-block {
  margin-left: 28px;
  margin-bottom: 8px;
  border: 1px solid var(--thinking-border);
  border-radius: var(--radius);
  background: var(--thinking-bg);
  transition:
    border-color var(--dur-base) var(--ease-standard),
    background-color var(--dur-base) var(--ease-standard);
}

.thinking-block--streaming {
  border-color: color-mix(in oklch, var(--primary) 38%, transparent);
}

.thinking-header {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  text-align: left;
  background: transparent;
  border: none;
  color: inherit;
  cursor: pointer;
  border-radius: var(--radius);
  transition: background-color var(--dur-enter) var(--ease-standard);
}

.thinking-header:hover:not(:disabled) {
  background-color: color-mix(in oklch, var(--primary) 6%, transparent);
}

.thinking-header:focus-visible {
  outline: 2px solid color-mix(in oklch, var(--primary) 60%, transparent);
  outline-offset: -2px;
}

.thinking-header--locked {
  cursor: default;
}

.thinking-icon {
  color: var(--primary);
  display: inline-flex;
  align-items: center;
}

.thinking-title {
  font-size: 11px;
  font-weight: 500;
  font-family: var(--app-font-mono);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: color-mix(in oklch, var(--thinking-fg) 85%, transparent);
}

.thinking-meta {
  font-size: 10px;
  color: color-mix(in oklch, var(--thinking-fg) 55%, transparent);
}

.thinking-meta--time {
  font-family: var(--app-font-mono);
}

.thinking-check {
  display: inline-flex;
  align-items: center;
  color: var(--success);
  font-size: 13px;
  font-weight: 600;
}

.thinking-spacer { flex: 1; }

.thinking-preview {
  font-size: 11px;
  color: color-mix(in oklch, var(--thinking-fg) 60%, transparent);
  max-width: 55%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.thinking-chevron {
  width: 14px;
  height: 14px;
  color: color-mix(in oklch, var(--thinking-fg) 60%, transparent);
  transition: transform var(--dur-enter) var(--ease-standard);
}

.thinking-chevron--collapsed {
  transform: rotate(-90deg);
}

.thinking-content {
  padding: 0 12px 10px 12px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--thinking-fg);
  white-space: pre-wrap;
  overflow: hidden;
  font-family: var(--app-font-mono);
}

.thinking-check-enter-from,
.thinking-check-leave-to { opacity: 0; }
.thinking-check-enter-active { transition: opacity var(--dur-base) var(--ease-standard); }
.thinking-check-leave-active { transition: opacity var(--dur-slow) var(--ease-exit); }

@media (prefers-reduced-motion: reduce) {
  .thinking-block,
  .thinking-chevron,
  .thinking-check-enter-active,
  .thinking-check-leave-active {
    transition: none !important;
  }
}
</style>
