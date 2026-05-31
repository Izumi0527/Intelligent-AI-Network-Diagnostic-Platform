/**
 * 命令面板命令注册表（factory 模式）。
 * CommandPalette.vue 在 setup 中传入 store 依赖, 返回 Command[] 用于渲染与执行。
 */
import type { useUiStore } from '@/stores/ui';
import type { useAppStore } from '@/stores/app';
import type { useAiAssistantStore } from '@/stores/ai-assistant';
import type { useTerminalStore } from '@/stores/terminal';

export interface Command {
  id: string;
  /** 显示名 */
  label: string;
  /** 副标题/描述 */
  hint?: string;
  /** 分组（用于面板内分类显示）*/
  group: '对话' | '导航' | '主题' | '设置' | '终端';
  /** 内联 SVG icon (16x16, currentColor stroke) */
  icon?: string;
  /** 快捷键标签（如 ⌘⇧K）*/
  shortcut?: string;
  /** 命令执行体 */
  action: () => void | Promise<void>;
  /** 关键词（用于搜索匹配, 大小写不敏感）*/
  keywords?: string[];
}

type Stores = {
  ui: ReturnType<typeof useUiStore>;
  app: ReturnType<typeof useAppStore>;
  ai: ReturnType<typeof useAiAssistantStore>;
  terminal: ReturnType<typeof useTerminalStore>;
};

const icon = {
  trash: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/></svg>',
  arrowDown: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/></svg>',
  bot: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><line x1="12" y1="7" x2="12" y2="11"/><line x1="8" y1="16" x2="8" y2="16"/><line x1="16" y1="16" x2="16" y2="16"/></svg>',
  zap: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
  search: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',
  sun: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>',
  panelLeft: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="9" y1="3" x2="9" y2="21"/></svg>',
  refresh: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>',
  plug: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22v-5"/><path d="M9 7V2"/><path d="M15 7V2"/><path d="M6 13V8h12v5a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4z"/></svg>',
};

export function createCommands(stores: Stores, hooks: { onClearChat: () => void; onFocusInput: () => void }): Command[] {
  const { ui, app, ai } = stores;

  return [
    {
      id: 'chat.clear',
      label: '清空当前对话',
      hint: '删除所有消息并开启新会话',
      group: '对话',
      icon: icon.trash,
      shortcut: '⌘⇧K',
      keywords: ['clear', 'reset', '清空', '重置', '新对话'],
      action: (): void => { hooks.onClearChat(); },
    },
    {
      id: 'chat.focus',
      label: '聚焦输入框',
      hint: '光标移到 AI 助手输入区',
      group: '对话',
      icon: icon.zap,
      shortcut: '⌘.',
      keywords: ['focus', 'input', '聚焦', '输入'],
      action: (): void => { hooks.onFocusInput(); },
    },
    {
      id: 'chat.scrollBottom',
      label: '滚动到最新消息',
      group: '对话',
      icon: icon.arrowDown,
      shortcut: '⌘L',
      keywords: ['scroll', 'bottom', '底部', '滚动'],
      action: (): void => {
        // 滚动逻辑在 ChatMessages 内部，通过自定义事件触发
        window.dispatchEvent(new CustomEvent('ai-scroll-to-bottom'));
      },
    },
    {
      id: 'chat.toggleSearch',
      label: ai.searchEnabled ? '关闭联网搜索' : '开启联网搜索',
      group: '对话',
      icon: icon.search,
      keywords: ['search', '搜索', '联网', 'web'],
      action: (): void => { ai.toggleSearchMode(); },
    },
    {
      id: 'theme.toggle',
      label: app.isDarkMode ? '切换到浅色模式' : '切换到深色模式',
      hint: '⌘/',
      group: '主题',
      icon: icon.sun,
      shortcut: '⌘/',
      keywords: ['theme', 'dark', 'light', '主题', '深色', '浅色'],
      action: (): void => { app.setDarkMode(!app.isDarkMode); },
    },
    {
      id: 'layout.toggleAi',
      label: ui.isAiPaneCollapsed ? '展开 AI 助手' : '折叠 AI 助手',
      group: '导航',
      icon: icon.panelLeft,
      shortcut: '⌘\\',
      keywords: ['collapse', 'toggle', 'panel', '折叠', '展开'],
      action: (): void => { ui.toggleAiPane(); },
    },
    {
      id: 'server.recheck',
      label: '重新检查后端连接',
      group: '设置',
      icon: icon.refresh,
      keywords: ['reconnect', 'health', '重连', '健康检查'],
      action: (): void => { void app.checkServerConnection(); },
    },
    {
      id: 'model.recheck',
      label: '重新检查模型连接',
      group: '设置',
      icon: icon.plug,
      keywords: ['model', 'connection', '模型', '重连'],
      action: (): void => { void ai.checkModelConnection(); },
    },
    {
      id: 'bot.greet',
      label: '关于本平台',
      hint: 'NetOps · AI 智能网络故障分析平台',
      group: '设置',
      icon: icon.bot,
      keywords: ['about', 'help', '关于', '帮助'],
      action: (): void => {
        // 简单 about 实现：弹 alert (后续可改为模态)
        window.alert('NetOps · AI 智能网络故障分析平台\n\n基于 Vue 3 + Vite + Tailwind v4 构建\n设计语言：Industrial HUD');
      },
    },
  ];
}

/** Fuzzy 搜索：大小写不敏感的子串匹配 (label / hint / keywords) */
export function filterCommands(commands: Command[], query: string): Command[] {
  const q = query.trim().toLowerCase();
  if (q === '') { return commands; }
  return commands.filter((c) => {
    if (c.label.toLowerCase().includes(q)) { return true; }
    if (c.hint?.toLowerCase().includes(q) === true) { return true; }
    if (c.keywords?.some((k) => k.toLowerCase().includes(q)) === true) { return true; }
    return false;
  });
}
