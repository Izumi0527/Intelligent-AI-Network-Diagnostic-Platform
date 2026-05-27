<template>
  <div
    role="status"
    aria-live="polite"
    class="terminal-status"
    :data-state="store.connectionStatus"
  >
    <span class="terminal-status__dot" aria-hidden="true" />
    <span class="terminal-status__text">{{ diagnosticMessage }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useTerminalStore } from '@/stores/terminal';

const store = useTerminalStore();

const diagnosticMessage = computed<string>(() => {
  switch (store.connectionStatus) {
    case 'connected':
      return `已成功连接到 ${store.deviceAddress}`;
    case 'connecting':
      return `正在连接到 ${store.deviceAddress}...`;
    case 'error':
      return '连接失败：请检查设备信息和网络状态';
    default:
      return '请输入设备信息进行连接';
  }
});
</script>

<style scoped>
.terminal-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  font-size: 12px;
  font-family: var(--app-font-mono);
}

.terminal-status[data-state='connected'] { color: var(--terminal-success); }
.terminal-status[data-state='connecting'] { color: var(--primary); }
.terminal-status[data-state='error'] { color: var(--terminal-error); }
.terminal-status[data-state='disconnected'] {
  color: color-mix(in oklch, var(--terminal-fg) 55%, transparent);
}

.terminal-status__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: currentColor;
  flex-shrink: 0;
}

.terminal-status[data-state='connected'] .terminal-status__dot,
.terminal-status[data-state='connecting'] .terminal-status__dot {
  box-shadow: 0 0 0 3px color-mix(in oklch, currentColor 22%, transparent);
}

.terminal-status[data-state='connecting'] .terminal-status__dot {
  animation: pulseDot 1.4s var(--ease-standard) infinite;
}

@keyframes pulseDot {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}

@media (prefers-reduced-motion: reduce) {
  .terminal-status__dot { animation: none !important; }
}
</style>
