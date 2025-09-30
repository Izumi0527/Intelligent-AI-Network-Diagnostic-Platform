<template>
  <div class="flex items-center justify-between">
    <span class="text-sm text-foreground/70">流式响应</span>
    <button 
      class="relative h-6 w-11 rounded-full transition-colors focus-visible:outline-none"
      :class="enabled ? 'bg-primary shadow-glow-sm' : 'bg-muted/70'"
      @click="$emit('toggle')"
    >
      <span
        class="absolute left-0.5 top-0.5 flex h-5 w-5 items-center justify-center rounded-full bg-white shadow-sm transition-transform duration-200"
        :class="enabled ? 'translate-x-5' : 'translate-x-0'"
      >
        <span 
          class="h-2.5 w-2.5 rounded-full" 
          :class="enabled ? 'bg-primary' : 'bg-muted-foreground'"
        ></span>
      </span>
    </button>
  </div>
</template>

<script setup lang="ts">
// Props
defineProps<{
  enabled: boolean
}>()

// Emits
defineEmits<{
  toggle: []
}>()
</script>
