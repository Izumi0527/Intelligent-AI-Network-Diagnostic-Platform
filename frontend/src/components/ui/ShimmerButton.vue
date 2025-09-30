<template>
  <button 
    class="shimmer-button"
    :style="{
      '--shimmer-color': shimmerColor,
      '--shimmer-size': shimmerSize,
      '--border-radius': borderRadius,
      '--shimmer-duration': shimmerDuration,
      'background': background
    }"
    :class="className"
  >
    <slot></slot>
  </button>
</template>

<script setup lang="ts">
interface Props {
  className?: string;
  shimmerColor?: string;
  shimmerSize?: string;
  borderRadius?: string;
  shimmerDuration?: string;
  background?: string;
}

withDefaults(defineProps<Props>(), {
  class: '',
  shimmerColor: '#ffffff',
  shimmerSize: '0.05em',
  borderRadius: '0.75rem',
  shimmerDuration: '2s',
  background: 'oklch(var(--primary))'
});
</script>

<style scoped>
.shimmer-button {
  position: relative;
  padding: 0.75em 1.5em;
  border: none;
  overflow: hidden;
  cursor: pointer;
  color: currentColor;
  background: v-bind(background);
  border-radius: var(--border-radius);
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s ease;
  box-shadow: 0 0 20px -5px oklch(var(--primary) / 0.4);
}

.shimmer-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 0 30px -3px oklch(var(--primary) / 0.6);
}

.shimmer-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.shimmer-button::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    100deg,
    rgba(255, 255, 255, 0) 0%,
    var(--shimmer-color) 50%,
    rgba(255, 255, 255, 0) 100%
  );
  transform: translateX(-100%);
  animation: shimmer var(--shimmer-duration) infinite;
  opacity: 0.6;
}

.shimmer-button:hover::before {
  animation-duration: calc(var(--shimmer-duration) * 0.7);
}

@keyframes shimmer {
  100% {
    transform: translateX(100%);
  }
}
</style>