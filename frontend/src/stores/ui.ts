/**
 * UI 全局交互状态：命令面板开关、AI 面板折叠、移动端 tab、面板分割比例。
 * 持久化使用 localStorage（与 app store 现有 'theme' 键并行）。
 */
import { defineStore } from 'pinia';
import { ref, computed, watch } from 'vue';

const SPLIT_RATIO_KEY = 'ui.split-ratio';
const AI_COLLAPSED_KEY = 'ui.ai-collapsed';
const MOBILE_TAB_KEY = 'ui.mobile-active-tab';

const SPLIT_MIN = 25;
const SPLIT_MAX = 75;
const SPLIT_DEFAULT = 66;

export type MobileTab = 'terminal' | 'ai' | 'settings';

const readNumber = (key: string, fallback: number): number => {
  const raw = localStorage.getItem(key);
  if (raw === null) { return fallback; }
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : fallback;
};

const readBool = (key: string, fallback: boolean): boolean => {
  const raw = localStorage.getItem(key);
  if (raw === null) { return fallback; }
  return raw === 'true';
};

const readMobileTab = (fallback: MobileTab): MobileTab => {
  const raw = localStorage.getItem(MOBILE_TAB_KEY);
  if (raw === 'terminal' || raw === 'ai' || raw === 'settings') { return raw; }
  return fallback;
};

export const useUiStore = defineStore('ui', () => {
  const isCommandPaletteOpen = ref(false);
  const isAiPaneCollapsed = ref(readBool(AI_COLLAPSED_KEY, false));
  const mobileActiveTab = ref<MobileTab>(readMobileTab('ai'));
  const splitRatio = ref(clamp(readNumber(SPLIT_RATIO_KEY, SPLIT_DEFAULT)));

  /** 终端面板占比 (%)。AI 折叠时返回 100。*/
  const terminalFlex = computed(() =>
    isAiPaneCollapsed.value ? 100 : splitRatio.value
  );

  /** AI 面板占比 (%)。折叠时返回 0。*/
  const aiFlex = computed(() =>
    isAiPaneCollapsed.value ? 0 : 100 - splitRatio.value
  );

  function clamp(v: number): number {
    return Math.min(SPLIT_MAX, Math.max(SPLIT_MIN, v));
  }

  const setSplitRatio = (v: number): void => {
    splitRatio.value = clamp(v);
  };

  const toggleAiPane = (): void => {
    isAiPaneCollapsed.value = !isAiPaneCollapsed.value;
  };

  const setAiPaneCollapsed = (v: boolean): void => {
    isAiPaneCollapsed.value = v;
  };

  const openCommandPalette = (): void => {
    isCommandPaletteOpen.value = true;
  };

  const closeCommandPalette = (): void => {
    isCommandPaletteOpen.value = false;
  };

  const toggleCommandPalette = (): void => {
    isCommandPaletteOpen.value = !isCommandPaletteOpen.value;
  };

  const setMobileTab = (tab: MobileTab): void => {
    mobileActiveTab.value = tab;
  };

  /* 持久化 watchers (写入 localStorage) */
  watch(splitRatio, (v) => { localStorage.setItem(SPLIT_RATIO_KEY, String(v)); });
  watch(isAiPaneCollapsed, (v) => { localStorage.setItem(AI_COLLAPSED_KEY, String(v)); });
  watch(mobileActiveTab, (v) => { localStorage.setItem(MOBILE_TAB_KEY, v); });

  return {
    isCommandPaletteOpen,
    isAiPaneCollapsed,
    mobileActiveTab,
    splitRatio,
    terminalFlex,
    aiFlex,
    setSplitRatio,
    toggleAiPane,
    setAiPaneCollapsed,
    openCommandPalette,
    closeCommandPalette,
    toggleCommandPalette,
    setMobileTab
  };
});
