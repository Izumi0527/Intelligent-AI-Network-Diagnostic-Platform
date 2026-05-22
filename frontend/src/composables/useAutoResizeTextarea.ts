import { ref, nextTick, type Ref } from 'vue';

interface UseAutoResizeTextareaOptions {
  /** 自适应高度的上限（px），默认 120 */
  maxHeight?: number
  /** 初始与重置后的最小高度（px），默认 32 */
  minHeight?: number
}

interface UseAutoResizeTextareaReturn {
  textareaRef: Ref<HTMLTextAreaElement | null>;
  resize: () => Promise<void>;
  reset: () => void;
}

/**
 * textarea 自适应高度 composable。
 *
 * 给 ref 绑到 textarea 元素，调用 `resize()` 在 input 之后让高度跟随
 * 内容增长（受 maxHeight 限制），调用 `reset()` 在清空内容后回到 minHeight。
 */
export function useAutoResizeTextarea(options: UseAutoResizeTextareaOptions = {}): UseAutoResizeTextareaReturn {
  const { maxHeight = 120, minHeight = 32 } = options;
  const textareaRef = ref<HTMLTextAreaElement | null>(null);

  const resize = async (): Promise<void> => {
    await nextTick();
    const el = textareaRef.value;
    if (!el) { return; }
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, maxHeight)}px`;
  };

  const reset = (): void => {
    if (textareaRef.value) {
      textareaRef.value.style.height = `${minHeight}px`;
    }
  };

  return { textareaRef, resize, reset };
}
