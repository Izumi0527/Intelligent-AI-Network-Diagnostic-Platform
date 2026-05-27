<template>
  <span
    class="packet-signal"
    :class="`packet-signal--${mode}`"
    :aria-label="ariaLabel"
    role="status"
  >
    <span class="packet-signal__dot" />
    <span class="packet-signal__dot" />
    <span class="packet-signal__dot" />
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue';

/**
 * 数据包信号灯：3 圆点序列，模拟数据包传输状态。
 *  - idle:     灰色静态
 *  - sending:  循环脉冲（蓝→绿），错相位 0.4s（替代 animate-pulse 表达"思考中"）
 *  - received: 全绿停顿（短暂提示完成）
 */
interface Props {
  mode?: 'idle' | 'sending' | 'received'
}

const props = withDefaults(defineProps<Props>(), { mode: 'sending' });

const ariaLabel = computed(() => {
  switch (props.mode) {
    case 'sending': return '正在传输';
    case 'received': return '已接收';
    default: return '空闲';
  }
});
</script>

<style scoped>
.packet-signal {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  height: 8px;
}

.packet-signal__dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background-color: var(--zinc-400);
  transition: background-color var(--dur-base) var(--ease-standard);
}

/* sending：三个圆点错相位脉冲 */
.packet-signal--sending .packet-signal__dot {
  animation: packetPulse 1.2s var(--ease-standard) infinite;
}

.packet-signal--sending .packet-signal__dot:nth-child(2) {
  animation-delay: 0.18s;
}

.packet-signal--sending .packet-signal__dot:nth-child(3) {
  animation-delay: 0.36s;
}

/* received：全绿静态 */
.packet-signal--received .packet-signal__dot {
  background-color: var(--success);
}

/* idle：灰色静态（已是默认） */

@media (prefers-reduced-motion: reduce) {
  .packet-signal--sending .packet-signal__dot {
    animation: none;
    background-color: var(--primary);
  }
}
</style>
