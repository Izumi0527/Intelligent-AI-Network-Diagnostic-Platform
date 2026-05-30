<template>
  <div
    class="hud-frame"
    :class="{ 'hud-frame--active': active, 'hud-frame--borderless': !bordered }"
  >
    <span
      v-if="label"
      class="hud-frame__label"
    >{{ label }}</span>
    <template v-if="showCorners">
      <span class="hud-frame__corner hud-frame__corner--tl" aria-hidden="true" />
      <span class="hud-frame__corner hud-frame__corner--tr" aria-hidden="true" />
      <span class="hud-frame__corner hud-frame__corner--bl" aria-hidden="true" />
      <span class="hud-frame__corner hud-frame__corner--br" aria-hidden="true" />
    </template>
    <div class="hud-frame__body">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

/**
 * HUD 容器框：四角 L 角标 + 可选顶部标签。
 * 标记"活动 / 可交互区域"，active 时角标点亮为主灯色 (非纯装饰)。
 */
interface Props {
  /** 是否高亮 (角标 + 边框点亮为主灯色) */
  active?: boolean
  /** 顶部 mono 标签 (压在边框上) */
  label?: string
  /** 角标显隐 */
  corners?: 'all' | 'none'
  /**
   * 是否绘制自身边框 / 卡片底色。
   * 默认 true（独立 HUD 卡片）。
   * false 时仅保留 L 角标 + label 作"焦点框叠加层"，
   * 用于包裹已有边框的面板（终端 / AI），避免双边框。
   */
  bordered?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  active: false,
  label: '',
  corners: 'all',
  bordered: true
});

const showCorners = computed<boolean>(() => props.corners !== 'none');
</script>

<style scoped>
.hud-frame {
  position: relative;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: color-mix(in oklch, var(--card) 55%, transparent);
  transition: border-color var(--dur-base) var(--ease-hud);
}

/* 叠加层模式：不画边框 / 底色，只保留 L 角标 + label 作焦点框 */
.hud-frame--borderless {
  border-color: transparent;
  background: transparent;
}

.hud-frame--active {
  border-color: color-mix(in oklch, var(--primary) 50%, var(--border));
}

/* 焦点框：内部元素获焦时点亮（与 active 同效），表达"当前操作面板" */
.hud-frame:not(.hud-frame--borderless):focus-within {
  border-color: color-mix(in oklch, var(--primary) 50%, var(--border));
}

.hud-frame__label {
  position: absolute;
  top: -7px;
  left: 10px;
  z-index: 1;
  padding: 0 6px;
  font-family: var(--app-font-mono);
  font-size: 9px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--muted-foreground);
  background: var(--background);
}

.hud-frame--active .hud-frame__label,
.hud-frame:focus-within .hud-frame__label {
  color: var(--primary);
}

.hud-frame__corner {
  position: absolute;
  width: 10px;
  height: 10px;
  border: 0 solid var(--hud-bracket);
  transition: border-color var(--dur-base) var(--ease-hud);
}

.hud-frame--active .hud-frame__corner,
.hud-frame:focus-within .hud-frame__corner {
  border-color: var(--hud-bracket-active);
}

.hud-frame__corner--tl { top: -1px; left: -1px; border-top-width: 2px; border-left-width: 2px; }
.hud-frame__corner--tr { top: -1px; right: -1px; border-top-width: 2px; border-right-width: 2px; }
.hud-frame__corner--bl { bottom: -1px; left: -1px; border-bottom-width: 2px; border-left-width: 2px; }
.hud-frame__corner--br { bottom: -1px; right: -1px; border-bottom-width: 2px; border-right-width: 2px; }

.hud-frame__body {
  position: relative;
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
</style>
