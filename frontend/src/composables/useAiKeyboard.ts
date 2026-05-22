import { onMounted, onUnmounted } from 'vue';

interface UseAiKeyboardOptions {
  /** Ctrl/Cmd + K 触发的回调，通常用于清空当前对话 */
  onClear: () => void
}

/**
 * AI 对话面板的全局快捷键监听。
 *
 * 当前仅监听 Ctrl/Cmd + K → 清空。其它键位（如 Enter / Shift+Enter）由
 * `ChatInput` 子组件内部处理，不在此 composable 范围。
 */
export function useAiKeyboard(options: UseAiKeyboardOptions): void {
  const handler = (event: KeyboardEvent): void => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      options.onClear();
    }
  };

  onMounted(() => document.addEventListener('keydown', handler));
  onUnmounted(() => document.removeEventListener('keydown', handler));
}
