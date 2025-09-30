<template>
  <div class="flex flex-col h-full w-full ai-assistant-panel">
    <!-- 顶部信息栏 -->
    <div class="flex items-center justify-between mb-4">
      <div class="flex items-center gap-2">
        <h2 class="ai-title text-lg font-medium">AI智能助手</h2>
      </div>
      <button
        class="ai-clear-button inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 shadow-glow-sm"
        type="button"
        title="清空当前对话"
        @click="handleClearConversation"
      >
        <span class="ai-clear-button__icon flex h-6 w-6 items-center justify-center rounded-full transition-colors">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </span>
        <span class="hidden sm:inline">清空对话</span>
      </button>
    </div>

    <!-- 模型选择与连接状态 -->
    <div class="mb-4">
      <div class="flex flex-col lg:flex-row lg:items-start lg:gap-6 space-y-3 lg:space-y-0">
        <div class="flex-1 space-y-2">
          <label class="text-sm font-medium text-foreground/80">模型选择</label>
          <select
            class="w-full ai-input text-sm focus:outline-none transition-all duration-200"
            :value="selectedModel"
            @change="handleModelChange"
          >
            <option
              v-for="model in store.availableModels"
              :key="String(model.value ?? model)"
              :value="String(model.value ?? model)"
            >
              {{ typeof model === 'string' ? model : model.label ?? model.value }}
            </option>
          </select>
        </div>

        <div class="flex flex-col items-end gap-2 lg:pt-1">
          <div
            class="flex items-center gap-2 text-xs font-medium"
            :class="store.isModelConnected ? 'text-emerald-500 dark:text-emerald-400' : 'text-red-500 dark:text-red-400'"
          >
            <span
              class="h-2 w-2 rounded-full"
              :class="store.isModelConnected
                ? 'bg-emerald-500 dark:bg-emerald-400 animate-pulse shadow-[0_0_0_4px_rgba(16,185,129,0.15)]'
                : 'bg-red-500 dark:bg-red-400 shadow-[0_0_0_4px_rgba(239,68,68,0.1)]'"
            />
            <span>{{ store.isModelConnected ? '已连接' : '未连接' }}</span>
          </div>

          <div class="flex items-center gap-3">
            <label class="text-sm font-medium text-foreground/80 whitespace-nowrap">流式响应</label>
            <button
              class="relative inline-flex h-8 w-14 items-center rounded-full transition-all duration-300 ease-in-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/30"
              :style="{ backgroundColor: store.streamingEnabled ? '#007AFF' : '#E5E5E7' }"
              type="button"
              @click="toggleStreamingMode"
            >
              <span
                class="h-6 w-6 rounded-full bg-white transition-transform duration-300 ease-in-out shadow-md"
                :class="store.streamingEnabled ? 'translate-x-7' : 'translate-x-1'"
              />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 聊天消息区域 -->
    <ChatMessages
      ref="chatMessagesRef"
      :messages="messagesForDisplay"
      :is-typing="store.isAIResponding"
      :is-streaming-content="store.isStreamingContent"
      :is-thinking="store.isThinking"
      :current-thinking-content="store.currentThinkingContent"
      :streaming-enabled="store.streamingEnabled"
      class="ai-chat-gradient"
    />

    <!-- 消息输入区域 -->
    <div class="border-t border-border/60 pt-4 mt-5">
      <div class="space-y-2">
        <div class="flex items-end gap-3">
          <textarea
            v-model="messageInput"
            class="ai-input flex-1 min-h-[32px] max-h-[120px] overflow-y-auto resize-none focus:outline-none"
            placeholder="输入消息..."
            :disabled="store.isLoading || store.isAIResponding"
            @keydown.enter.exact.prevent="() => handleSendMessage()"
            @keydown.ctrl.enter="insertNewline"
            @input="adjustTextareaHeight"
          ></textarea>
          <button
            class="flex-shrink-0 inline-flex h-12 w-12 items-center justify-center rounded-xl text-blue-600 dark:text-blue-200 hover:text-blue-700 dark:hover:text-blue-100 disabled:opacity-40 disabled:cursor-not-allowed transition-transform duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500/70 bg-blue-50 dark:bg-blue-500/20 shadow-glow-sm p-0"
            type="button"
            :disabled="store.isLoading || store.isAIResponding || !messageInput.trim()"
            @click="() => handleSendMessage()"
          >
            <svg class="w-full h-full" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.9">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
        <div class="flex items-center justify-between text-xs text-gray-500">
          <span>Enter 发送 | Ctrl + Enter 换行</span>
          <span class="hidden sm:inline text-gray-400">Ctrl/Cmd + K 清空对话</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import ChatMessages from './components/ChatMessages.vue'
import { useAiAssistantStore } from '@/stores/aiAssistant'

const store = useAiAssistantStore()
const chatMessagesRef = ref<InstanceType<typeof ChatMessages> | null>(null)
const messageInput = ref('')

const selectedModel = computed(() => store.selectedModel)
const messagesForDisplay = computed(() => {
  return store.chatMessages
    .filter((msg) => msg.role === 'user' || msg.role === 'assistant')
    .map((msg) => {
      const base = {
        role: msg.role as 'user' | 'assistant',
        content: msg.content
      }
      return typeof msg.timestamp === 'number'
        ? { ...base, timestamp: msg.timestamp }
        : base
    })
})

const handleClearConversation = async () => {
  try {
    await store.clearConversation()
  } catch (error) {
    console.error('清空对话失败:', error)
  }
}

const handleModelChange = async (event: Event) => {
  const target = event.target as HTMLSelectElement | null
  if (!target) return
  const value = target.value
  try {
    store.setSelectedModel(value)
    store.loadConversationFromStorage()
    await store.checkModelConnection()
  } catch (error) {
    console.error('模型切换失败:', error)
  }
}

const toggleStreamingMode = () => {
  store.toggleStreamingMode()
}

const handleSendMessage = async (message?: string) => {
  const content = message ?? messageInput.value.trim()
  if (!content || store.isLoading || store.isAIResponding) return

  try {
    messageInput.value = ''
    await store.sendMessage(content)
    chatMessagesRef.value?.scrollToBottom()
  } catch (error) {
    console.error('发送消息失败:', error)
  }
}

const insertNewline = () => {
  const textarea = document.activeElement as HTMLTextAreaElement | null
  if (!textarea) return
  const start = textarea.selectionStart
  const end = textarea.selectionEnd
  const value = textarea.value
  messageInput.value = `${value.substring(0, start)}\n${value.substring(end)}`
  requestAnimationFrame(() => {
    textarea.selectionStart = textarea.selectionEnd = start + 1
  })
}

const adjustTextareaHeight = (event: Event) => {
  const textarea = event.target as HTMLTextAreaElement
  textarea.style.height = 'auto'
  const newHeight = Math.min(textarea.scrollHeight, 120)
  textarea.style.height = newHeight + 'px'
}

onMounted(async () => {
  try {
    store.isLoading = true
    await store.loadAvailableModels()
    if (store.selectedModel) {
      await store.checkModelConnection()
    }
  } catch (error) {
    console.error('AI助手初始化失败:', error)
  } finally {
    store.isLoading = false
  }

  // 初始化textarea高度
  requestAnimationFrame(() => {
    const textarea = document.querySelector('textarea.ai-input') as HTMLTextAreaElement
    if (textarea) {
      textarea.style.height = '32px'
    }
  })
})

watch(
  () => store.selectedModel,
  async (newModel, oldModel) => {
    if (newModel === oldModel) return
    try {
      store.loadConversationFromStorage()
      await store.checkModelConnection()
    } catch (error) {
      console.error('检查模型连接失败:', error)
    }
  }
)

const handleKeyboardShortcuts = (event: KeyboardEvent) => {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    handleClearConversation()
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeyboardShortcuts)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyboardShortcuts)
})
</script>

<style scoped>
.btn-glow {
  box-shadow: 0 0 20px -5px oklch(var(--primary) / 0.3);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.btn-glow:hover {
  box-shadow: 0 0 25px -5px oklch(var(--primary) / 0.5);
  transform: translateY(-1px);
}

.input-glow:focus {
  box-shadow: 0 0 15px -3px oklch(var(--primary) / 0.3);
}

.shadow-glow-sm {
  box-shadow: 0 0 10px -2px oklch(var(--primary) / 0.2);
}
</style>
