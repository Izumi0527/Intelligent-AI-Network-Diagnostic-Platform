<template>
  <div
    class="flex flex-col h-full w-full min-h-0 bg-terminal text-terminal-foreground overflow-hidden shadow-glow-lg border-tech rounded-xl"
  >
    <div class="p-4 border-b border-border/80 terminal-config-panel">
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
