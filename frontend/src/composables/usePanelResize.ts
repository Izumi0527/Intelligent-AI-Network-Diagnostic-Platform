/**
 * 拖拽分割条 composable：维护拖拽中状态、计算新的分割比例并写回 useUiStore。
 * 数学：基于容器宽度和指针 X 坐标计算 ratio = (clientX - left) / width * 100。
 */
import { ref, onUnmounted, type Ref } from 'vue';
import { useUiStore } from '@/stores/ui';

interface UsePanelResizeReturn {
  isDragging: Ref<boolean>;
  startDrag: (event: PointerEvent, containerEl: HTMLElement) => void;
}

export function usePanelResize(): UsePanelResizeReturn {
  const ui = useUiStore();
  const isDragging = ref(false);
  let containerEl: HTMLElement | null = null;
  let pointerId: number | null = null;

  const onPointerMove = (event: PointerEvent): void => {
    if (containerEl === null) { return; }
    const rect = containerEl.getBoundingClientRect();
    if (rect.width === 0) { return; }
    const ratio = ((event.clientX - rect.left) / rect.width) * 100;
    ui.setSplitRatio(ratio);
  };

  const stopDrag = (): void => {
    isDragging.value = false;
    document.removeEventListener('pointermove', onPointerMove);
    document.removeEventListener('pointerup', stopDrag);
    document.removeEventListener('pointercancel', stopDrag);
    document.body.style.userSelect = '';
    document.body.style.cursor = '';
    containerEl = null;
    pointerId = null;
  };

  const startDrag = (event: PointerEvent, el: HTMLElement): void => {
    event.preventDefault();
    containerEl = el;
    pointerId = event.pointerId;
    isDragging.value = true;
    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'col-resize';
    document.addEventListener('pointermove', onPointerMove);
    document.addEventListener('pointerup', stopDrag);
    document.addEventListener('pointercancel', stopDrag);
  };

  onUnmounted(() => {
    if (isDragging.value) { stopDrag(); }
  });

  // 防御性：让 TS 知道 pointerId 被读取（用于将来扩展，如多指触控）
  void pointerId;

  return { isDragging, startDrag };
}
