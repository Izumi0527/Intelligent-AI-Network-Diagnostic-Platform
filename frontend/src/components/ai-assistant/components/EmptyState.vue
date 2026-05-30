<template>
  <div class="empty-state">
    <div class="empty-state__inner">
      <div class="empty-state__head">
        <span class="empty-state__sigil">[ AI ]</span>
        <p class="empty-state__title">AI 助手就绪</p>
        <p class="empty-state__hint">选择下方诊断预设，或直接输入网络故障现象</p>
      </div>

      <ul
        class="empty-state__grid"
        aria-label="示例提示词"
      >
        <li v-for="(item, i) in prompts" :key="i">
          <button
            type="button"
            class="prompt-card"
            @click="onSelect(item.prompt)"
          >
            <span class="prompt-card__idx">{{ String(i + 1).padStart(2, '0') }}</span>
            <span class="prompt-card__body">
              <span class="prompt-card__title">{{ item.title }}</span>
              <span class="prompt-card__prompt">{{ item.prompt }}</span>
            </span>
          </button>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

export interface SamplePrompt {
  title: string
  prompt: string
  icon?: string
}

interface Props {
  samplePrompts?: SamplePrompt[]
}

const props = withDefaults(defineProps<Props>(), {
  // 注意：defineProps 默认值函数会被 hoist 到 setup 外，不能引用本地变量；
  // 因此 4 条默认 prompt 内联在此
  samplePrompts: () => [
    { title: 'OSPF 协议原理', prompt: '解释 OSPF 协议的工作原理，重点说明 LSA 类型与 SPF 计算流程。' },
    { title: '排查端口环路', prompt: '交换机端口频繁 flap、CPU 飙高，怀疑环路，给我一套从 STP 到 storm-control 的排查方法。' },
    { title: 'Cisco vs 华为 命令对照', prompt: '给我一份常用 Cisco 与华为命令对照表，覆盖 show interface、配置 trunk、查看 MAC 地址表等场景。' },
    { title: 'BGP neighbor down 根因', prompt: '如何快速定位 BGP neighbor down 的根因？请按 TCP 层 / OPEN 报文 / TTL / 时钟偏差 分层给出排查清单。' }
  ]
});

const emit = defineEmits<{
  select: [prompt: string]
}>();

const prompts = computed<SamplePrompt[]>(() => props.samplePrompts);

const onSelect = (prompt: string): void => {
  emit('select', prompt);
};
</script>

<style scoped>
.empty-state {
  position: relative;
  display: flex;
  height: 100%;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

/* HUD 双层网格底：粗 96px 定区 + 细 16px 给精度，克制不喧宾夺主 */
.empty-state::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  background-image:
    linear-gradient(var(--hud-grid-coarse) 1px, transparent 1px),
    linear-gradient(90deg, var(--hud-grid-coarse) 1px, transparent 1px),
    linear-gradient(var(--hud-grid-fine) 1px, transparent 1px),
    linear-gradient(90deg, var(--hud-grid-fine) 1px, transparent 1px);
  background-size: 96px 96px, 96px 96px, 16px 16px, 16px 16px;
  background-position: -1px -1px;
  opacity: 0.5;
}

.empty-state__inner {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 42rem;
}

.empty-state__head {
  text-align: center;
  margin-bottom: 20px;
}

.empty-state__sigil {
  display: inline-block;
  font-family: var(--app-font-mono);
  font-size: 11px;
  letter-spacing: 0.2em;
  color: var(--primary);
  border: 1px solid color-mix(in oklch, var(--primary) 40%, var(--border));
  padding: 3px 10px;
  border-radius: var(--radius);
  margin-bottom: 12px;
}

.empty-state__title {
  font-size: 15px;
  font-weight: 500;
  color: var(--foreground);
  margin: 0 0 4px;
}

.empty-state__hint {
  font-size: 12.5px;
  color: var(--muted-foreground);
  margin: 0;
}

.empty-state__grid {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
}

@media (min-width: 640px) {
  .empty-state__grid {
    grid-template-columns: 1fr 1fr;
  }
}

.prompt-card {
  position: relative;
  display: flex;
  gap: 10px;
  width: 100%;
  text-align: left;
  padding: 12px;
  background: color-mix(in oklch, var(--card) 50%, transparent);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  cursor: pointer;
  transition:
    border-color var(--dur-base) var(--ease-hud),
    background-color var(--dur-base) var(--ease-hud);
}

.prompt-card:hover {
  border-color: color-mix(in oklch, var(--primary) 50%, var(--border));
  background: color-mix(in oklch, var(--primary) 6%, transparent);
}

.prompt-card:active {
  transform: scale(0.985);
}

.prompt-card:focus-visible {
  outline: 2px solid color-mix(in oklch, var(--primary) 60%, transparent);
  outline-offset: 2px;
}

.prompt-card__idx {
  flex-shrink: 0;
  font-family: var(--app-font-mono);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.05em;
  color: var(--primary);
  margin-top: 1px;
}

.prompt-card__body {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.prompt-card__title {
  font-size: 13px;
  font-weight: 500;
  color: var(--foreground);
}

.prompt-card__prompt {
  font-size: 11.5px;
  color: var(--muted-foreground);
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

@media (prefers-reduced-motion: reduce) {
  .prompt-card {
    transition: none !important;
  }
}
</style>
