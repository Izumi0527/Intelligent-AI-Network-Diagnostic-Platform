<template>
  <div class="toggle-row">
    <search-icon class="toggle-row__icon" :size="13" aria-hidden="true" />
    <span :id="labelId" class="toggle-row__label">联网搜索</span>
    <button
      class="toggle-switch"
      :class="{ 'toggle-switch--on': enabled }"
      type="button"
      role="switch"
      :aria-checked="enabled"
      :aria-labelledby="labelId"
      @click="$emit('toggle')"
    >
      <span class="toggle-switch__thumb" />
    </button>
  </div>
</template>

<script setup lang="ts">
import { SearchIcon } from '@/components/common/icons';

defineProps<{ enabled: boolean }>();
defineEmits<{ toggle: [] }>();

const labelId = 'search-toggle-label';
</script>

<style scoped>
.toggle-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.toggle-row__icon {
  color: var(--muted-foreground);
}

.toggle-row__label {
  font-size: 12px;
  color: var(--muted-foreground);
}

.toggle-switch {
  position: relative;
  width: 32px;
  height: 18px;
  border-radius: 999px;
  background-color: var(--muted);
  border: 1px solid var(--border);
  cursor: pointer;
  transition: background-color var(--dur-enter) var(--ease-standard);
  flex-shrink: 0;
  margin-left: 2px;
}

.toggle-switch:hover {
  border-color: color-mix(in oklch, var(--foreground) 16%, transparent);
}

.toggle-switch:focus-visible {
  outline: 2px solid color-mix(in oklch, var(--primary) 50%, transparent);
  outline-offset: 2px;
}

.toggle-switch--on {
  background-color: var(--primary);
  border-color: color-mix(in oklch, var(--primary), black 8%);
}

.toggle-switch__thumb {
  position: absolute;
  top: 50%;
  left: 2px;
  transform: translateY(-50%);
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background-color: var(--background);
  transition: transform var(--dur-enter) var(--ease-standard);
}

.toggle-switch--on .toggle-switch__thumb {
  transform: translate(14px, -50%);
}
</style>
