<template>
  <button 
    ref="buttonRef"
    :class="['ripple-button', buttonClass]"
    @click="handleClick"
    :disabled="disabled"
  >
    <span class="ripple-content">
      <slot></slot>
    </span>
    <span 
      v-for="ripple in ripples" 
      :key="ripple.id"
      class="ripple"
      :style="{
        left: ripple.x + 'px',
        top: ripple.y + 'px',
        backgroundColor: rippleColor,
        animationDuration: duration + 'ms'
      }"
    ></span>
  </button>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';

interface Props {
  class?: string;
  rippleColor?: string;
  duration?: number;
  disabled?: boolean;
}

interface Ripple {
  id: number;
  x: number;
  y: number;
}

const props = withDefaults(defineProps<Props>(), {
  class: '',
  rippleColor: 'rgba(255, 255, 255, 0.6)',
  duration: 600,
  disabled: false
});

const emit = defineEmits<{
  click: [event: MouseEvent];
}>();

const buttonRef = ref<HTMLButtonElement>();
const ripples = ref<Ripple[]>([]);

const buttonClass = computed(() => [
  'relative overflow-hidden transition-all duration-200 border-0 cursor-pointer',
  'bg-primary text-primary-foreground hover:bg-primary/90',
  'rounded-lg px-4 py-2 font-medium text-sm',
  'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
  'disabled:opacity-50 disabled:cursor-not-allowed',
  'shadow-glow-sm hover:shadow-glow-md',
  props.class
]);

const handleClick = (event: MouseEvent) => {
  if (props.disabled) return;
  
  createRipple(event);
  emit('click', event);
};

const createRipple = (event: MouseEvent) => {
  if (!buttonRef.value) return;

  const button = buttonRef.value;
  const rect = button.getBoundingClientRect();
  
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  
  const ripple: Ripple = {
    id: Date.now() + Math.random(),
    x: x - 10, // Offset for ripple size
    y: y - 10
  };
  
  ripples.value.push(ripple);
  
  // Remove ripple after animation
  setTimeout(() => {
    const index = ripples.value.findIndex(r => r.id === ripple.id);
    if (index > -1) {
      ripples.value.splice(index, 1);
    }
  }, props.duration);
};
</script>

<style scoped>
.ripple-button {
  position: relative;
  overflow: hidden;
}

.ripple-content {
  position: relative;
  z-index: 1;
}

.ripple {
  position: absolute;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  pointer-events: none;
  transform: scale(0);
  animation: ripple-animation var(--duration, 600ms) ease-out;
  z-index: 0;
}

@keyframes ripple-animation {
  0% {
    transform: scale(0);
    opacity: 0.6;
  }
  50% {
    opacity: 0.3;
  }
  100% {
    transform: scale(20);
    opacity: 0;
  }
}
</style>