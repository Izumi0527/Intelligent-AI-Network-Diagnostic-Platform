<template>
  <div class="p-4 border-b border-border/60 bg-transparent rounded-t-xl">
    <div class="flex items-center justify-between mb-3">
      <h2 class="text-lg font-semibold text-foreground">
        AI智能助手
      </h2>
      <div class="flex gap-2">
        <ShimmerButton
          class="flex items-center gap-1 rounded-lg border border-border/40 px-2.5 py-1.5 text-xs font-medium text-foreground"
          background="oklch(var(--secondary))"
          shimmer-color="rgba(139, 92, 246, 0.5)"
          border-radius="0.5rem"
          @click="$emit('clear')"
          title="清空当前对话"
        >
          <ClearIcon class="w-3.5 h-3.5" />
          <span class="hidden sm:inline">清空对话</span>
        </ShimmerButton>
      </div>
    </div>
    
    <slot />
  </div>
</template>

<script setup lang="ts">
import { ClearIcon } from '@/components/common/icons'
import ShimmerButton from '@/components/ui/ShimmerButton.vue'

// 定义事件
defineEmits<{
  clear: []
}>()
</script>
