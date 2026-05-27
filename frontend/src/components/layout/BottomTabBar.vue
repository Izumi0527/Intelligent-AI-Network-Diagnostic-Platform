<template>
  <nav class="bottom-tab-bar" aria-label="移动端导航">
    <button
      v-for="tab in tabs"
      :key="tab.key"
      type="button"
      class="bottom-tab-bar__tab"
      :class="{ 'bottom-tab-bar__tab--active': ui.mobileActiveTab === tab.key }"
      :aria-current="ui.mobileActiveTab === tab.key ? 'page' : undefined"
      @click="ui.setMobileTab(tab.key)"
    >
      <span class="bottom-tab-bar__icon" v-html="tab.icon" />
      <span class="bottom-tab-bar__label">{{ tab.label }}</span>
    </button>
  </nav>
</template>

<script setup lang="ts">
import { useUiStore, type MobileTab } from '@/stores/ui';

const ui = useUiStore();

interface Tab {
  key: MobileTab;
  label: string;
  /** Inline SVG path (16x16) */
  icon: string;
}

const tabs: Tab[] = [
  {
    key: 'terminal',
    label: '终端',
    icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>'
  },
  {
    key: 'ai',
    label: 'AI 助手',
    icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>'
  },
  {
    key: 'settings',
    label: '设置',
    icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>'
  }
];
</script>

<style scoped>
.bottom-tab-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  display: none;
  height: 56px;
  padding-bottom: env(safe-area-inset-bottom, 0);
  background-color: var(--background);
  border-top: 1px solid var(--border);
  z-index: var(--z-popover);
}

@media (max-width: 768px) {
  .bottom-tab-bar {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
  }
}

.bottom-tab-bar__tab {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  background: transparent;
  border: none;
  color: var(--muted-foreground);
  font-size: 11px;
  cursor: pointer;
  transition: color var(--dur-enter) var(--ease-standard);
}

.bottom-tab-bar__tab:hover {
  color: var(--foreground);
}

.bottom-tab-bar__tab--active {
  color: var(--primary);
}

.bottom-tab-bar__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.bottom-tab-bar__label {
  font-weight: 500;
  letter-spacing: 0.02em;
}
</style>
