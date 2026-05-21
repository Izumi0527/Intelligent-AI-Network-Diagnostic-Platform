<template>
  <div
    ref="chatContainer"
    class="flex-1 overflow-y-auto p-4 space-y-6 bg-transparent"
    style="min-height: 400px;"
  >
    <!-- 空状态 -->
    <div v-if="messages.length === 0" class="flex h-full items-center justify-center">
      <div class="text-center max-w-sm p-8">
        <div class="text-4xl mb-4 opacity-30">💬</div>
        <p class="mb-2 text-gray-600 font-medium">与AI助手开始对话获取网络问题的帮助</p>
        <p class="text-sm text-gray-500">可以询问网络设备配置、故障排查方法或最佳实践</p>
      </div>
    </div>
    
    <!-- 消息列表 -->
    <template v-else>
      <div
        v-for="(message, index) in messages"
        :key="index"
        :class="[
          message.role === 'user' ? 'message-user flex flex-col items-end' : 'message-assistant',
          'group transition-all'
        ]"
      >
        <div
          :class="[
            'font-medium text-xs mb-1.5 opacity-70 group-hover:opacity-100 flex items-center gap-2 text-gray-600',
            message.role === 'user' ? 'flex-row-reverse' : ''
          ]"
        >
          <span class="inline-block w-5 h-5 rounded-full overflow-hidden flex items-center justify-center">
            <span v-if="message.role === 'user'" class="text-xs">👤</span>
            <span v-else class="text-xs">🤖</span>
          </span>
          <span class="text-gray-700">{{ message.role === 'user' ? '用户' : 'AI助手' }}</span>
          <span class="text-gray-400 text-[10px]">{{ formatTime(message.timestamp) }}</span>
        </div>

        <!-- 思考内容 (仅AI助手消息且有思考内容时显示) -->
        <div
          v-if="message.role === 'assistant' && message.thinking && message.thinking.content"
          class="ml-7 mb-2 p-3 bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg"
        >
          <div class="flex items-center gap-2 mb-2">
            <span class="text-blue-600 text-sm">🤔</span>
            <span class="text-blue-700 text-xs font-medium">AI思考过程</span>
            <span v-if="!message.thinking.isComplete" class="text-blue-500 text-xs">思考中...</span>
          </div>
          <div class="text-sm text-blue-800 whitespace-pre-wrap leading-relaxed">
            {{ message.thinking.content }}
          </div>
        </div>

        <div
          :class="[
            'rounded-lg px-4 py-3 max-w-none break-words transition-colors fade-in',
            message.role === 'user'
              ? 'bg-blue-500 text-white mr-7 border border-blue-600 max-w-md'
              : 'bg-gray-50 ml-7 border border-gray-200'
          ]"
        >
          <div
            v-if="message.role === 'assistant'"
            class="prose prose-base max-w-none prose-gray leading-relaxed prose-p:mb-4 prose-ul:my-3 prose-ol:my-3 prose-li:mb-1 prose-h1:mb-4 prose-h2:mb-3 prose-h3:mb-3 prose-pre:bg-gray-100 prose-pre:border prose-pre:p-3 prose-pre:rounded prose-code:bg-gray-100 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-blockquote:border-l-4 prose-blockquote:border-gray-300 prose-blockquote:pl-4"
            v-html="formatMessage(message.content)"
          ></div>
          <div v-else class="whitespace-pre-wrap text-sm leading-relaxed" :class="message.role === 'user' ? 'text-white' : 'text-gray-800'">{{ message.content }}</div>
        </div>
      </div>
    </template>
    
    <!-- 实时思考内容显示 - 当AI正在思考时显示 -->
    <div v-if="isThinking && currentThinkingContent" class="message-assistant group transition-all fade-in">
      <div class="font-medium text-xs mb-1.5 opacity-70 flex items-center gap-2 text-gray-600">
        <span class="inline-block w-5 h-5 rounded-full overflow-hidden flex items-center justify-center">
          <span class="text-xs">🤔</span>
        </span>
        <span class="text-blue-700">AI助手思考中</span>
        <span class="text-blue-400 text-[10px]">正在思考...</span>
      </div>
      <div class="rounded-lg px-3 py-2 bg-gradient-to-r from-blue-50 to-purple-50 ml-7 border border-blue-200">
        <div class="flex items-center gap-2 mb-2">
          <div class="w-2 h-2 bg-blue-400 rounded-full animate-pulse"></div>
          <span class="text-xs font-medium text-blue-700">思考过程</span>
        </div>
        <div class="text-sm text-blue-800 whitespace-pre-wrap leading-relaxed">
          {{ currentThinkingContent }}
        </div>
      </div>
    </div>

    <!-- 流式内容接收指示器 - 只在正在接收流式内容且非流式模式时显示 -->
    <div v-if="isStreamingContent && !streamingEnabled" class="message-assistant group transition-all fade-in">
      <div class="font-medium text-xs mb-1.5 opacity-70 flex items-center gap-2 text-gray-600">
        <span class="inline-block w-5 h-5 rounded-full overflow-hidden flex items-center justify-center">
          <span class="text-xs">🤖</span>
        </span>
        <span class="text-gray-700">AI助手</span>
        <span class="text-gray-400 text-[10px]">正在回复...</span>
      </div>
      <div class="rounded-lg px-3 py-2 bg-gray-50 ml-7 border border-gray-200">
        <div class="flex items-center gap-1">
          <div class="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
          <span class="text-sm text-gray-600 ml-2">正在接收内容中...</span>
        </div>
      </div>
    </div>

    <!-- 正在输入指示 - 只在等待响应且非流式内容接收且非流式模式时显示 -->
    <div v-if="isTyping && !isStreamingContent && !streamingEnabled" class="message-assistant group transition-all fade-in">
      <div class="font-medium text-xs mb-1.5 opacity-70 flex items-center gap-2 text-gray-600">
        <span class="inline-block w-5 h-5 rounded-full overflow-hidden flex items-center justify-center">
          <span class="text-xs">🤖</span>
        </span>
        <span class="text-gray-700">AI助手</span>
        <span class="text-gray-400 text-[10px]">正在输入...</span>
      </div>
      <div class="rounded-lg px-3 py-2 bg-gray-50 ml-7 border border-gray-200">
        <div class="flex items-center gap-1">
          <div class="flex space-x-1">
            <div class="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></div>
            <div class="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style="animation-delay: 0.1s"></div>
            <div class="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
          </div>
          <span class="text-sm text-gray-600 ml-2">AI助手正在思考中...</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, watchEffect } from 'vue'
import { marked } from 'marked'

interface ThinkingContent {
  content: string
  isComplete: boolean
  timestamp: number
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp?: number
  thinking?: ThinkingContent // 思考内容（仅限assistant角色）
}

const props = defineProps<{
  messages: Message[]
  isTyping: boolean
  isStreamingContent: boolean  // 新增：是否正在接收流式内容
  isThinking?: boolean  // 新增：是否正在思考
  currentThinkingContent?: string  // 新增：当前思考内容
  streamingEnabled?: boolean  // 新增：是否启用流式模式
}>()

const chatContainer = ref<HTMLElement>()

// 添加状态监控用于调试 - 接收到props时立即打印
watchEffect(() => {
  console.log('[ChatMessages] 状态监控:', {
    isTyping: props.isTyping,
    isStreamingContent: props.isStreamingContent,
    messagesCount: props.messages.length,
    timestamp: Date.now()
  })

  // 使用nextTick确保显示状态的及时更新
  nextTick(() => {
    if (props.isStreamingContent) {
      console.log('[ChatMessages] 正在接收流式内容，调用滚动')
      scrollToBottom()
    }
  })
})

const formatMessage = (content: string): string => {
  try {
    const result = marked.parse(content, { async: false })
    return typeof result === 'string' ? result : content
  } catch (error) {
    console.error('Markdown渲染错误:', error)
    return content
  }
}

const formatTime = (timestamp?: number): string => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

const scrollToBottom = async () => {
  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

watch(() => props.messages.length, scrollToBottom)
watch(() => props.isTyping, scrollToBottom)
watch(() => props.isStreamingContent, scrollToBottom)  // 监听流式状态变化

defineExpose({
  scrollToBottom
})
</script>

<style scoped>
.message-user { margin-bottom: 1.5rem; }
.message-assistant { margin-bottom: 1.5rem; }

/* 优化滚动条样式 */
.flex-1::-webkit-scrollbar {
  width: 6px;
}

.flex-1::-webkit-scrollbar-track {
  background: transparent;
}

.flex-1::-webkit-scrollbar-thumb {
  background: color-mix(in oklch, oklch(var(--muted)), oklch(var(--foreground)) 18%);
  border-radius: 3px;
}

.flex-1::-webkit-scrollbar-thumb:hover {
  background: color-mix(in oklch, oklch(var(--muted)), oklch(var(--foreground)) 32%);
}
</style>
