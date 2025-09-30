<template>
  <div 
    ref="cardRef"
    class="card-spotlight"
    :class="slotClass"
    @mousemove="handleMouseMove"
    @mouseleave="handleMouseLeave"
  >
    <div 
      class="spotlight-gradient"
      :style="gradientStyle"
    ></div>
    <div class="spotlight-content">
      <slot></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';

interface Props {
  gradientSize?: number;
  gradientColor?: string;
  gradientOpacity?: number;
  slotClass?: string;
}

const props = withDefaults(defineProps<Props>(), {
  gradientSize: 300,
  gradientColor: 'oklch(var(--primary))',
  gradientOpacity: 0.15,
  slotClass: ''
});

const cardRef = ref<HTMLElement>();
const mouseX = ref(0);
const mouseY = ref(0);
const isHovered = ref(false);

const gradientStyle = computed(() => {
  if (!isHovered.value) {
    return {
      opacity: '0',
      background: 'transparent'
    };
  }

  return {
    opacity: props.gradientOpacity.toString(),
    background: `radial-gradient(${props.gradientSize}px circle at ${mouseX.value}px ${mouseY.value}px, ${props.gradientColor}, transparent 70%)`,
    transition: 'opacity 0.3s ease'
  };
});

const handleMouseMove = (event: MouseEvent) => {
  if (!cardRef.value) return;
  
  const rect = cardRef.value.getBoundingClientRect();
  mouseX.value = event.clientX - rect.left;
  mouseY.value = event.clientY - rect.top;
  isHovered.value = true;
};

const handleMouseLeave = () => {
  isHovered.value = false;
};

onMounted(() => {
  if (cardRef.value) {
    // 确保卡片有适当的样式
    cardRef.value.style.position = 'relative';
    cardRef.value.style.overflow = 'hidden';
  }
});
</script>

<style scoped>
.card-spotlight {
  position: relative;
  overflow: hidden;
}

.spotlight-gradient {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.spotlight-content {
  position: relative;
  z-index: 2;
  height: 100%;
  width: 100%;
}
</style>