import { defineStore } from 'pinia';
import { ref } from 'vue';
import { logger } from '@/utils/logger';

export const useAppStore = defineStore('app', () => {
  // 服务器连接状态
  const isServerConnected = ref(false);

  // 主题模式（暗色/亮色）
  const isDarkMode = ref(
    localStorage.getItem('theme') === 'dark' ||
        (localStorage.getItem('theme') === null &&
            false) // 默认使用亮色主题，忽略系统偏好
  );

  // 检查服务器连接状态
  const checkServerConnection = async (): Promise<boolean> => {
    try {
      const response = await fetch('/api/health');
      isServerConnected.value = response.ok;
      return response.ok;
    } catch (error) {
      logger.error('服务器连接检查失败:', error);
      isServerConnected.value = false;
      return false;
    }
  };

  // 设置暗黑模式
  const setDarkMode = (value: boolean): void => {
    isDarkMode.value = value;
    localStorage.setItem('theme', value ? 'dark' : 'light');

    if (value) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  };

  return {
    isServerConnected,
    isDarkMode,
    checkServerConnection,
    setDarkMode
  };
});