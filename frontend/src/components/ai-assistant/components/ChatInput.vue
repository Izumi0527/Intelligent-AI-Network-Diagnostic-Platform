<template>
  <div class="p-4 border-t border-border/60 bg-transparent rounded-b-xl">
    <div class="flex gap-2 items-end">
      <div class="flex-1 relative">
        <textarea
          ref="messageInput"
          v-model="message"
          :disabled="!!disabled"
          @keydown="handleKeyDown"
          @input="handleInput"
          placeholder="输入你的问题...(Shift+Enter 换行, Enter 发送)"
          class="w-full resize-none rounded-lg border border-border/85 bg-background/50 px-3 py-2 text-sm min-h-[40px] max-h-[120px] focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/40 input-glow transition-colors placeholder:text-muted-foreground/60"
          :class="{ 
            'opacity-50 cursor-not-allowed': !!disabled,
            'pr-10': hasError
          }"
        />
        
        <!-- 错误提示 -->
        <div 
          v-if="hasError" 
          class="absolute right-2 top-2 text-destructive"
          :title="errorMessage"
        >
          <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
          </svg>
        </div>
      </div>
      
      <ShimmerButton
        :disabled="!canSend"
        class="flex items-center justify-center w-11 h-11 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed text-white shadow-glow-sm ring-1 ring-primary/40"
        background="oklch(var(--primary))"
        shimmer-color="rgba(255, 255, 255, 0.6)"
        border-radius="0.5rem"
        title="发送消息"
        @click="handleSend"
      >
        <SendIcon class="w-4 h-4" />
      </ShimmerButton>
    </div>
    
    <!-- 字符计数和提示 -->
    <div class="flex justify-between items-center mt-2 text-xs text-muted-foreground/60">
      <div class="flex items-center gap-4">
        <span>{{ message.length }}/{{ maxLength }} 字符</span>
        <span v-if="disabled" class="text-orange-500">{{ statusText }}</span>
      </div>
      <div class="text-[10px] opacity-60">Shift+Enter 换行 · Enter 发送</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { SendIcon } from '@/components/common/icons'
import ShimmerButton from '@/components/ui/ShimmerButton.vue'

const props = withDefaults(defineProps<{
  disabled?: boolean
  statusText?: string
  maxLength?: number
  placeholder?: string
}>(), {
  disabled: false,
  statusText: '',
  maxLength: 2000,
  placeholder: '输入你的问题...(Shift+Enter 换行, Enter 发送)'
})

const emit = defineEmits<{
  send: [message: string]
  input: [message: string]
}>()

const message = ref('')
const messageInput = ref<HTMLTextAreaElement>()

const canSend = computed(() => {
  return !props.disabled && message.value.trim().length > 0 && message.value.length <= props.maxLength
})

const hasError = computed(() => message.value.length > props.maxLength)

const errorMessage = computed(() => {
  if (hasError.value) {
    return `内容超出限制，最多 ${props.maxLength} 字符`
  }
  return ''
})

const handleSend = () => {
  if (!canSend.value) return
  const content = message.value.trim()
  if (content) {
    emit('send', content)
    message.value = ''
    adjustTextareaHeight()
  }
}

const handleKeyDown = (event: KeyboardEvent) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSend()
  }
}

const handleInput = () => {
  emit('input', message.value)
  adjustTextareaHeight()
}

const adjustTextareaHeight = async () => {
  await nextTick()
  if (messageInput.value) {
    messageInput.value.style.height = 'auto'
    const scrollHeight = messageInput.value.scrollHeight
    const maxHeight = 120
    messageInput.value.style.height = Math.min(scrollHeight, maxHeight) + 'px'
  }
}

const focus = () => { messageInput.value?.focus() }
const clear = () => { message.value = ''; adjustTextareaHeight() }

watch(() => props.disabled, (disabled) => { if (!disabled) focus() })

defineExpose({ focus, clear })
</script>

<style scoped>
textarea { field-sizing: content; }
</style>
