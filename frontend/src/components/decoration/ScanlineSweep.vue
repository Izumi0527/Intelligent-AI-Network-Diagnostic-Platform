<template>
  <span
    class="scanline-sweep"
    :class="`scanline-sweep--${mode}`"
    role="status"
    :aria-label="ariaLabel"
  >
    <span class="scanline-sweep__track">
      <span class="scanline-sweep__beam" />
    </span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue';

/**
 * 扫描光束：一束琥珀光在轨道上往复扫描，模拟雷达 / 示波器数据处理。
 * Industrial HUD 下替代圆点脉冲，表达"系统正在分析"。
 *  - idle:     暗 bracket 静止
 *  - scanning: 琥珀光束循环扫描 (带辉光)
 *  - done:     全轨道点亮为 ok 绿
 */
interface Props {
  mode?: 'idle' | 'scanning' | 'done'
}

const props = withDefaults(defineProps<Props>(), { mode: 'scanning' });

const ariaLabel = computed<string>(() => {
  switch (props.mode) {
    case 'scanning': return '正在分析';
    case 'done': return '已完成';
    default: return '空闲';
  }
});
</script>

<style scoped>
.scanline-sweep {
  display: inline-flex;
  align-items: center;
  height: 8px;
}

.scanline-sweep__track {
  position: relative;
  width: 30px;
  height: 2px;
  overflow: hidden;
  border-radius: 1px;
  background: color-mix(in oklch, var(--hud-bracket) 45%, transparent);
}

.scanline-sweep__beam {
  position: absolute;
  inset: 0 auto 0 0;
  width: 40%;
  height: 100%;
  background: var(--hud-amber);
  box-shadow: 0 0 4px var(--hud-glow);
}

.scanline-sweep--scanning .scanline-sweep__beam {
  animation: scanline-beam 1.1s var(--ease-standard) infinite;
}

.scanline-sweep--idle .scanline-sweep__beam {
  background: var(--hud-bracket);
  box-shadow: none;
  opacity: 0.5;
}

.scanline-sweep--done .scanline-sweep__beam {
  width: 100%;
  background: var(--hud-ok);
  box-shadow: none;
}

@keyframes scanline-beam {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(250%); }
}

@media (prefers-reduced-motion: reduce) {
  .scanline-sweep--scanning .scanline-sweep__beam {
    animation: none;
    width: 100%;
    opacity: 0.7;
  }
}
</style>
