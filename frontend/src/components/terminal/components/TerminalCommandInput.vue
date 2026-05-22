<template>
  <div class="border-t border-border bg-terminal/90 backdrop-blur-md p-4">
    <div class="flex gap-2 items-center">
      <span class="terminal-prompt font-mono font-semibold">{{ devicePrompt }}</span>
      <label for="terminal-command" class="sr-only">终端命令</label>
      <input
        id="terminal-command"
        name="command"
        v-model="command"
        class="flex-1 rounded-lg border border-border bg-terminal/70 terminal-text px-3 py-2 text-sm font-mono input-glow focus:border-primary backdrop-blur-sm transition-all duration-200"
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
        class="terminal-send-button px-4 py-2 rounded-lg font-medium text-sm transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
        @click="handleExecute"
      >
        发送
      </button>
    </div>
    <div class="text-xs text-gray-400 mt-2 px-1 font-mono">
      <span
        >提示: 使用
        <kbd class="px-2 py-0.5 rounded bg-gray-700 text-gray-300 border border-gray-600 font-mono text-xs">↑</kbd>
        <kbd class="px-2 py-0.5 rounded bg-gray-700 text-gray-300 border border-gray-600 font-mono text-xs">↓</kbd>
        浏览历史命令</span
      >
    </div>
  </div>
</template>

<script setup lang="ts">
import { useTerminalStore } from '@/stores/terminal'
import { useCommandHistory } from '../composables/useCommandHistory'

defineProps<{
  devicePrompt: string
}>()

const store = useTerminalStore()
const { command, showPrevious, showNext, reset } = useCommandHistory()

const handleExecute = async (): Promise<void> => {
  const value = command.value.trim()
  if (!value || store.connectionStatus !== 'connected') return
  await store.executeCommand(value)
  reset()
}
</script>
