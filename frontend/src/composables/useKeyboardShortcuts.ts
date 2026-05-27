/**
 * 全局键盘快捷键 composable。注册一次即可在应用范围内监听：
 *   ⌘/Ctrl + K      → 打开命令面板
 *   ⌘/Ctrl + ⇧ + K  → 清空当前对话（迁出自 useAiKeyboard 的 Ctrl+K）
 *   ⌘/Ctrl + \      → 折叠/展开 AI 助手面板
 *   ⌘/Ctrl + .      → 聚焦输入框
 *   ⌘/Ctrl + /      → 切换深浅色主题
 *   Escape          → 关闭命令面板 / popover (命令面板内自处理)
 *
 * 实现选择：原生 keydown 监听器优于 useMagicKeys —— 后者不易在 SSR-free Vite Vue3 中
 * 拦截到原始事件的 preventDefault；本场景需要阻止浏览器默认 ⌘K（书签搜索）等行为。
 */
import { onMounted, onUnmounted } from 'vue';
import { useUiStore } from '@/stores/ui';
import { useAppStore } from '@/stores/app';

interface UseKeyboardShortcutsOptions {
  /** 清空对话回调（迁出自原 useAiKeyboard Ctrl+K）*/
  onClearChat?: () => void;
  /** 聚焦输入框回调 */
  onFocusInput?: () => void;
}

export function useKeyboardShortcuts(options: UseKeyboardShortcutsOptions = {}): void {
  const ui = useUiStore();
  const app = useAppStore();

  const handler = (event: KeyboardEvent): void => {
    const isMod = event.ctrlKey || event.metaKey;

    // 命令面板内的按键先放行（面板内部自己处理）
    if (ui.isCommandPaletteOpen) {
      if (event.key === 'Escape') {
        ui.closeCommandPalette();
        event.preventDefault();
      }
      return;
    }

    if (!isMod) { return; }

    const key = event.key.toLowerCase();

    // ⌘⇧K → 清空对话（先判断，避免被 ⌘K 抢占）
    if (event.shiftKey && key === 'k') {
      event.preventDefault();
      options.onClearChat?.();
      return;
    }

    // ⌘K → 打开命令面板
    if (!event.shiftKey && key === 'k') {
      event.preventDefault();
      ui.toggleCommandPalette();
      return;
    }

    // ⌘\ → 折叠 AI 助手
    if (key === '\\') {
      event.preventDefault();
      ui.toggleAiPane();
      return;
    }

    // ⌘. → 聚焦输入框
    if (key === '.') {
      event.preventDefault();
      options.onFocusInput?.();
      return;
    }

    // ⌘/ → 切换主题
    if (key === '/') {
      event.preventDefault();
      app.setDarkMode(!app.isDarkMode);
      return;
    }
  };

  onMounted(() => {
    document.addEventListener('keydown', handler);
  });

  onUnmounted(() => {
    document.removeEventListener('keydown', handler);
  });
}
