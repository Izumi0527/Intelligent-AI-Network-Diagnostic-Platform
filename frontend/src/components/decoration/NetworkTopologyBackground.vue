<template>
  <svg
    class="topology-bg"
    :class="{ 'topology-bg--subtle': subtle }"
    aria-hidden="true"
    xmlns="http://www.w3.org/2000/svg"
  >
    <defs>
      <!--
        SVG pattern: 节点 + 连线网格.
        每个 64x64 单元格包含 1 个节点 (圆点) 和 4 条连线 (上下左右半段),
        平铺即形成连续的网络拓扑视觉.
      -->
      <pattern
        id="topology-grid"
        x="0"
        y="0"
        width="64"
        height="64"
        patternUnits="userSpaceOnUse"
      >
        <!-- 节点 -->
        <circle cx="32" cy="32" r="1.5" fill="currentColor" />
        <!-- 横向连线 -->
        <line x1="32" y1="32" x2="64" y2="32" stroke="currentColor" stroke-width="0.5" />
        <line x1="0" y1="32" x2="32" y2="32" stroke="currentColor" stroke-width="0.5" />
        <!-- 纵向连线 -->
        <line x1="32" y1="32" x2="32" y2="64" stroke="currentColor" stroke-width="0.5" />
        <line x1="32" y1="0" x2="32" y2="32" stroke="currentColor" stroke-width="0.5" />
      </pattern>
    </defs>

    <rect width="100%" height="100%" fill="url(#topology-grid)" />
  </svg>
</template>

<script setup lang="ts">
/**
 * 网络拓扑底纹：absolute fill 的 SVG pattern，1.5% 不透明度。
 * 用于 MainLayout 主区域作"网络运维"主题视觉锚点。
 * pointer-events:none 不阻挡交互。
 */
interface Props {
  /** 是否更微弱 (用于明色背景上避免过亮，默认 false 用 1.5%；true 用 1%) */
  subtle?: boolean
}

withDefaults(defineProps<Props>(), { subtle: false });
</script>

<style scoped>
.topology-bg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
  color: var(--foreground);
  opacity: 0.018;
}

.topology-bg--subtle {
  opacity: 0.012;
}

.dark .topology-bg {
  opacity: 0.04;
}

.dark .topology-bg--subtle {
  opacity: 0.025;
}
</style>
