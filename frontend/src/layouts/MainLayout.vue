<template>
  <div class="w-full h-full flex flex-col bg-gradient-to-br from-background via-background to-accent/5 text-foreground">
    <!-- 顶部导航 - 增强的玻璃态效果 -->
    <header class="h-16 glass-effect border-b border-border/80 px-6 flex items-center justify-between z-10 shadow-glow-sm backdrop-blur-xl">
      <h1 class="text-3xl font-bold page-title drop-shadow-sm">
        AI智能网络故障分析平台
      </h1>

      <div class="flex items-center gap-4">
        <!-- 后端连接状态指示器 -->
        <ServerStatusIndicator />

        <!-- 主题切换开关 -->
        <button
          class="p-2 rounded-xl glass-effect text-foreground hover:text-primary transition-all duration-300 hover:scale-105 hover:shadow-glow-sm"
          @click="toggleTheme"
          :title="isDarkMode ? '切换到浅色模式' : '切换到深色模式'"
        >
          <component :is="isDarkMode ? SunIcon : MoonIcon" class="w-5 h-5" />
        </button>
      </div>
    </header>

    <!-- 主内容区域：左侧终端(2/3) + 右侧AI助手(1/3) -->
    <main class="flex flex-1 overflow-hidden min-h-0 responsive-layout">
      <section class="w-2/3 h-full overflow-hidden transition-all duration-300 p-3 terminal-section">
        <CardSpotlight
          :gradient-size="400"
          gradient-color="oklch(var(--primary) / 0.3)"
          :gradient-opacity="0.1"
          slot-class="h-full flex flex-col"
        >
          <NetworkTerminal />
        </CardSpotlight>
      </section>

      <section class="w-1/3 h-full overflow-hidden border-l border-border/60 rounded-r-xl pr-3 pt-3 pb-3 ai-section">
        <CardSpotlight
          :gradient-size="350"
          gradient-color="oklch(var(--accent) / 0.4)"
          :gradient-opacity="0.08"
          slot-class="h-full flex flex-col rounded-xl"
        >
          <FloatingParticlesBackground>
            <AIAssistant />
          </FloatingParticlesBackground>
        </CardSpotlight>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watchEffect } from 'vue';
import NetworkTerminal from '@/components/terminal/NetworkTerminal.vue';
import AIAssistant from '@/components/ai-assistant/AIAssistant.vue';
import ServerStatusIndicator from '@/components/common/ServerStatusIndicator.vue';
import CardSpotlight from '@/components/ui/CardSpotlight.vue';
import FloatingParticlesBackground from '@/components/ui/FloatingParticlesBackground.vue';
import { useAppStore } from '@/stores/app';
import { SunIcon, MoonIcon } from '@/components/common/icons';

const appStore = useAppStore();
const isDarkMode = ref(false);  // 明确设置为false，确保浅色主题

// 切换主题
const toggleTheme = () => {
  isDarkMode.value = !isDarkMode.value;
  appStore.setDarkMode(isDarkMode.value);
};


onMounted(() => {
  // 强制初始化为浅色模式
  isDarkMode.value = false;
  appStore.setDarkMode(false);
  document.documentElement.classList.remove('dark');

  // 清除可能的localStorage缓存
  localStorage.removeItem('theme');

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
