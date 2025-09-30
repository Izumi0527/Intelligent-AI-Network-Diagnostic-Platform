<template>
  <div class="flex items-center gap-3">
    <div class="flex-1">
      <select 
        :value="selectedModel"
        @change="handleModelChange"
        class="w-full rounded-lg border border-border/40 bg-background/50 px-3 py-2 text-sm input-glow"
      >
        <option 
          v-for="model in availableModels" 
          :key="model.value" 
          :value="model.value"
        >
          {{ model.label }}
        </option>
      </select>
    </div>
    
    <div 
      class="px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1.5"
      :class="isConnected ? 'bg-success/10 text-success' : 'bg-destructive/10 text-destructive'"
    >
      <span 
        class="block w-1.5 h-1.5 rounded-full"
        :class="isConnected ? 'bg-success animate-pulse' : 'bg-destructive'"
      ></span>
      <span>{{ isConnected ? '已连接' : '未连接' }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
interface ModelOption {
  value: string
  label: string
}

defineProps<{
  selectedModel: string
  availableModels: ModelOption[]
  isConnected: boolean
}>()

const emit = defineEmits<{
  'model-change': [value: string]
}>()

const handleModelChange = (event: Event) => {
  const target = event.target as HTMLSelectElement
  emit('model-change', target.value)
}
</script>

