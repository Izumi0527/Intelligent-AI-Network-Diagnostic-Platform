<template>
  <div class="toggle-row">
    <span id="stream-toggle-label" class="toggle-row__label">流式响应</span>
    <button
      class="toggle-switch"
      :class="{ 'toggle-switch--on': enabled }"
      type="button"
      role="switch"
      :aria-checked="enabled"
      aria-labelledby="stream-toggle-label"
      @click="$emit('toggle')"
    >
      <span class="toggle-switch__thumb" />
    </button>
  </div>
</template>

<script setup lang="ts">
defineProps<{ enabled: boolean }>();
defineEmits<{ toggle: [] }>();
</script>

<style scoped>
.toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
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
