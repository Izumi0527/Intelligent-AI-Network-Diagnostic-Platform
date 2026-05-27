import { onMounted, onUnmounted } from 'vue';

interface UseAiKeyboardOptions {
  /** Ctrl/Cmd + L 触发的回调：滚动到消息列表底部 */
  onScrollToBottom?: () => void
}

/**
 * AI 对话面板的局部快捷键。
 *
 * - Ctrl/Cmd + L → 滚动到最新消息（可选）
 *
 * 注意：⌘K（命令面板）与 ⌘⇧K（清空对话）已迁出至全局 useKeyboardShortcuts，
 * 此 composable 只保留对话面板内的轻量便捷键。
 * 其它键位（Enter / Shift+Enter / Escape 在 textarea 内）由 ChatInput 子组件处理。
 */
export function useAiKeyboard(options: UseAiKeyboardOptions): void {
  const handler = (event: KeyboardEvent): void => {
    if (!(event.ctrlKey || event.metaKey)) { return; }
    const key = event.key.toLowerCase();
    if (key === 'l' && options.onScrollToBottom !== undefined) {
      event.preventDefault();
      options.onScrollToBottom();
    }
  };

  onMounted(() => document.addEventListener('keydown', handler));
  onUnmounted(() => document.removeEventListener('keydown', handler));
}
