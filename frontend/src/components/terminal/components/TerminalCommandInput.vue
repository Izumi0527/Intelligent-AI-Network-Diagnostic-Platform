<template>
  <div class="terminal-cmd">
    <div class="terminal-cmd__row">
      <span class="terminal-cmd__prompt">{{ devicePrompt }}</span>
      <label for="terminal-command" class="sr-only">终端命令</label>
      <input
        id="terminal-command"
        v-model="command"
        name="command"
        class="terminal-cmd__input"
        placeholder="输入命令..."
        type="text"
        autocomplete="off"
        :disabled="store.connectionStatus !== 'connected'"
        @keydown.enter="handleExecute"
        @keyup.up="showPrevious"
        @keyup.down="showNext"
      />
      <button
        :disabled="store.connectionStatus !== 'connected'"
        class="terminal-send-button"
        @click="handleExecute"
      >
        发送
      </button>
    </div>
    <div class="terminal-cmd__hint">
      <span>使用</span>
      <kbd>↑</kbd>
      <kbd>↓</kbd>
      <span>浏览历史命令</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useTerminalStore } from '@/stores/terminal';
import { useCommandHistory } from '../composables/useCommandHistory';

defineProps<{
  devicePrompt: string
}>();

const store = useTerminalStore();
const { command, showPrevious, showNext, reset } = useCommandHistory();

const handleExecute = async (): Promise<void> => {
  const value = command.value.trim();
  if (!value || store.connectionStatus !== 'connected') { return; }
  await store.executeCommand(value);
  reset();
};
</script>

<style scoped>
.terminal-cmd {
  padding: 12px 16px;
  border-top: 1px solid var(--terminal-border);
  background-color: color-mix(in oklch, var(--terminal-bg), white 2%);
}

.terminal-cmd__row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.terminal-cmd__prompt {
  font-family: var(--app-font-mono);
  font-weight: 600;
  color: var(--terminal-prompt);
  font-size: 13px;
}

.terminal-cmd__input {
  flex: 1;
  height: 30px;
  padding: 0 10px;
  font-size: 13px;
  font-family: var(--app-font-mono);
  background-color: color-mix(in oklch, var(--terminal-bg), black 8%);
  color: var(--terminal-fg);
  border: 1px solid var(--terminal-border);
  border-radius: var(--radius);
  transition: border-color var(--dur-enter) var(--ease-standard);
}

.terminal-cmd__input:focus,
.terminal-cmd__input:focus-visible {
  outline: none;
  border-color: color-mix(in oklch, var(--primary) 55%, transparent);
  box-shadow: 0 0 0 2px color-mix(in oklch, var(--primary) 20%, transparent);
}

.terminal-cmd__input:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.terminal-cmd__hint {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 6px;
  font-size: 10.5px;
  color: color-mix(in oklch, var(--terminal-fg) 55%, transparent);
  font-family: var(--app-font-mono);
}

.terminal-cmd__hint kbd {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 3px;
  background-color: color-mix(in oklch, var(--terminal-bg), white 8%);
  border: 1px solid var(--terminal-border);
  color: var(--terminal-fg);
  font-size: 10px;
}
</style>
