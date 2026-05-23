import { onMounted, onUnmounted } from 'vue';

interface UseAiKeyboardOptions {
  /** Ctrl/Cmd + K 触发的回调，通常用于清空当前对话 */
  onClear: () => void
  /** Ctrl/Cmd + L 触发的回调，通常用于滚动到消息列表底部 */
  onScrollToBottom?: () => void
}

/**
 * AI 对话面板的全局快捷键监听。
 *
 * - Ctrl/Cmd + K → 清空当前对话（onClear）
 * - Ctrl/Cmd + L → 滚动到最新消息（onScrollToBottom，可选）
 *
 * 其它键位（Enter / Shift+Enter / Escape 在 textarea 内）由 `ChatInput`
 * 子组件内部处理，不在此 composable 范围。
 */
export function useAiKeyboard(options: UseAiKeyboardOptions): void {
  const handler = (event: KeyboardEvent): void => {
    if (!(event.ctrlKey || event.metaKey)) { return; }
    const key = event.key.toLowerCase();
    if (key === 'k') {
      event.preventDefault();
      options.onClear();
      return;
    }
    if (key === 'l' && options.onScrollToBottom !== undefined) {
      event.preventDefault();
      options.onScrollToBottom();
    }
  };

  onMounted(() => document.addEventListener('keydown', handler));
  onUnmounted(() => document.removeEventListener('keydown', handler));
}
