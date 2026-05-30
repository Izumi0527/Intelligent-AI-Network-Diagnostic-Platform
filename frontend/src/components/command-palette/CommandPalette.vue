<template>
  <Teleport to="body">
    <Transition name="cmdk">
      <div
        v-if="ui.isCommandPaletteOpen"
        class="cmdk-backdrop"
        role="dialog"
        aria-modal="true"
        aria-label="命令面板"
        @click.self="ui.closeCommandPalette"
      >
        <div ref="paletteEl" class="cmdk-palette">
          <div class="cmdk-search">
            <span class="cmdk-search__icon" v-html="searchIcon" />
            <input
              ref="inputEl"
              v-model="query"
              type="text"
              placeholder="搜索命令… (↑↓ 选择, ↵ 执行, Esc 关闭)"
              class="cmdk-search__input"
              autocomplete="off"
              spellcheck="false"
              @keydown="onKeyDown"
            />
            <kbd class="cmdk-search__kbd">⌘K</kbd>
          </div>

          <div v-if="filtered.length === 0" class="cmdk-empty">
            <span>没有匹配的命令</span>
            <span class="cmdk-empty__hint">尝试搜索 "清空" 或 "主题"</span>
          </div>

          <ul v-else class="cmdk-list" role="listbox">
            <template v-for="(group, gi) in groupedCommands" :key="group.name">
              <li v-if="gi > 0 || group.name !== ''" class="cmdk-group-label" role="presentation">
                {{ group.name }}
              </li>
              <li
                v-for="cmd in group.items"
                :key="cmd.id"
                class="cmdk-item"
                :class="{ 'cmdk-item--active': cmd.id === activeId }"
                role="option"
                :aria-selected="cmd.id === activeId"
                @mouseenter="setActive(cmd.id)"
                @click="execute(cmd)"
              >
                <span v-if="cmd.icon" class="cmdk-item__icon" v-html="cmd.icon" />
                <span class="cmdk-item__body">
                  <span class="cmdk-item__label">{{ cmd.label }}</span>
                  <span v-if="cmd.hint" class="cmdk-item__hint">{{ cmd.hint }}</span>
                </span>
                <kbd v-if="cmd.shortcut" class="cmdk-item__kbd">{{ cmd.shortcut }}</kbd>
              </li>
            </template>
          </ul>

          <div class="cmdk-footer">
            <span class="cmdk-footer__hint">
              <span class="cmdk-footer__hint-item"><kbd>↑</kbd><kbd>↓</kbd> 导航</span>
              <span class="cmdk-footer__hint-item"><kbd>↵</kbd> 执行</span>
              <span class="cmdk-footer__hint-item"><kbd>Esc</kbd> 关闭</span>
            </span>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue';
import { useUiStore } from '@/stores/ui';
import { useAppStore } from '@/stores/app';
import { useAiAssistantStore } from '@/stores/ai-assistant';
import { useTerminalStore } from '@/stores/terminal';
import { createCommands, filterCommands, type Command } from './commands';

const props = defineProps<{
  /** 由 MainLayout 传入：清空对话的实际实现 */
  onClearChat:() => void;
  /** 由 MainLayout 传入：聚焦输入框的实际实现 */
  onFocusInput: () => void;
}>();

const ui = useUiStore();
const app = useAppStore();
const ai = useAiAssistantStore();
const terminal = useTerminalStore();

const query = ref('');
const inputEl = ref<HTMLInputElement | null>(null);
const paletteEl = ref<HTMLDivElement | null>(null);
const activeId = ref<string | null>(null);

const searchIcon = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>';

/** 重新构造命令列表（command 标签依赖响应式 store 状态, 每次重算）*/
const commands = computed<Command[]>(() =>
  createCommands(
    { ui, app, ai, terminal },
    {
      onClearChat: () => { props.onClearChat(); },
      onFocusInput: () => { props.onFocusInput(); }
    }
  )
);

const filtered = computed<Command[]>(() => filterCommands(commands.value, query.value));

/** 按 group 分组（保持原顺序）*/
const groupedCommands = computed(() => {
  const map = new Map<string, Command[]>();
  for (const cmd of filtered.value) {
    const arr = map.get(cmd.group) ?? [];
    arr.push(cmd);
    map.set(cmd.group, arr);
  }
  return Array.from(map.entries()).map(([name, items]) => ({ name, items }));
});

const flatFiltered = computed<Command[]>(() =>
  groupedCommands.value.flatMap((g) => g.items)
);

const setActive = (id: string): void => { activeId.value = id; };

const moveActive = (delta: 1 | -1): void => {
  const list = flatFiltered.value;
  if (list.length === 0) { return; }
  const currentIdx = list.findIndex((c) => c.id === activeId.value);
  let nextIdx = currentIdx + delta;
  if (nextIdx < 0) { nextIdx = list.length - 1; }
  if (nextIdx >= list.length) { nextIdx = 0; }
  const item = list[nextIdx];
  if (item !== undefined) { activeId.value = item.id; }
};

const execute = async (cmd: Command): Promise<void> => {
  ui.closeCommandPalette();
  // 关闭动画后再执行：避免命令触发 alert 等阻塞导致面板卡住
  await nextTick();
  await cmd.action();
};

const onKeyDown = (event: KeyboardEvent): void => {
  if (event.key === 'ArrowDown') {
    event.preventDefault();
    moveActive(1);
  } else if (event.key === 'ArrowUp') {
    event.preventDefault();
    moveActive(-1);
  } else if (event.key === 'Enter') {
    event.preventDefault();
    const current = flatFiltered.value.find((c) => c.id === activeId.value);
    if (current !== undefined) { void execute(current); }
  } else if (event.key === 'Escape') {
    event.preventDefault();
    ui.closeCommandPalette();
  }
};

/** 打开时：聚焦输入框 + 默认选中第一项；关闭时重置 */
watch(
  () => ui.isCommandPaletteOpen,
  (open) => {
    if (open) {
      query.value = '';
      const first = flatFiltered.value[0];
      activeId.value = first !== undefined ? first.id : null;
      void nextTick(() => inputEl.value?.focus());
    } else {
      activeId.value = null;
    }
  }
);

/** 搜索变化时：保持 activeId 落在过滤结果中 */
watch(filtered, (list) => {
  if (list.length === 0) {
    activeId.value = null;
    return;
  }
  if (!list.some((c) => c.id === activeId.value)) {
    const first = list[0];
    activeId.value = first !== undefined ? first.id : null;
  }
});
</script>

<style scoped>
.cmdk-backdrop {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 18vh;
  background-color: oklch(0 0 0 / 0.35);
  backdrop-filter: blur(4px);
  z-index: var(--z-cmdk);
}

.dark .cmdk-backdrop {
  background-color: oklch(0 0 0 / 0.55);
}

.cmdk-palette {
  width: min(640px, calc(100vw - 32px));
  max-height: 70vh;
  display: flex;
  flex-direction: column;
  background-color: var(--popover);
  border: 1px solid var(--border);
  border-radius: calc(var(--radius) + 2px);
  box-shadow: var(--shadow-popover);
  overflow: hidden;
  color: var(--popover-foreground);
}

.cmdk-search {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--border);
}

/* L 角标 bracket：标记"当前输入活动区"，聚焦时点亮 */
.cmdk-search::before,
.cmdk-search::after {
  content: '';
  position: absolute;
  width: 9px;
  height: 9px;
  pointer-events: none;
  border: 1px solid var(--hud-bracket);
  transition: border-color var(--dur-enter) var(--ease-hud);
}

.cmdk-search::before {
  top: 6px;
  left: 6px;
  border-right: none;
  border-bottom: none;
}

.cmdk-search::after {
  right: 6px;
  bottom: 6px;
  border-left: none;
  border-top: none;
}

.cmdk-search:focus-within::before,
.cmdk-search:focus-within::after {
  border-color: var(--hud-bracket-active);
}

.cmdk-search__icon {
  color: var(--muted-foreground);
  display: inline-flex;
}

.cmdk-search__input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: var(--foreground);
  font-family: var(--app-font-sans);
  font-size: 14px;
}

.cmdk-search__input::placeholder {
  color: var(--muted-foreground);
}

.cmdk-search__kbd,
.cmdk-item__kbd,
.cmdk-footer kbd {
  font-family: var(--app-font-mono);
  font-size: 10px;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  background-color: var(--muted);
  color: var(--muted-foreground);
  border: 1px solid var(--border);
}

.cmdk-list {
  list-style: none;
  margin: 0;
  padding: 4px;
  overflow-y: auto;
  flex: 1;
}

.cmdk-group-label {
  padding: 8px 10px 4px;
  font-size: 10px;
  font-weight: 500;
  font-family: var(--app-font-mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted-foreground);
}

.cmdk-group-label:not(:first-child) {
  margin-top: 4px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

.cmdk-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 10px;
  border-radius: var(--radius);
  cursor: pointer;
  transition: background-color var(--dur-enter) var(--ease-standard);
}

.cmdk-item--active {
  background-color: var(--muted);
  box-shadow: inset 2px 0 0 var(--primary);
}

.cmdk-item__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  color: var(--muted-foreground);
}

.cmdk-item--active .cmdk-item__icon {
  color: var(--primary);
}

.cmdk-item__body {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.cmdk-item__label {
  font-size: 13px;
  color: var(--foreground);
}

.cmdk-item__hint {
  font-size: 11px;
  color: var(--muted-foreground);
  margin-top: 1px;
}

.cmdk-empty {
  padding: 32px 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: center;
  color: var(--muted-foreground);
  font-size: 13px;
}

.cmdk-empty__hint {
  font-size: 11px;
  opacity: 0.7;
}

.cmdk-footer {
  border-top: 1px solid var(--border);
  padding: 8px 14px;
  font-size: 11px;
  color: var(--muted-foreground);
}

.cmdk-footer__hint {
  display: inline-flex;
  align-items: center;
  gap: 12px;
}

.cmdk-footer__hint-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

/* Transition: 极简 fade + scale */
.cmdk-enter-active,
.cmdk-leave-active {
  transition:
    opacity var(--dur-enter) var(--ease-standard),
    backdrop-filter var(--dur-enter) var(--ease-standard);
}

.cmdk-enter-active .cmdk-palette,
.cmdk-leave-active .cmdk-palette {
  transition:
    transform var(--dur-base) var(--ease-standard),
    opacity var(--dur-base) var(--ease-standard);
}

.cmdk-enter-from,
.cmdk-leave-to {
  opacity: 0;
}

.cmdk-enter-from .cmdk-palette,
.cmdk-leave-to .cmdk-palette {
  opacity: 0;
  transform: translateY(-8px) scale(0.98);
}
</style>
