<template>
  <div class="flex flex-col h-full w-full min-h-0 bg-terminal text-terminal-foreground overflow-hidden shadow-glow-lg border-tech rounded-xl">
    <!-- 连接控制面板 - 按设计需求：深灰色背景卡片，6个控件水平排列 -->
    <div class="p-4 border-b border-border/80 terminal-config-panel">
      <form @submit.prevent="handleConnect" class="grid grid-cols-6 gap-4">
        <!-- 1. 连接方式下拉框 -->
        <div>
          <label class="text-sm font-medium mb-1 block text-gray-400">连接方式</label>
          <select
            v-model="store.connectionType"
            class="w-full rounded-lg border terminal-config-input px-3 py-2 text-sm transition-all duration-200 hover:border-primary/50"
          >
            <option value="telnet">Telnet</option>
            <option value="ssh">SSH</option>
          </select>
        </div>

        <!-- 2. 设备地址输入框 -->
        <div>
          <label class="text-sm font-medium mb-1 block text-gray-400">设备地址</label>
          <input
            v-model="store.deviceAddress"
            class="w-full rounded-lg border terminal-config-input px-3 py-2 text-sm transition-all duration-200 hover:border-primary/50 focus:border-primary"
            placeholder="192.168.20.1"
          />
        </div>

        <!-- 3. 端口输入框 -->
        <div>
          <label class="text-sm font-medium mb-1 block text-gray-400">端口</label>
          <input
            v-model="store.port"
            class="w-20 rounded-lg border terminal-config-input px-3 py-2 text-sm transition-all duration-200 hover:border-primary/50 focus:border-primary"
            :placeholder="store.connectionType === 'ssh' ? '22' : '23'"
          />
        </div>

        <!-- 4. 用户名输入框 -->
        <div>
          <label class="text-sm font-medium mb-1 block text-gray-400">用户名</label>
          <input
            v-model="store.username"
            class="w-full rounded-lg border terminal-config-input px-3 py-2 text-sm transition-all duration-200 hover:border-primary/50 focus:border-primary"
            placeholder="admin"
          />
        </div>

        <!-- 5. 密码输入框 -->
        <div>
          <label class="text-sm font-medium mb-1 block text-gray-400">密码</label>
          <input
            v-model="store.password"
            class="w-full rounded-lg border terminal-config-input px-3 py-2 text-sm transition-all duration-200 hover:border-primary/50 focus:border-primary"
            type="password"
            placeholder="••••••••"
          />
        </div>

        <!-- 6. 执行按钮 -->
        <div class="flex items-end">
          <div class="w-full flex gap-2">
            <button
              type="submit"
              :class="[
                'flex-1 h-10 terminal-config-button rounded-lg font-medium text-sm',
                store.connectionStatus === 'connected'
                  ? 'bg-red-600 hover:bg-red-700'
                  : 'terminal-config-button'
              ]"
              :disabled="store.connectionStatus === 'connecting' && !store.canCancelConnection"
            >
              <div class="flex items-center justify-center">
                <span v-if="store.connectionStatus === 'connecting' && !store.canCancelConnection" class="pulse-animation">
                  连接中...
                </span>
                <span v-else>
                  {{ store.connectionStatus === 'connected' ? '断开连接' : '执行连接' }}
                </span>
              </div>
            </button>

            <!-- 取消按钮 -->
            <button
              v-if="store.canCancelConnection && store.connectionStatus === 'connecting'"
              type="button"
              class="h-10 px-4 bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg font-medium text-sm transition-all duration-200"
              @click="handleCancelConnect"
            >
              取消连接
            </button>
          </div>
        </div>
      </form>

      <!-- 连接诊断信息 -->
      <div
        class="mt-3 text-sm flex items-center"
        :class="{
          'text-terminal-success': store.connectionStatus === 'connected',
          'text-terminal-error': store.connectionStatus === 'error',
          'text-gray-400': store.connectionStatus === 'disconnected' || store.connectionStatus === 'connecting'
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
        {{ connectionDiagnosticMessage }}
      </div>
    </div>
    
    <!-- 虚拟终端显示区域 - 纯黑背景 -->
    <div
      ref="terminalOutputRef"
      class="flex-1 min-h-[60vh] overflow-auto p-4 font-mono text-sm whitespace-pre-wrap terminal-display text-left"
    >
      <div v-for="(line, index) in formattedOutput" :key="index" class="mb-1 text-left" :class="getLineClass(line)">
        <span v-if="line.startsWith('>')" class="terminal-prompt mr-1 font-semibold">{{ devicePrompt }}</span>
        <span class="terminal-text">{{ line.startsWith('>') ? line.substring(1) : line }}</span>
      </div>
      <div v-if="store.connectionStatus === 'connected'" class="flex">
        <span class="terminal-prompt mr-1 font-semibold">{{ devicePrompt }}</span>
        <span class="terminal-cursor terminal-text">_</span>
      </div>
    </div>

    <!-- 命令输入区域 -->
    <div class="border-t border-border bg-terminal/90 backdrop-blur-md p-4">
      <div class="flex gap-2 items-center">
        <span class="terminal-prompt font-mono font-semibold">{{ devicePrompt }}</span>
        <input
          v-model="command"
          class="flex-1 rounded-lg border border-border bg-terminal/70 terminal-text px-3 py-2 text-sm font-mono input-glow focus:border-primary backdrop-blur-sm transition-all duration-200"
          placeholder="输入命令..."
          @keydown.enter="handleExecuteCommand"
          @keyup.up="handlePreviousCommand"
          @keyup.down="handleNextCommand"
          :disabled="store.connectionStatus !== 'connected'"
        />
        <button
          :disabled="store.connectionStatus !== 'connected'"
          class="terminal-send-button px-4 py-2 rounded-lg font-medium text-sm transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          @click="handleExecuteCommand"
        >
          发送
        </button>
      </div>
      <div class="text-xs text-gray-400 mt-2 px-1 font-mono">
        <span>提示: 使用 <kbd class="px-2 py-0.5 rounded bg-gray-700 text-gray-300 border border-gray-600 font-mono text-xs">↑</kbd> <kbd class="px-2 py-0.5 rounded bg-gray-700 text-gray-300 border border-gray-600 font-mono text-xs">↓</kbd> 浏览历史命令</span>
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
  return `admin@${store.deviceAddress}:~${prefix}# `;
});

// 格式化终端输出，添加样式
const formattedOutput = computed(() => {
  return store.terminalOutput;
});

// 获取行样式
const getLineClass = (line: string) => {
  if (line.includes('错误') || line.includes('失败')) {
    return 'terminal-error';
  } else if (line.includes('成功') || line.includes('已连接')) {
    return 'terminal-success';
  } else if (line.startsWith('>')) {
    return 'terminal-command';
  } else if (line.includes('警告')) {
    return 'terminal-warning';
  }
  return 'terminal-text';
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
  command.value = nextCommand || ''; // 确保不是undefined
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

// 处理取消连接
const handleCancelConnect = async () => {
  await store.cancelConnection();
};
</script>

<style scoped>
.terminal-output {
  min-height: 60vh;
  text-align: left;
}

.terminal-output > div {
  text-align: left;
  margin-right: auto;
  display: block;
  width: 100%;
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

/* 强制白色空间保留和左对齐 */
.terminal-output span {
  white-space: pre-wrap;
  text-align: left;
  word-break: break-all;
  display: inline;
}

/* 发送按钮采用高对比配色，确保浅色模式下文字清晰 */
.terminal-send-button {
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  color: #ffffff;
  border: 1px solid rgba(37, 99, 235, 0.65);
  box-shadow: 0 14px 28px -18px rgba(37, 99, 235, 0.6);
}

.terminal-send-button:hover:not(:disabled) {
  background: linear-gradient(135deg, #1d4ed8, #1e40af);
  box-shadow: 0 16px 32px -16px rgba(37, 99, 235, 0.55);
}

.terminal-send-button:active:not(:disabled) {
  transform: translateY(1px);
  box-shadow: 0 10px 22px -18px rgba(37, 99, 235, 0.65);
}

.terminal-send-button:disabled {
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.2), rgba(29, 78, 216, 0.25));
  color: rgba(241, 245, 249, 0.6);
  border-color: rgba(148, 163, 184, 0.35);
}

:deep(.dark) .terminal-send-button {
  background: linear-gradient(135deg, #3b82f6, #1e3a8a);
  color: #f8fafc;
  border-color: rgba(96, 165, 250, 0.85);
}

:deep(.dark) .terminal-send-button:hover:not(:disabled) {
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  box-shadow: 0 18px 34px -18px rgba(59, 130, 246, 0.55);
}
</style> 