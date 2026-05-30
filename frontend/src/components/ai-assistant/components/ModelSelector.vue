<template>
  <div class="model-selector">
    <div class="model-selector__field">
      <select
        id="ai-model-selector"
        name="aiModel"
        :value="selectedModel"
        aria-label="模型选择"
        class="model-selector__select"
        @change="handleModelChange"
      >
        <option
          v-for="model in availableModels"
          :key="model.value"
          :value="model.value"
          :disabled="!model.available"
          :title="model.available ? '' : '该 provider API 密钥未配置或连接失败'"
        >
          {{ model.label }}{{ model.available ? '' : '（未配置）' }}
        </option>
      </select>
      <svg class="model-selector__chevron" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <polyline points="6 9 12 15 18 9"/>
      </svg>
    </div>

    <span
      class="model-selector__status"
      :data-state="isConnected ? 'connected' : 'disconnected'"
    >
      <span class="model-selector__dot" aria-hidden="true" />
      <span class="model-selector__status-text">{{ isConnected ? '已连接' : '未连接' }}</span>
    </span>
  </div>
</template>

<script setup lang="ts">
interface ModelOption {
  value: string
  label: string
  available: boolean
}

defineProps<{
  selectedModel: string
  availableModels: ModelOption[]
  isConnected: boolean
}>();

const emit = defineEmits<{
  'model-change': [value: string]
}>();

const handleModelChange = (event: Event): void => {
  const target = event.target as HTMLSelectElement;
  emit('model-change', target.value);
};
</script>

<style scoped>
.model-selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.model-selector__field {
  position: relative;
  flex: 1;
  min-width: 0;
}

.model-selector__select {
  width: 100%;
  height: 28px;
  padding: 0 28px 0 10px;
  font-size: 12px;
  background-color: var(--background);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--foreground);
  font-family: var(--app-font-sans);
  cursor: pointer;
  appearance: none;
  -webkit-appearance: none;
  transition: border-color var(--dur-enter) var(--ease-standard);
}

.model-selector__select:hover {
  border-color: color-mix(in oklch, var(--foreground) 16%, transparent);
}

.model-selector__select:focus-visible {
  outline: none;
  border-color: color-mix(in oklch, var(--primary) 55%, transparent);
  box-shadow: 0 0 0 2px color-mix(in oklch, var(--primary) 18%, transparent);
}

.model-selector__chevron {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--muted-foreground);
  pointer-events: none;
}

.model-selector__status {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  font-size: 11px;
  font-family: var(--app-font-mono);
  letter-spacing: 0.02em;
}

.model-selector__status[data-state='connected'] {
  background-color: color-mix(in oklch, var(--success) 14%, transparent);
  color: var(--success);
}

/* A2: Light 下 --success 作徽标文字落在 success14% 浅芯片上仅 ~4.4:1，压暗到 >=4.5
   (实测 6.14:1)。Dark 已达 7.51:1，仅在非 dark (html.light) 下覆盖。 */
html:not(.dark) .model-selector__status[data-state='connected'] {
  color: color-mix(in oklch, var(--success), black 18%);
}

.model-selector__status[data-state='disconnected'] {
  background-color: color-mix(in oklch, var(--destructive) 14%, transparent);
  color: var(--destructive);
}

.model-selector__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: currentColor;
}

.model-selector__status[data-state='connected'] .model-selector__dot {
  box-shadow: 0 0 0 2px color-mix(in oklch, var(--success) 25%, transparent);
}
</style>
