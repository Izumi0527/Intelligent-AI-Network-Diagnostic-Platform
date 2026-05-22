<template>
  <div
    class="flex flex-col h-full w-full min-h-0 bg-terminal text-terminal-foreground overflow-hidden shadow-glow-lg border-tech rounded-xl"
  >
    <div class="p-4 border-b border-border/80 terminal-config-panel">
      <TerminalConnectionForm />
      <TerminalStatusBar />
    </div>

    <TerminalOutput :device-prompt="devicePrompt" />

    <TerminalCommandInput :device-prompt="devicePrompt" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useTerminalStore } from '@/stores/terminal'
import {
  TerminalConnectionForm,
  TerminalStatusBar,
  TerminalOutput,
  TerminalCommandInput
} from './components'

const store = useTerminalStore()

const devicePrompt = computed<string>(() => {
  if (!store.deviceAddress) return '$ '
  const prefix = store.connectionType === 'ssh' ? 'ssh' : 'telnet'
  return `admin@${store.deviceAddress}:~${prefix}# `
})
</script>
