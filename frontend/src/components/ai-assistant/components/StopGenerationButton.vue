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
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="currentColor"
          stroke="none"
          aria-hidden="true"
          focusable="false"
        >
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
  bottom: 12px;
  transform: translateX(-50%);
  z-index: 5;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 500;
  line-height: 1;
  color: oklch(var(--foreground));
  background: color-mix(in oklch, oklch(var(--background)) 80%, oklch(var(--muted)) 20%);
  border: 1px solid oklch(var(--border));
  border-radius: 999px;
  box-shadow: var(--shadow-card);
  cursor: pointer;
  backdrop-filter: blur(8px);
  transition:
    background-color var(--dur-fast) var(--ease-out),
    border-color var(--dur-fast) var(--ease-out),
    transform var(--dur-fast) var(--ease-out),
    box-shadow var(--dur-fast) var(--ease-out);
}

.stop-btn:hover {
  background: color-mix(in oklch, oklch(var(--background)) 65%, oklch(var(--muted)) 35%);
  border-color: oklch(0.55 0.18 30 / 0.5);
  box-shadow: 0 4px 12px oklch(0.55 0.18 30 / 0.15);
}

.stop-btn:focus-visible {
  outline: 2px solid oklch(0.55 0.18 30 / 0.6);
  outline-offset: 2px;
}

.stop-btn:active {
  transform: translateX(-50%) scale(0.96);
}

.stop-icon {
  display: inline-flex;
  color: oklch(0.55 0.18 30);
}

.stop-label {
  user-select: none;
}

/* 进出场动画 */
.stop-fade-enter-active,
.stop-fade-leave-active {
  transition: opacity var(--dur-base) var(--ease-out),
              transform var(--dur-base) var(--ease-out);
}
.stop-fade-enter-from,
.stop-fade-leave-to {
  opacity: 0;
  transform: translate(-50%, 8px);
}
</style>
