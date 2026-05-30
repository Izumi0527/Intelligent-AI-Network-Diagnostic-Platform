<template>
  <div
    class="hud-bg"
    :class="{ 'hud-bg--subtle': subtle }"
    aria-hidden="true"
  >
    <div class="hud-bg__grid" />
    <div class="hud-bg__scanline" />
    <span class="hud-bg__corner hud-bg__corner--tl" />
    <span class="hud-bg__corner hud-bg__corner--tr" />
    <span class="hud-bg__corner hud-bg__corner--bl" />
    <span class="hud-bg__corner hud-bg__corner--br" />
  </div>
</template>

<script setup lang="ts">
/**
 * HUD 网格背景：双层网格 (粗 96px + 细 16px) + 慢扫描线 + viewport 四角 L 角标。
 * Industrial HUD 视觉锚点，标记整个工作区边界。
 * absolute fill + pointer-events:none，不阻挡交互。
 */
interface Props {
  /** 更弱网格 (用于内容密集区) */
  subtle?: boolean
}

withDefaults(defineProps<Props>(), { subtle: false });
</script>

<style scoped>
.hud-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
}

/* 双层网格：粗线定区域 + 细线给精度 */
.hud-bg__grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(var(--hud-grid-coarse) 1px, transparent 1px),
    linear-gradient(90deg, var(--hud-grid-coarse) 1px, transparent 1px),
    linear-gradient(var(--hud-grid-fine) 1px, transparent 1px),
    linear-gradient(90deg, var(--hud-grid-fine) 1px, transparent 1px);
  background-size: 96px 96px, 96px 96px, 16px 16px, 16px 16px;
  background-position: -1px -1px;
}

.hud-bg--subtle .hud-bg__grid {
  opacity: 0.5;
}

/* 慢扫描线：从顶部缓慢下扫，表达"系统在线" */
.hud-bg__scanline {
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  height: 42%;
  background: linear-gradient(
    to bottom,
    transparent,
    var(--hud-scanline) 60%,
    transparent
  );
  animation: hud-scan var(--dur-scan) var(--ease-standard) infinite;
  will-change: transform;
}

@keyframes hud-scan {
  0% { transform: translateY(-100%); }
  100% { transform: translateY(340%); }
}

/* viewport 四角 L 角标：标记工作区边界 */
.hud-bg__corner {
  position: absolute;
  width: 20px;
  height: 20px;
  border: 0 solid var(--hud-bracket);
}
.hud-bg__corner--tl { top: 10px; left: 10px; border-top-width: 2px; border-left-width: 2px; }
.hud-bg__corner--tr { top: 10px; right: 10px; border-top-width: 2px; border-right-width: 2px; }
.hud-bg__corner--bl { bottom: 10px; left: 10px; border-bottom-width: 2px; border-left-width: 2px; }
.hud-bg__corner--br { bottom: 10px; right: 10px; border-bottom-width: 2px; border-right-width: 2px; }

@media (prefers-reduced-motion: reduce) {
  .hud-bg__scanline {
    animation: none;
    opacity: 0;
  }
}
</style>
