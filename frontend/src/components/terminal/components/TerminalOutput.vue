<template>
  <div
    ref="outputRef"
    role="log"
    aria-live="polite"
    class="flex-1 min-h-[60vh] overflow-auto p-4 font-mono text-sm whitespace-pre-wrap terminal-display text-left"
  >
    <div
      v-for="(line, index) in store.terminalOutput"
      :key="index"
      class="mb-1 text-left"
      :class="getLineClass(line)"
    >
      <span v-if="line.startsWith('>')" class="terminal-prompt mr-1 font-semibold">{{ devicePrompt }}</span>
      <span class="terminal-text">{{ line.startsWith('>') ? line.substring(1) : line }}</span>
    </div>
    <div v-if="store.connectionStatus === 'connected'" class="flex">
      <span class="terminal-prompt mr-1 font-semibold">{{ devicePrompt }}</span>
      <span class="terminal-cursor terminal-text">_</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { useTerminalStore } from '@/stores/terminal';
import { useTerminalLineStyle } from '../composables/useTerminalLineStyle';

defineProps<{
  devicePrompt: string
}>();

const store = useTerminalStore();
const { getLineClass } = useTerminalLineStyle();

const outputRef = ref<HTMLElement | null>(null);

watch(
  () => store.terminalOutput.length,
  () => {
    if (outputRef.value) {
      outputRef.value.scrollTop = outputRef.value.scrollHeight;
    }
  }
);
</script>

<style scoped>
.terminal-cursor {
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  from,
  to {
    opacity: 1;
  }
  50% {
    opacity: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .terminal-cursor {
    animation: none;
  }
}
</style>
