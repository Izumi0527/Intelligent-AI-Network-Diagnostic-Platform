<template>
  <div class="flex flex-col h-full w-full bg-terminal text-terminal-foreground rounded-xl overflow-hidden shadow-inner">
    <!-- 连接控制面板 -->
    <div class="p-4 border-b border-border/20 glass-effect backdrop-blur-md">
      <form @submit.prevent="handleConnect" class="grid grid-cols-3 gap-4">
        <div>
          <label class="text-sm font-medium mb-1 block opacity-80">连接方式</label>
          <select 
            v-model="store.connectionType"
            class="w-full rounded-md border border-border/30 bg-terminal/50 text-terminal-foreground px-3 py-2 text-sm input-glow"
          >
            <option value="ssh">SSH</option>
            <option value="telnet">Telnet</option>
          </select>
        </div>
        
        <div>
          <label class="text-sm font-medium mb-1 block opacity-80">设备地址</label>
          <input 
            v-model="store.deviceAddress"
            class="w-full rounded-md border border-border/30 bg-terminal/50 text-terminal-foreground px-3 py-2 text-sm input-glow focus:border-primary"
            placeholder="192.168.1.1" 
          />
        </div>
        
        <div>
          <label class="text-sm font-medium mb-1 block opacity-80">端口</label>
          <input 
            v-model="store.port"
            class="w-full rounded-md border border-border/30 bg-terminal/50 text-terminal-foreground px-3 py-2 text-sm input-glow focus:border-primary"
            :placeholder="store.connectionType === 'ssh' ? '22' : '23'"
          />
        </div>
        
        <div>
          <label class="text-sm font-medium mb-1 block opacity-80">用户名</label>
          <input 
            v-model="store.username"
            class="w-full rounded-md border border-border/30 bg-terminal/50 text-terminal-foreground px-3 py-2 text-sm input-glow focus:border-primary"
            placeholder="admin"
          />
        </div>
        
        <div>
          <label class="text-sm font-medium mb-1 block opacity-80">密码</label>
          <input 
            v-model="store.password"
            class="w-full rounded-md border border-border/30 bg-terminal/50 text-terminal-foreground px-3 py-2 text-sm input-glow focus:border-primary"
            type="password"
            placeholder="********"
          />
        </div>
        
        <div class="flex items-end">
          <button 
            type="submit"
            class="w-full h-10 rounded-md px-4 py-2 text-sm font-medium transition-all duration-300 focus-visible:outline-none btn-glow"
            :class="[
              store.connectionStatus === 'connected' 
                ? 'bg-destructive text-destructive-foreground hover:bg-destructive/90' 
                : 'bg-primary text-primary-foreground hover:bg-primary/90'
            ]"
          >
            <div class="flex items-center justify-center">
              <span v-if="store.connectionStatus === 'connecting'" class="animate-pulse">
                连接中...
              </span>
              <span v-else>
                {{ store.connectionStatus === 'connected' ? '断开连接' : '连接' }}
              </span>
            </div>
          </button>
        </div>
      </form>
      
      <!-- 连接诊断信息 -->
      <div 
        class="mt-3 text-sm flex items-center" 
        :class="{
          'text-terminal-success': store.connectionStatus === 'connected',
          'text-terminal-error': store.connectionStatus === 'error',
          'text-terminal-foreground/60': store.connectionStatus === 'disconnected' || store.connectionStatus === 'connecting'
        }"
      >
        <span 
          class="inline-block w-2 h-2 rounded-full mr-2"
          :class="{
            'bg-terminal-success animate-pulse': store.connectionStatus === 'connected',
            'bg-terminal-error': store.connectionStatus === 'error',
            'bg-terminal-foreground/60': store.connectionStatus === 'disconnected',
            'bg-primary animate-pulse': store.connectionStatus === 'connecting'
          }"
        ></span>
        {{ connectionDiagnosticMessage }}
      </div>
    </div>
    
    <!-- 虚拟终端显示区域 -->
    <div 
      ref="terminalOutputRef"
      class="flex-1 overflow-auto p-4 font-mono text-sm whitespace-pre-wrap terminal-output"
    >
      <div v-for="(line, index) in formattedOutput" :key="index" class="mb-1" :class="getLineClass(line)">
        <span v-if="line.startsWith('>')" class="text-terminal-prompt mr-1">{{ devicePrompt }}</span>
        <span>{{ line.startsWith('>') ? line.substring(1) : line }}</span>
      </div>
      <div v-if="store.connectionStatus === 'connected'" class="flex">
        <span class="text-terminal-prompt mr-1">{{ devicePrompt }}</span>
        <span class="terminal-cursor">_</span>
      </div>
    </div>
    
    <!-- 命令输入区域 -->
    <div class="border-t border-border/20 bg-terminal/90 p-4">
      <div class="flex gap-2 items-center">
        <span class="text-terminal-prompt font-mono">{{ devicePrompt }}</span>
        <input 
          v-model="command"
          class="flex-1 rounded-lg border border-border/30 bg-terminal/50 text-terminal-foreground px-3 py-2 text-sm font-mono input-glow focus:border-primary"
          placeholder="输入命令..." 
          @keydown.enter="handleExecuteCommand"
          @keyup.up="handlePreviousCommand"
          @keyup.down="handleNextCommand"
          :disabled="store.connectionStatus !== 'connected'"
        />
        <button 
          @click="handleExecuteCommand"
          :disabled="store.connectionStatus !== 'connected'"
          class="rounded-lg px-4 py-2 text-sm font-medium bg-primary text-primary-foreground transition-all focus-visible:outline-none btn-glow disabled:opacity-50 hover:bg-primary/90"
        >
          发送
        </button>
      </div>
      <div class="text-xs text-terminal-foreground/50 mt-1 px-1">
        <span>提示: 使用 <kbd class="px-1 py-0.5 rounded bg-terminal/70 text-terminal-foreground/80">↑</kbd> <kbd class="px-1 py-0.5 rounded bg-terminal/70 text-terminal-foreground/80">↓</kbd> 浏览历史命令</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { useTerminalStore } from '@/stores/terminal';

const store = useTerminalStore();
const command = ref('');
const terminalOutputRef = ref<HTMLElement | null>(null);

// 设备提示符
const devicePrompt = computed(() => {
  if (!store.deviceAddress) return '$ ';
  const prefix = store.connectionType === 'ssh' ? 'ssh' : 'telnet';
  return `${store.username}@${store.deviceAddress}:~${prefix}# `;
});

// 格式化终端输出，添加样式
const formattedOutput = computed(() => {
  return store.terminalOutput;
});

// 获取行样式
const getLineClass = (line: string) => {
  if (line.includes('错误') || line.includes('失败')) {
    return 'text-terminal-error';
  } else if (line.includes('成功') || line.includes('已连接')) {
    return 'text-terminal-success';
  } else if (line.startsWith('>')) {
    return 'text-terminal-command';
  }
  return '';
};

// 诊断信息
const connectionDiagnosticMessage = computed(() => {
  if (store.connectionStatus === 'connected') {
    return `已成功连接到 ${store.deviceAddress}`;
  } else if (store.connectionStatus === 'connecting') {
    return `正在连接到 ${store.deviceAddress}...`;
  } else if (store.connectionStatus === 'error') {
    return `连接失败: 请检查设备信息和网络状态`;
  }
  return '请输入设备信息进行连接';
});

// 处理连接
const handleConnect = async () => {
  await store.connectToDevice();
};

// 处理命令执行
const handleExecuteCommand = async () => {
  if (!command.value.trim() || store.connectionStatus !== 'connected') return;
  
  await store.executeCommand(command.value);
  command.value = '';
};

// 浏览命令历史
const handlePreviousCommand = () => {
  const prevCommand = store.getPreviousCommand();
  if (prevCommand) {
    command.value = prevCommand;
  }
};

const handleNextCommand = () => {
  const nextCommand = store.getNextCommand();
  command.value = nextCommand; // 可能是空字符串，这是预期行为
};

// 滚动到终端底部
const scrollToBottom = () => {
  if (terminalOutputRef.value) {
    terminalOutputRef.value.scrollTop = terminalOutputRef.value.scrollHeight;
  }
};

// 监视终端输出的变化，自动滚动到底部
watch(
  () => store.terminalOutput.length,
  () => {
    scrollToBottom();
  }
);
</script>

<style scoped>
.terminal-output {
  min-height: 200px;
}

.terminal-cursor {
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  from, to { opacity: 1; }
  50% { opacity: 0; }
}

/* 添加内部阴影效果 */
.shadow-inner {
  box-shadow: inset 0 2px 6px rgba(0, 0, 0, 0.2);
}
</style> 