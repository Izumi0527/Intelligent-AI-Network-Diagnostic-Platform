<template>
  <div
    v-if="thinking.content !== ''"
    role="log"
    aria-live="polite"
    :aria-busy="isBusy ? 'true' : 'false'"
    class="thinking-block ml-7 mb-2 rounded-lg border"
    :class="isStreaming
      ? 'border-blue-400 dark:border-blue-600'
      : 'border-blue-200 dark:border-blue-800'"
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
        <span
          v-else-if="formattedTime !== ''"
          class="thinking-meta text-[11px]"
          :title="absoluteTime"
        >{{ formattedTime }}</span>
        <transition name="thinking-check">
          <span
            v-if="showCheckmark"
            class="thinking-check inline-flex items-center text-green-600 dark:text-green-400 text-sm font-semibold"
            aria-hidden="true"
          >✓</span>
        </transition>
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
    <transition
      name="thinking-collapse"
      @enter="onCollapseEnter"
      @after-enter="onCollapseAfterEnter"
      @leave="onCollapseLeave"
    >
      <div
        v-show="isExpanded || isStreaming"
        id="thinking-content-region"
        class="thinking-content text-sm whitespace-pre-wrap leading-relaxed px-3 pb-3 overflow-hidden"
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

// 完成提示绿勾：流式 → 完成态切换瞬间淡入 → 1.5s 后自动消失
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

// 折叠态预览：思考首行前 80 字符（剥除多余空白）
const previewText = computed<string>(() => {
  const cleaned = props.thinking.content.replace(/\s+/g, ' ').trim();
  if (cleaned.length <= 80) { return cleaned; }
  return `${cleaned.slice(0, 80)}…`;
});

// aria-busy=true 条件：实时流式态，或历史态但 thinking 尚未标记完成
const isBusy = computed<boolean>(() =>
  props.isStreaming || !props.thinking.isComplete
);

// 相对时间：每 30s 触发一次重算，组件卸载清理定时器
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

// 折叠展开 max-height + opacity 过渡：用 Vue Transition JS 钩子，避免给 Tailwind 写死 max-h
const onCollapseEnter = (el: Element): void => {
  const node = el as HTMLElement;
  node.style.maxHeight = '0px';
  node.style.opacity = '0';
  // 强制 reflow 让起始值生效，再切换到目标值触发过渡
  void node.offsetHeight;
  node.style.transition = 'max-height 240ms var(--ease-out, ease), opacity 200ms var(--ease-out, ease)';
  node.style.maxHeight = `${node.scrollHeight}px`;
  node.style.opacity = '1';
};

const onCollapseAfterEnter = (el: Element): void => {
  const node = el as HTMLElement;
  // 还原 inline style，避免影响流式期内容追加导致的 scrollHeight 变化
  node.style.maxHeight = '';
  node.style.transition = '';
  node.style.opacity = '';
};

const onCollapseLeave = (el: Element): void => {
  const node = el as HTMLElement;
  node.style.maxHeight = `${node.scrollHeight}px`;
  node.style.opacity = '1';
  void node.offsetHeight;
  node.style.transition = 'max-height 200ms var(--ease-out, ease), opacity 160ms var(--ease-out, ease)';
  node.style.maxHeight = '0px';
  node.style.opacity = '0';
};
</script>

<style scoped>
.thinking-block {
  background: var(--thinking-bg);
  transition: border-color 300ms var(--ease-out, ease), background 300ms var(--ease-out, ease);
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

/* 完成态绿勾淡入淡出 */
.thinking-check-enter-from,
.thinking-check-leave-to {
  opacity: 0;
}
.thinking-check-enter-active {
  transition: opacity 200ms var(--ease-out, ease);
}
.thinking-check-leave-active {
  transition: opacity 240ms var(--ease-out, ease);
}

/* 尊重 prefers-reduced-motion：移除装饰性过渡 */
@media (prefers-reduced-motion: reduce) {
  .thinking-block,
  .thinking-chevron,
  .thinking-check-enter-active,
  .thinking-check-leave-active {
    transition: none !important;
  }
}
</style>
