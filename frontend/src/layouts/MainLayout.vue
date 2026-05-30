<template>
  <div class="netops-shell">
    <!-- 网络拓扑底纹（z-0 绝对定位铺底） -->
    <network-topology-background />

    <!-- 顶部状态栏 -->
    <header class="netops-header">
      <div class="netops-header__brand">
        <span class="netops-header__logo" v-html="logoSvg" />
        <span class="netops-header__title">NetOps</span>
        <span class="netops-header__divider" />
        <span class="netops-header__subtitle">AI 网络故障智能分析平台</span>
      </div>

      <div class="netops-header__actions">
        <div class="netops-header__clock" role="timer" aria-label="当前时间">{{ clock }}</div>
        <server-status-indicator />

        <button
          type="button"
          class="netops-header__cmdk"
          aria-label="打开命令面板"
          @click="ui.openCommandPalette"
        >
          <span class="netops-header__cmdk-icon" v-html="searchIconSvg" />
          <span class="netops-header__cmdk-text">搜索命令…</span>
          <kbd class="netops-header__cmdk-kbd">⌘K</kbd>
        </button>

        <button
          type="button"
          class="netops-header__icon-btn"
          :title="isDarkMode ? '切换到浅色模式' : '切换到深色模式'"
          :aria-label="isDarkMode ? '切换到浅色模式' : '切换到深色模式'"
          @click="toggleTheme"
        >
          <component :is="isDarkMode ? SunIcon : MoonIcon" class="w-4 h-4" />
        </button>
      </div>
    </header>

    <!-- 主内容区：桌面端双面板 + 拖拽分割条 -->
    <main ref="containerEl" class="netops-main">
      <!-- 终端面板 -->
      <section
        v-if="!isMobile || ui.mobileActiveTab === 'terminal'"
        class="netops-pane netops-pane--terminal"
        :style="paneStyle('terminal')"
        :data-collapsed="ui.isAiPaneCollapsed ? 'true' : 'false'"
      >
        <hud-frame :bordered="false" label="TERMINAL" class="netops-pane__frame">
          <network-terminal />
        </hud-frame>
      </section>

      <!-- 拖拽分割条（仅桌面） -->
      <drag-handle
        v-if="!isMobile && !ui.isAiPaneCollapsed"
        :container-ref="containerEl"
      />

      <!-- AI 助手面板 -->
      <section
        v-if="(!isMobile && !ui.isAiPaneCollapsed) || (isMobile && ui.mobileActiveTab === 'ai')"
        class="netops-pane netops-pane--ai"
        :style="paneStyle('ai')"
      >
        <hud-frame :bordered="false" label="AI ASSISTANT" class="netops-pane__frame">
          <a-i-assistant ref="aiAssistantRef" @request-clear="handleClearChat" />
        </hud-frame>
      </section>

      <!-- 移动端设置抽屉 -->
      <section
        v-if="isMobile && ui.mobileActiveTab === 'settings'"
        class="netops-pane netops-pane--settings"
      >
        <div class="mobile-settings">
          <h2 class="mobile-settings__title">设置</h2>
          <div class="mobile-settings__row">
            <span>深色模式</span>
            <button class="btn-outline mobile-settings__btn" @click="toggleTheme">
              {{ isDarkMode ? '关闭' : '开启' }}
            </button>
          </div>
          <div class="mobile-settings__row">
            <span>命令面板</span>
            <button class="btn-outline mobile-settings__btn" @click="ui.openCommandPalette">
              打开
            </button>
          </div>
          <div class="mobile-settings__row">
            <span>重连后端</span>
            <button class="btn-outline mobile-settings__btn" @click="appStore.checkServerConnection">
              检查
            </button>
          </div>
          <p class="mobile-settings__hint">
            桌面端支持 ⌘K 命令面板、⌘\ 折叠 AI 助手、拖拽中线调整布局比例
          </p>
        </div>
      </section>
    </main>

    <!-- 移动端底部 Tab -->
    <bottom-tab-bar />

    <!-- 命令面板 -->
    <command-palette
      :on-clear-chat="handleClearChat"
      :on-focus-input="handleFocusInput"
    />

    <!-- 统一清空对话确认弹窗（按钮点击 + ⌘⇧K 共用） -->
    <confirm-dialog
      :open="confirmClearOpen"
      title="清空当前对话"
      message="将清除当前模型下的全部聊天记录与缓存，且无法恢复。确定继续吗？"
      confirm-text="清空"
      cancel-text="取消"
      @confirm="onClearConfirm"
      @cancel="onClearCancel"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, type CSSProperties } from 'vue';
import NetworkTerminal from '@/components/terminal/NetworkTerminal.vue';
import AIAssistant from '@/components/ai-assistant/AIAssistant.vue';
import ServerStatusIndicator from '@/components/common/ServerStatusIndicator.vue';
import NetworkTopologyBackground from '@/components/decoration/NetworkTopologyBackground.vue';
import HudFrame from '@/components/decoration/HudFrame.vue';
import DragHandle from '@/components/layout/DragHandle.vue';
import BottomTabBar from '@/components/layout/BottomTabBar.vue';
import CommandPalette from '@/components/command-palette/CommandPalette.vue';
import ConfirmDialog from '@/components/ai-assistant/components/ConfirmDialog.vue';
import { SunIcon, MoonIcon } from '@/components/common/icons';
import { useAppStore } from '@/stores/app';
import { useUiStore } from '@/stores/ui';
import { useAiAssistantStore } from '@/stores/ai-assistant';
import { useKeyboardShortcuts } from '@/composables/useKeyboardShortcuts';

const appStore = useAppStore();
const ui = useUiStore();
const aiStore = useAiAssistantStore();

const containerEl = ref<HTMLElement | null>(null);
const aiAssistantRef = ref<InstanceType<typeof AIAssistant> | null>(null);

const isDarkMode = computed(() => appStore.isDarkMode);

const isMobile = ref(window.innerWidth < 768);

const onResize = (): void => {
  isMobile.value = window.innerWidth < 768;
};

/* 任务时钟：mono 实时时钟，运维场景定位事件发生时间 */
const clock = ref('');
let clockTimer: ReturnType<typeof setInterval> | null = null;
const updateClock = (): void => {
  const d = new Date();
  const p = (n: number): string => String(n).padStart(2, '0');
  clock.value = `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
};

const logoSvg = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><rect x="2" y="2" width="20" height="20" rx="6" fill="currentColor" fill-opacity="0.05" stroke="currentColor" stroke-width="1"/><line x1="7" y1="7" x2="12" y2="12" stroke="currentColor" stroke-width="0.8" stroke-opacity="0.55"/><line x1="17" y1="7" x2="12" y2="12" stroke="currentColor" stroke-width="0.8" stroke-opacity="0.55"/><line x1="7" y1="17" x2="12" y2="12" stroke="currentColor" stroke-width="0.8" stroke-opacity="0.55"/><line x1="17" y1="17" x2="12" y2="12" stroke="currentColor" stroke-width="0.8" stroke-opacity="0.55"/><circle cx="7" cy="7" r="1.5" fill="currentColor"/><circle cx="17" cy="7" r="1.5" fill="currentColor"/><circle cx="7" cy="17" r="1.5" fill="currentColor"/><circle cx="17" cy="17" r="1.5" fill="currentColor"/><circle cx="12" cy="12" r="2.6" fill="none" stroke="currentColor" stroke-width="1"/><circle cx="12" cy="12" r="1.1" fill="currentColor"/></svg>';

const searchIconSvg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>';

const toggleTheme = (): void => {
  appStore.setDarkMode(!appStore.isDarkMode);
};

const paneStyle = (which: 'terminal' | 'ai'): CSSProperties => {
  if (isMobile.value) {
    return { flex: '1 1 auto', width: '100%' };
  }
  const flex = which === 'terminal' ? ui.terminalFlex : ui.aiFlex;
  return { flexBasis: `${flex}%`, flexGrow: 0, flexShrink: 0 };
};

const confirmClearOpen = ref(false);

const handleClearChat = (): void => {
  confirmClearOpen.value = true;
};

const onClearConfirm = (): void => {
  confirmClearOpen.value = false;
  void aiStore.clearConversation();
};

const onClearCancel = (): void => {
  confirmClearOpen.value = false;
};

const handleFocusInput = (): void => {
  // 通过自定义事件解耦：ChatInput 监听 'ai-focus-input' 并 focus()
  window.dispatchEvent(new CustomEvent('ai-focus-input'));
};

useKeyboardShortcuts({
  onClearChat: handleClearChat,
  onFocusInput: handleFocusInput
});

/* 主题持久化：根据 store 状态同步 documentElement 类 */
watch(
  () => appStore.isDarkMode,
  (dark) => {
    if (dark) {
      document.documentElement.classList.add('dark');
      document.documentElement.classList.remove('light');
    } else {
      document.documentElement.classList.add('light');
      document.documentElement.classList.remove('dark');
    }
  },
  { immediate: true }
);

onMounted(() => {
  window.addEventListener('resize', onResize);
  updateClock();
  clockTimer = setInterval(updateClock, 1000);
});

onUnmounted(() => {
  window.removeEventListener('resize', onResize);
  if (clockTimer !== null) { clearInterval(clockTimer); clockTimer = null; }
});
</script>

<style scoped>
.netops-shell {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: var(--background);
  color: var(--foreground);
  overflow: hidden;
}

/* 顶部状态栏 (h-12 紧凑) */
.netops-header {
  position: relative;
  z-index: 10;
  height: 48px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  background-color: var(--background);
  border-bottom: 1px solid var(--border);
}

.netops-header__brand {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--foreground);
}

.netops-header__logo {
  color: var(--primary);
  display: inline-flex;
  align-items: center;
}

.netops-header__title {
  font-weight: 600;
  letter-spacing: 0.12em;
  font-size: 13px;
  font-family: var(--app-font-mono);
  text-transform: uppercase;
}

.netops-header__divider {
  width: 1px;
  height: 16px;
  background-color: var(--border);
  margin: 0 4px;
}

.netops-header__subtitle {
  font-size: 12px;
  color: var(--muted-foreground);
  letter-spacing: 0.01em;
}

@media (max-width: 640px) {
  .netops-header__divider,
  .netops-header__subtitle {
    display: none;
  }
}

.netops-header__actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.netops-header__clock {
  font-family: var(--app-font-mono);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.06em;
  color: var(--muted-foreground);
  height: 28px;
  padding: 0 9px;
  display: inline-flex;
  align-items: center;
  border: 1px solid var(--border);
  border-radius: var(--radius);
}

@media (max-width: 640px) {
  .netops-header__clock { display: none; }
}

.netops-header__cmdk {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 32px;
  padding: 0 10px;
  background-color: var(--muted);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--muted-foreground);
  font-size: 12px;
  cursor: pointer;
  transition:
    background-color var(--dur-enter) var(--ease-standard),
    color var(--dur-enter) var(--ease-standard),
    border-color var(--dur-enter) var(--ease-standard);
}

.netops-header__cmdk:hover {
  color: var(--foreground);
  border-color: color-mix(in oklch, var(--foreground) 16%, transparent);
}

.netops-header__cmdk-text {
  min-width: 100px;
  text-align: left;
}

@media (max-width: 640px) {
  .netops-header__cmdk-text {
    display: none;
  }
  .netops-header__cmdk {
    min-width: 36px;
    padding: 0 8px;
  }
}

.netops-header__cmdk-kbd {
  font-family: var(--app-font-mono);
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 3px;
  background-color: var(--background);
  border: 1px solid var(--border);
  color: var(--muted-foreground);
}

.netops-header__icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background-color: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius);
  color: var(--muted-foreground);
  cursor: pointer;
  transition:
    background-color var(--dur-enter) var(--ease-standard),
    color var(--dur-enter) var(--ease-standard),
    border-color var(--dur-enter) var(--ease-standard);
}

.netops-header__icon-btn:hover {
  background-color: var(--muted);
  color: var(--foreground);
  border-color: var(--border);
}

/* 主内容区 */
.netops-main {
  position: relative;
  z-index: 1;
  flex: 1;
  min-height: 0;
  display: flex;
  overflow: hidden;
}

.netops-pane {
  position: relative;
  display: flex;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

/* HudFrame 焦点框叠加层：撑满面板，让终端 / AI 内容仍铺满 */
.netops-pane__frame {
  flex: 1 1 auto;
  min-width: 0;
  width: 100%;
}

.netops-pane--terminal {
  padding: 12px;
  padding-right: 6px;
}

.netops-pane--ai {
  padding: 12px;
  padding-left: 6px;
}

.netops-pane--terminal[data-collapsed='true'] {
  padding: 12px;
}

@media (max-width: 768px) {
  .netops-main {
    padding-bottom: 56px; /* 留出 BottomTabBar 高度 */
  }
  .netops-pane {
    padding: 12px !important;
    flex-basis: auto !important;
    width: 100%;
  }
}

/* 移动端设置面板 */
.netops-pane--settings {
  padding: 16px;
  flex-direction: column;
}

.mobile-settings {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
}

.mobile-settings__title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 8px;
  color: var(--foreground);
}

.mobile-settings__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  background-color: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 13px;
  color: var(--foreground);
}

.mobile-settings__btn {
  height: 28px;
  padding: 0 12px;
  font-size: 12px;
}

.mobile-settings__hint {
  font-size: 11px;
  color: var(--muted-foreground);
  margin-top: 8px;
  line-height: 1.5;
  font-family: var(--app-font-mono);
}
</style>
