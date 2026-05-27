<template>
  <transition name="stop-fade">
    <button
      v-if="visible"
      type="button"
      class="stop-btn"
      aria-label="停止生成"
      title="停止生成"
      @click="emit('stop')"
    >
      <span class="stop-icon" aria-hidden="true">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" stroke="none" aria-hidden="true">
          <rect x="6" y="6" width="12" height="12" rx="1.5" />
        </svg>
      </span>
      <span class="stop-label">停止生成</span>
    </button>
  </transition>
</template>

<script setup lang="ts">
interface Props {
  visible: boolean
}

defineProps<Props>();

const emit = defineEmits<{
  stop: []
}>();
</script>

<style scoped>
.stop-btn {
  position: absolute;
  left: 50%;
  bottom: 16px;
  transform: translateX(-50%);
  z-index: 5;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 500;
  line-height: 1;
  color: var(--foreground);
  background-color: var(--background);
  border: 1px solid var(--border);
  border-radius: 999px;
  box-shadow: var(--shadow-card);
  cursor: pointer;
  transition:
    background-color var(--dur-enter) var(--ease-standard),
    border-color var(--dur-enter) var(--ease-standard),
    transform var(--dur-enter) var(--ease-standard);
}

.stop-btn:hover {
  border-color: color-mix(in oklch, var(--destructive) 50%, transparent);
  background-color: color-mix(in oklch, var(--destructive) 6%, var(--background));
}

.stop-btn:focus-visible {
  outline: 2px solid color-mix(in oklch, var(--destructive) 55%, transparent);
  outline-offset: 2px;
}

.stop-btn:active {
  transform: translateX(-50%) scale(0.96);
}

.stop-icon {
  display: inline-flex;
  color: var(--destructive);
}

.stop-label { user-select: none; }

.stop-fade-enter-active,
.stop-fade-leave-active {
  transition:
    opacity var(--dur-base) var(--ease-standard),
    transform var(--dur-base) var(--ease-standard);
}
.stop-fade-enter-from,
.stop-fade-leave-to {
  opacity: 0;
  transform: translate(-50%, 8px);
}
</style>
