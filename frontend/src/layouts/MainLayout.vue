<template>
  <div class="flex-1 flex flex-col bg-background text-foreground">
    <!-- 顶部导航栏 - 玻璃态效果 -->
    <header class="h-16 glass-effect border-b border-border/40 px-6 flex items-center justify-between z-10 shadow-sm mx-4 mt-4 mb-4 rounded-md">
      <h1 class="text-xl font-semibold bg-gradient-to-r from-primary to-accent-cyan bg-clip-text text-transparent">
        AI智能网络故障分析平台
      </h1>
      
      <div class="flex items-center gap-4">
        <!-- 后端连接状态指示器 -->
        <ServerStatusIndicator />
        
        <!-- 主题切换开关 -->
        <button 
          class="p-2 rounded-full glass-effect text-foreground/70 hover:text-foreground transition-colors"
          @click="toggleTheme"
          :title="isDarkMode ? '切换到浅色模式' : '切换到深色模式'"
        >
          <component :is="isDarkMode ? SunIcon : MoonIcon" class="w-5 h-5" />
        </button>
      </div>
    </header>
    
    <!-- 主内容区域：左侧终端(2/3) + 右侧AI助手(1/3) -->
    <main class="flex flex-1 overflow-hidden mx-4 mb-4">
      <section class="w-2/3 h-full terminal-border rounded-xl mr-4 shadow-lg">
        <NetworkTerminal />
      </section>
      
      <section class="w-1/3 h-full ai-assistant-border glass-effect shadow-xl rounded-xl overflow-hidden">
        <AIAssistant />
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watchEffect } from 'vue';
import NetworkTerminal from '@/components/terminal/NetworkTerminal.vue';
import AIAssistant from '@/components/ai-assistant/AIAssistant.vue';
import ServerStatusIndicator from '@/components/common/ServerStatusIndicator.vue';
import { useAppStore } from '@/stores/app';
import { SunIcon, MoonIcon } from '@/components/common/icons';

const appStore = useAppStore();
const isDarkMode = ref(appStore.isDarkMode);

// 切换主题
const toggleTheme = () => {
  isDarkMode.value = !isDarkMode.value;
  appStore.setDarkMode(isDarkMode.value);
};

// 强制移除dark类，确保初始为浅色主题
document.documentElement.classList.remove('dark');

onMounted(() => {
  // 初始化主题设置为浅色模式
  appStore.setDarkMode(false);
  
  // 监听系统主题变化
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
  
  const handleChange = () => {
    if (localStorage.getItem('theme') === null) {
      // 即使系统是深色，也默认使用浅色
      isDarkMode.value = false;
      appStore.setDarkMode(false);
    }
  };
  
  // 初始设置
  handleChange();
  
  // 添加监听
  mediaQuery.addEventListener('change', handleChange);
  
  // 检查服务器连接状态
  appStore.checkServerConnection();
});

// 根据暗黑模式状态添加/移除 dark 类
watchEffect(() => {
  if (isDarkMode.value) {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
});
</script> 