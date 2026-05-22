<template>
  <div class="flex items-center gap-2" role="status" aria-live="polite">
    <div
      class="w-2 h-2 rounded-full transition-[background-color] duration-[var(--dur-base)] ease-[var(--ease-out)]"
      :class="appStore.isServerConnected ? 'bg-green-500' : 'bg-red-500'"
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