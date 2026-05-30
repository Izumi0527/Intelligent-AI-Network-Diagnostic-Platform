<template>
  <button
    type="button"
    class="drag-handle"
    :class="{ 'drag-handle--dragging': isDragging }"
    role="separator"
    aria-label="调整面板宽度"
    aria-orientation="vertical"
    :aria-valuenow="ratio"
    aria-valuemin="25"
    aria-valuemax="75"
    @pointerdown="onPointerDown"
    @dblclick="onDoubleClick"
    @keydown="onKeyDown"
  >
    <span class="drag-handle__bar" />
  </button>
</template>

<script setup lang="ts">
/**
 * 桌面端可拖拽分割条。
 * - 点击 + 拖拽改变两侧面板比例
 * - 双击重置到 66/34 默认值
 * - Arrow Left/Right 键盘步进 (a11y)
 */
import { computed } from 'vue';
import { useUiStore } from '@/stores/ui';
import { usePanelResize } from '@/composables/usePanelResize';

const props = defineProps<{
  /** 容器元素引用，用于计算 ratio */
  containerRef: HTMLElement | null
}>();

const ui = useUiStore();
const { isDragging, startDrag } = usePanelResize();

const ratio = computed(() => Math.round(ui.splitRatio));

const onPointerDown = (event: PointerEvent): void => {
  if (props.containerRef === null) { return; }
  startDrag(event, props.containerRef);
};

const onDoubleClick = (): void => {
  ui.setSplitRatio(66);
};

const onKeyDown = (event: KeyboardEvent): void => {
  const step = event.shiftKey ? 5 : 2;
  if (event.key === 'ArrowLeft') {
    event.preventDefault();
    ui.setSplitRatio(ui.splitRatio - step);
  } else if (event.key === 'ArrowRight') {
    event.preventDefault();
    ui.setSplitRatio(ui.splitRatio + step);
  }
};
</script>

<style scoped>
.drag-handle {
  flex: 0 0 6px;
  position: relative;
  background: transparent;
  border: none;
  padding: 0;
  cursor: col-resize;
  outline: none;
  transition: background-color var(--dur-base) var(--ease-standard);
}

.drag-handle:hover,
.drag-handle:focus-visible {
  background-color: color-mix(in oklch, var(--primary) 12%, transparent);
}

.drag-handle__bar {
  position: absolute;
  inset: 0;
  margin: auto;
  width: 1px;
  height: 100%;
  background-color: var(--border);
  transition:
    background-color var(--dur-base) var(--ease-standard),
    box-shadow var(--dur-base) var(--ease-standard),
    width var(--dur-base) var(--ease-standard);
}

.drag-handle:hover .drag-handle__bar,
.drag-handle:focus-visible .drag-handle__bar,
.drag-handle--dragging .drag-handle__bar {
  width: 2px;
  background-color: var(--primary);
  box-shadow: 0 0 8px var(--hud-glow);
}

.drag-handle--dragging {
  background-color: color-mix(in oklch, var(--primary) 16%, transparent);
}

@media (max-width: 768px) {
  .drag-handle {
    display: none;
  }
}
</style>
