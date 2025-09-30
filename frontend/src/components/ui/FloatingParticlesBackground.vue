<template>
  <div class="floating-particles-bg">
    <div 
      v-for="particle in particles" 
      :key="particle.id"
      class="particle"
      :style="particle.style"
    ></div>
    <div v-if="!disableOverlay" class="gradient-overlay"></div>
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';

interface Props {
  /** 是否禁用覆盖性的渐变遮罩（便于查看底部背景） */
  disableOverlay?: boolean;
}

withDefaults(defineProps<Props>(), {
  disableOverlay: false,
});

interface Particle {
  id: number;
  style: {
    left: string;
    top: string;
    width: string;
    height: string;
    animationDelay: string;
    animationDuration: string;
    opacity: string;
  };
}

const particles = ref<Particle[]>([]);
let animationId: number;

const createParticles = () => {
  const particleCount = 8;
  const newParticles: Particle[] = [];

  for (let i = 0; i < particleCount; i++) {
    const particle: Particle = {
      id: i,
      style: {
        left: Math.random() * 100 + '%',
        top: Math.random() * 100 + '%',
        width: (Math.random() * 6 + 2) + 'px',
        height: (Math.random() * 6 + 2) + 'px',
        animationDelay: (Math.random() * 20) + 's',
        animationDuration: (Math.random() * 10 + 15) + 's',
        opacity: (Math.random() * 0.3 + 0.1).toString()
      }
    };
    newParticles.push(particle);
  }

  particles.value = newParticles;
};

const animateParticles = () => {
  // Update particle positions subtly
  particles.value.forEach(particle => {
    const currentLeft = parseFloat(particle.style.left);
    const currentTop = parseFloat(particle.style.top);
    
    // Very slow drift movement
    const newLeft = currentLeft + (Math.random() - 0.5) * 0.02;
    const newTop = currentTop + (Math.random() - 0.5) * 0.02;
    
    // Keep within bounds
    particle.style.left = Math.max(0, Math.min(100, newLeft)) + '%';
    particle.style.top = Math.max(0, Math.min(100, newTop)) + '%';
  });
  
  animationId = requestAnimationFrame(animateParticles);
};

onMounted(() => {
  createParticles();
  animateParticles();
});

onUnmounted(() => {
  if (animationId) {
    cancelAnimationFrame(animationId);
  }
});
</script>

<style scoped>
.floating-particles-bg {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.particle {
  position: absolute;
  background: linear-gradient(45deg, 
    oklch(var(--primary) / 0.4), 
    oklch(var(--accent) / 0.3)
  );
  border-radius: 50%;
  pointer-events: none;
  animation: float-around linear infinite;
}

.gradient-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(
    135deg,
    transparent 0%,
    oklch(var(--primary) / 0.015) 30%,
    oklch(var(--accent) / 0.01) 70%,
    transparent 100%
  );
  pointer-events: none;
  z-index: 1;
}

.floating-particles-bg > :not(.particle):not(.gradient-overlay) {
  position: relative;
  z-index: 2;
}

@keyframes float-around {
  0%, 100% {
    transform: translate(0, 0) rotate(0deg) scale(1);
  }
  25% {
    transform: translate(-20px, -20px) rotate(90deg) scale(1.1);
  }
  50% {
    transform: translate(20px, -10px) rotate(180deg) scale(0.9);
  }
  75% {
    transform: translate(-10px, 20px) rotate(270deg) scale(1.05);
  }
}
</style>
