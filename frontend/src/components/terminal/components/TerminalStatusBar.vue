<template>
  <div
    role="status"
    aria-live="polite"
    class="mt-3 text-sm flex items-center"
    :class="{
      'text-terminal-success': store.connectionStatus === 'connected',
      'text-terminal-error': store.connectionStatus === 'error',
      'text-gray-400':
        store.connectionStatus === 'disconnected' || store.connectionStatus === 'connecting'
    }"
  >
    <span
      class="inline-block w-2 h-2 rounded-full mr-2"
      :class="{
        'bg-green-500 pulse-animation': store.connectionStatus === 'connected',
        'bg-red-500': store.connectionStatus === 'error',
        'bg-gray-400': store.connectionStatus === 'disconnected',
        'bg-blue-500 pulse-animation': store.connectionStatus === 'connecting'
      }"
    ></span>
    {{ diagnosticMessage }}
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
      return '连接失败: 请检查设备信息和网络状态';
    default:
      return '请输入设备信息进行连接';
  }
});
</script>
