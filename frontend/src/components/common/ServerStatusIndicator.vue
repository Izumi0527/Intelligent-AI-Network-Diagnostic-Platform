<template>
  <div class="flex items-center gap-2" role="status" aria-live="polite">
    <div
      class="server-dot"
      :class="appStore.isServerConnected ? 'server-dot--ok' : 'server-dot--down'"
      aria-hidden="true"
    ></div>
    <span class="text-sm">{{ statusText }}</span>
  </div>
</template>

<script setup lang="ts">
import { useAppStore } from '@/stores/app';
import { useIntervalFn } from '@vueuse/core';
import { computed } from 'vue';

const appStore = useAppStore();

const statusText = computed(() =>
  appStore.isServerConnected ? '服务器已连接' : '服务器未连接'
);

useIntervalFn(() => {
  appStore.checkServerConnection();
}, 30000, { immediateCallback: true });
</script>

<style scoped>
.server-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  transition: background-color var(--dur-base) var(--ease-standard);
}

.server-dot--ok {
  background-color: var(--hud-ok);
  animation: server-pulse 2.4s var(--ease-standard) infinite;
}

.server-dot--down {
  background-color: var(--hud-alert);
}

/* 在线呼吸：绿色 glow 脉冲，表达"系统在线" */
@keyframes server-pulse {
  0%, 100% { box-shadow: 0 0 0 0 color-mix(in oklch, var(--hud-ok) 40%, transparent); }
  50% { box-shadow: 0 0 6px 1px color-mix(in oklch, var(--hud-ok) 40%, transparent); }
}

@media (prefers-reduced-motion: reduce) {
  .server-dot--ok { animation: none; }
}
</style>