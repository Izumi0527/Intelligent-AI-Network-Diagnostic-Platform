<template>
  <div class="network-terminal">
    <div class="network-terminal__config">
      <terminal-connection-form />
      <terminal-status-bar />
    </div>

    <terminal-output :device-prompt="devicePrompt" />

    <terminal-command-input :device-prompt="devicePrompt" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useTerminalStore } from '@/stores/terminal';
import {
  TerminalConnectionForm,
  TerminalStatusBar,
  TerminalOutput,
  TerminalCommandInput
} from './components';

const store = useTerminalStore();

const promptUsername = computed<string>(() => store.username.trim() || 'admin');

const devicePrompt = computed<string>(() => {
  if (!store.deviceAddress) { return '$ '; }
  const prefix = store.connectionType === 'ssh' ? 'ssh' : 'telnet';
  return `${promptUsername.value}@${store.deviceAddress}:~${prefix}# `;
});
</script>

<style scoped>
.network-terminal {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  min-height: 0;
  background-color: var(--terminal-bg);
  color: var(--terminal-fg);
  border: 1px solid var(--terminal-border);
  border-radius: calc(var(--radius) + 4px);
  overflow: hidden;
}

.network-terminal__config {
  padding: 14px 16px;
  border-bottom: 1px solid var(--terminal-border);
  background-color: color-mix(in oklch, var(--terminal-bg), white 2%);
}
</style>
