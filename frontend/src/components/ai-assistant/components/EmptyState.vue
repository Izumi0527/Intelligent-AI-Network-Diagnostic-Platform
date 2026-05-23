<template>
  <div class="flex h-full items-center justify-center p-4">
    <div class="w-full max-w-2xl">
      <div class="text-center mb-6">
        <div class="text-4xl mb-3 opacity-40" aria-hidden="true">💬</div>
        <p class="text-foreground/85 font-medium text-base mb-1">与AI助手开始对话</p>
        <p class="text-sm text-muted-foreground">点击下方示例快速体验，或直接输入网络问题</p>
      </div>

      <ul
        class="grid grid-cols-1 sm:grid-cols-2 gap-3"
        aria-label="示例提示词"
      >
        <li v-for="(item, i) in prompts" :key="i">
          <button
            type="button"
            class="prompt-card group w-full text-left p-3 rounded-lg border border-border/60 bg-card/50 hover:bg-card/80 hover:border-primary/40 transition-colors duration-[var(--dur-fast)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60"
            @click="onSelect(item.prompt)"
          >
            <div class="flex items-start gap-2.5">
              <span
                class="text-lg leading-none mt-0.5 opacity-80 group-hover:opacity-100 transition-opacity"
                aria-hidden="true"
              >{{ item.icon }}</span>
              <div class="min-w-0 flex-1">
                <div class="text-sm font-medium text-foreground/90 truncate">{{ item.title }}</div>
                <div class="text-xs text-muted-foreground mt-1 line-clamp-2">{{ item.prompt }}</div>
              </div>
            </div>
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
  // 因此 4 条默认 prompt 内联在此（plan P4 第 225-231 行规定）
  samplePrompts: () => [
    { title: 'OSPF 协议原理', icon: '🛰️', prompt: '解释 OSPF 协议的工作原理，重点说明 LSA 类型与 SPF 计算流程。' },
    { title: '排查端口环路', icon: '🔁', prompt: '交换机端口频繁 flap、CPU 飙高，怀疑环路，给我一套从 STP 到 storm-control 的排查方法。' },
    { title: 'Cisco vs 华为 命令对照', icon: '📒', prompt: '给我一份常用 Cisco 与华为命令对照表，覆盖 show interface、配置 trunk、查看 MAC 地址表等场景。' },
    { title: 'BGP neighbor down 根因', icon: '🌐', prompt: '如何快速定位 BGP neighbor down 的根因？请按 TCP 层 / OPEN 报文 / TTL / 时钟偏差 分层给出排查清单。' }
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
.prompt-card:active {
  transform: scale(0.985);
}

@media (prefers-reduced-motion: reduce) {
  .prompt-card {
    transition: none !important;
  }
}
</style>
