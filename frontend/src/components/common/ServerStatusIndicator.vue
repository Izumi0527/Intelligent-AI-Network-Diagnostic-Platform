<template>
  <div class="flex items-center gap-2">
    <div 
      class="w-2 h-2 rounded-full transition-colors" 
      :class="appStore.isServerConnected ? 'bg-green-500' : 'bg-red-500'"
    ></div>
    <span class="text-sm">{{ statusText }}</span>
  </div>
</template>

<script setup lang="ts">
import { useAppStore } from '@/stores/app';
import { computed, onMounted, onUnmounted } from 'vue';

const appStore = useAppStore();

const statusText = computed(() => 
  appStore.isServerConnected ? '服务器已连接' : '服务器未连接'
);

// 定期检查服务器连接状态
let intervalId: NodeJS.Timeout;

onMounted(() => {
  // 立即检查一次
  appStore.checkServerConnection();
  
  // 每30秒检查一次
  intervalId = setInterval(() => {
    appStore.checkServerConnection();
  }, 30000);
});

onUnmounted(() => {
  clearInterval(intervalId);
});
</script> 