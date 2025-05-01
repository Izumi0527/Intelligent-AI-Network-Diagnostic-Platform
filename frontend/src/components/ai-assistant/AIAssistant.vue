<template>
  <div class="flex flex-col h-full w-full bg-gradient-to-b from-card/90 to-card/70 rounded-xl">
    <!-- AI助手头部 -->
    <div class="p-4 border-b border-border/30 bg-card/50 backdrop-blur-sm rounded-t-xl">
      <div class="flex items-center justify-between mb-3">
        <h2 class="text-lg font-medium flex items-center gap-2">
          <span class="bg-gradient-to-r from-accent-purple to-accent-cyan bg-clip-text text-transparent">
            AI智能助手
          </span>
          <span class="px-1.5 py-0.5 bg-primary/10 text-xs rounded-full text-primary">Beta</span>
        </h2>
        <div class="flex gap-2">
          <button 
            class="flex items-center gap-1 rounded-lg border border-border/40 px-2.5 py-1.5 text-xs font-medium transition-colors hover:bg-muted/50 btn-glow"
            @click="handleClearConversation"
            title="清空当前对话"
          >
            <ClearIcon class="w-3.5 h-3.5" />
            <span class="hidden sm:inline">清空对话</span>
          </button>
        </div>
      </div>
      
      <!-- AI模型选择 -->
      <div class="flex items-center gap-3 mb-3">
        <div class="flex-1">
          <select 
            v-model="selectedModel"
            class="w-full rounded-lg border border-border/40 bg-background/50 px-3 py-2 text-sm input-glow"
            @change="handleModelChange"
          >
            <option 
              v-for="model in store.availableModels" 
              :key="model.value" 
              :value="model.value"
            >
              {{ model.label }}
            </option>
          </select>
        </div>
        
        <div 
          class="px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1.5"
          :class="store.isModelConnected ? 'bg-success/10 text-success' : 'bg-destructive/10 text-destructive'"
        >
          <span 
            class="block w-1.5 h-1.5 rounded-full"
            :class="store.isModelConnected ? 'bg-success animate-pulse' : 'bg-destructive'"
          ></span>
          <span>{{ store.isModelConnected ? '已连接' : '未连接' }}</span>
        </div>
      </div>
      
      <!-- 流式响应开关 -->
      <div class="flex items-center justify-between">
        <span class="text-sm text-foreground/70">流式响应</span>
        <button 
          class="relative h-6 w-11 rounded-full transition-colors focus-visible:outline-none"
          :class="store.streamingEnabled ? 'bg-primary shadow-glow-sm' : 'bg-muted/70'"
          @click="toggleStreamingMode"
        >
          <span
            class="absolute left-0.5 top-0.5 flex h-5 w-5 items-center justify-center rounded-full bg-white shadow-sm transition-transform duration-200"
            :class="store.streamingEnabled ? 'translate-x-5' : 'translate-x-0'"
          >
            <span 
              class="h-2.5 w-2.5 rounded-full" 
              :class="store.streamingEnabled ? 'bg-primary' : 'bg-muted-foreground'"
            ></span>
          </span>
        </button>
      </div>
    </div>
    
    <!-- 聊天内容显示区域 -->
    <div 
      ref="chatContainerRef"
      class="flex-1 overflow-y-auto p-4 space-y-4 bg-gradient-to-b from-transparent to-card/30"
      style="min-height: 200px;"
    >
      <div v-if="store.chatMessages.length === 0" class="flex h-full items-center justify-center">
        <div class="text-center text-muted-foreground/60 max-w-sm p-8">
          <div class="text-4xl mb-4 opacity-30">💬</div>
          <p class="mb-2">与AI助手开始对话获取网络问题的帮助</p>
          <p class="text-xs">可以询问网络设备配置、故障排查方法或最佳实践</p>
        </div>
      </div>
      
      <template v-else>
        <div 
          v-for="(message, index) in store.chatMessages" 
          :key="index"
          :class="[
            message.role === 'user' ? 'message-user' : 'message-assistant',
            'group transition-all'
          ]"
        >
          <div class="font-medium text-xs mb-1.5 opacity-70 group-hover:opacity-100 flex items-center gap-2">
            <span class="inline-block w-5 h-5 rounded-full overflow-hidden flex items-center justify-center">
              <span v-if="message.role === 'user'" class="text-xs">👤</span>
              <span v-else class="text-xs">🤖</span>
            </span>
            <span>{{ message.role === 'user' ? '你' : getModelLabel }}</span>
            <span class="text-[10px] opacity-50">{{ formatTime() }}</span>
          </div>
          <div 
            class="whitespace-pre-wrap message-content" 
            v-if="message.role === 'user'"
          >{{ message.content }}</div>
          <div 
            class="message-content ai-message-content" 
            v-else
            v-html="formatAIMessage(message.content)"
          ></div>
        </div>
      </template>
      
      <!-- 正在输入指示器 - 仅在没有任何消息或最后一条不是assistant时显示 -->
      <div 
        v-if="store.isAIResponding && (store.chatMessages.length === 0 || store.chatMessages[store.chatMessages.length - 1].role !== 'assistant')" 
        class="message-assistant"
      >
        <div class="font-medium text-xs mb-1.5 opacity-70 flex items-center gap-2">
          <span class="inline-block w-5 h-5 rounded-full overflow-hidden flex items-center justify-center">
            <span class="text-xs">🤖</span>
          </span>
          <span>{{ getModelLabel }}</span>
          <span class="text-[10px] opacity-50">{{ formatTime() }}</span>
        </div>
        <div class="flex gap-1.5 px-2 py-1">
          <span class="thinking-dot animate-pulse"></span>
          <span class="thinking-dot animate-pulse animation-delay-200"></span>
          <span class="thinking-dot animate-pulse animation-delay-400"></span>
        </div>
      </div>
    </div>
    
    <!-- 消息输入区域 -->
    <div class="border-t border-border/30 p-4 bg-card/50 rounded-b-xl">
      <div class="flex flex-col gap-2">
        <textarea 
          v-model="userInput"
          placeholder="输入消息..." 
          rows="3"
          class="w-full resize-none rounded-lg border border-border/40 bg-background/50 px-3 py-2 text-sm input-glow"
          @keydown.enter.prevent="(event) => !event.ctrlKey && handleSendMessage()"
          @keydown.ctrl.enter="insertNewline"
        />
        <div class="flex justify-between items-center">
          <div class="text-xs text-muted-foreground">
            <kbd class="px-1.5 py-0.5 rounded bg-muted/40 text-foreground/70">Enter</kbd> 发送 | 
            <kbd class="px-1.5 py-0.5 rounded bg-muted/40 text-foreground/70">Ctrl</kbd> + 
            <kbd class="px-1.5 py-0.5 rounded bg-muted/40 text-foreground/70">Enter</kbd> 换行
          </div>
          <button 
            @click="handleSendMessage" 
            :disabled="!store.isModelConnected || store.isAIResponding || !userInput.trim()"
            class="flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium transition-all focus-visible:outline-none btn-glow disabled:opacity-50"
            :class="!userInput.trim() ? 'bg-muted text-muted-foreground' : 'bg-primary text-primary-foreground hover:bg-primary/90'"
          >
            <span>发送</span>
            <SendIcon class="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onMounted, computed } from 'vue';
import { useAIAssistantStore } from '@/stores/aiAssistant';
import { SendIcon, ClearIcon } from '@/components/common/icons';

const store = useAIAssistantStore();
const userInput = ref('');
const chatContainerRef = ref<HTMLElement | null>(null);
const selectedModel = ref(store.selectedModel);

// 获取当前选中模型的显示名称
const getModelLabel = computed(() => {
  const model = store.availableModels.find(m => m.value === store.selectedModel);
  return model ? model.label : 'AI助手';
});

// 格式化时间
const formatTime = () => {
  const now = new Date();
  return `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
};

// 发送消息
const handleSendMessage = async () => {
  if (!userInput.value.trim() || !store.isModelConnected || store.isAIResponding) return;
  
  const message = userInput.value;
  userInput.value = '';
  await store.sendMessage(message);
};

// 清空对话
const handleClearConversation = () => {
  if (store.chatMessages.length === 0) return;
  
  if (confirm('确定要清空当前对话吗？')) {
    store.clearConversation();
  }
};

// 切换流式响应
const toggleStreamingMode = () => {
  store.streamingEnabled = !store.streamingEnabled;
};

// 切换模型
const handleModelChange = () => {
  store.changeModel(selectedModel.value);
};

// 滚动到聊天底部
const scrollToBottom = () => {
  nextTick(() => {
    if (chatContainerRef.value) {
      chatContainerRef.value.scrollTop = chatContainerRef.value.scrollHeight;
    }
  });
};

// 插入换行符
const insertNewline = (event: KeyboardEvent) => {
  // 获取当前光标位置
  const target = event.target as HTMLTextAreaElement;
  const start = target.selectionStart;
  const end = target.selectionEnd;
  
  // 在光标位置插入换行符
  const newValue = userInput.value.substring(0, start) + '\n' + userInput.value.substring(end);
  userInput.value = newValue;
  
  // 重新设置光标位置
  nextTick(() => {
    target.selectionStart = target.selectionEnd = start + 1;
  });
};

onMounted(() => {
  // 初始化
  store.loadConversationFromStorage();
  store.checkModelConnection();
  scrollToBottom();
});

// 监视聊天消息变化，自动滚动到底部
watch(
  () => store.chatMessages.length,
  () => {
    scrollToBottom();
  }
);

// 当最后一条消息内容更新时也要滚动到底部（用于流式响应）
watch(
  () => store.chatMessages.length > 0 ? store.chatMessages[store.chatMessages.length - 1].content : '',
  () => {
    scrollToBottom();
  }
);

// 格式化AI消息
const formatAIMessage = (content: string): string => {
  if (!content) return '';
  
  // 转义HTML特殊字符但保留emoji
  let formatted = content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
  
  // 处理数字列表：
  // 1. 转换以"数字."开头的行为带有编号的列表项
  formatted = formatted.replace(/^(\d+)\.\s+(.+)$/gm, '<span class="number-list"><strong>$1.</strong> $2</span>');
  
  // 处理特殊标记和分隔符
  formatted = formatted.replace(/###/g, '<div class="section-divider"></div>');
  
  // 解析简单的Markdown样式标记
  formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
  formatted = formatted.replace(/\*\*([^\*]+)\*\*/g, '<strong>$1</strong>');
  formatted = formatted.replace(/\*([^\*]+)\*/g, '<em>$1</em>');
  
  // 检测并保留表情符号
  formatted = formatted.replace(/([\uD800-\uDBFF][\uDC00-\uDFFF])/g, '<span class="emoji">$1</span>');
  
  // 处理换行符，确保流式响应时的平滑显示
  formatted = formatted.replace(/\n/g, '<br>');
  
  return formatted;
};
</script>

<style scoped>
.message-content {
  line-height: 1.6;
  word-break: break-word;
  hyphens: auto;
}

.ai-message-content {
  /* 提高AI消息的可读性 */
  padding: 0.5rem;
  border-radius: 0.5rem;
  background-color: rgba(var(--card), 0.3);
  white-space: pre-wrap;
  transition: all 0.2s ease-in-out; /* 添加过渡效果使得动态添加内容平滑 */
  position: relative;
  overflow: hidden;
}

/* 添加文字渐入动画效果 */
@keyframes textFadeIn {
  from { opacity: 0; transform: translateY(2px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 为新添加的内容应用动画 */
.ai-message-content br:last-child,
.ai-message-content span:last-child,
.ai-message-content strong:last-child,
.ai-message-content code:last-child,
.ai-message-content em:last-child {
  animation: textFadeIn 0.3s ease-out;
  display: inline-block;
}

/* 确保代码块内的格式保持正确 */
.ai-message-content code {
  font-family: monospace;
  background-color: rgba(var(--muted), 0.3);
  padding: 0.1rem 0.3rem;
  border-radius: 0.25rem;
}

/* 段落间距 */
.ai-message-content p {
  margin-bottom: 0.75rem;
}

/* 列表样式 */
.ai-message-content ul,
.ai-message-content ol {
  padding-left: 1.5rem;
  margin-bottom: 0.75rem;
}

.ai-message-content ul {
  list-style-type: disc;
}

.ai-message-content ol {
  list-style-type: decimal;
}

/* 链接样式 */
.ai-message-content a {
  color: var(--primary);
  text-decoration: underline;
}

/* 数字列表解析 */
.ai-message-content .number-list {
  display: block;
  position: relative;
  padding-left: 1.5rem;
  margin-bottom: 0.5rem;
}

/* 转换普通文本中的数字列表为正确格式 */
.ai-message-content .number-list::before {
  content: "•";
  position: absolute;
  left: 0.5rem;
}

.thinking-dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  background-color: currentColor;
  opacity: 0.7;
}

.animation-delay-200 {
  animation-delay: 200ms;
}

.animation-delay-400 {
  animation-delay: 400ms;
}

/* 消息容器样式 */
.message-user {
  padding: 0.75rem;
  border-radius: 0.75rem;
  background-color: rgba(var(--primary), 0.05);
  margin-left: 1rem;
  margin-right: 0;
}

.message-assistant {
  padding: 0.75rem;
  border-radius: 0.75rem;
  background-color: rgba(var(--muted), 0.1);
  margin-right: 1rem;
  margin-left: 0;
}

/* 特殊元素样式 */
.section-divider {
  height: 1px;
  background-color: rgba(var(--border), 0.3);
  margin: 0.5rem 0;
}

.emoji {
  display: inline;
  font-size: 1.1em;
  vertical-align: middle;
}
</style> 