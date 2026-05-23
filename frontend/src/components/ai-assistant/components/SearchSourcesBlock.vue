<template>
  <section
    class="search-sources mt-2 ml-7"
    aria-label="联网搜索来源"
  >
    <div
      v-if="searchFailed && !hasSources"
      role="status"
      class="search-warning rounded-md border border-amber-300/70 dark:border-amber-700/60 px-3 py-2 text-xs"
    >
      <span aria-hidden="true">⚠️</span>
      联网搜索失败或未取到结果，本次回答未引用网络。
    </div>
    <ol
      v-else
      class="space-y-2"
    >
      <li
        v-for="(source, idx) in sources"
        :key="`${source.url}-${idx}`"
        class="search-source-card rounded-lg border border-border/60 px-3 py-2 transition-colors hover:border-primary/60"
      >
        <a
          :href="source.url"
          target="_blank"
          rel="noopener noreferrer"
          class="block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[oklch(var(--primary)/0.5)] rounded"
        >
          <div class="flex items-baseline gap-2">
            <span class="search-source-index text-xs font-medium" aria-hidden="true">[{{ idx + 1 }}]</span>
            <h4 class="search-source-title text-sm font-medium truncate">{{ source.title }}</h4>
          </div>
          <div class="search-source-url text-[11px] truncate">{{ displayHost(source.url) }}</div>
          <p
            v-if="source.description !== undefined && source.description !== ''"
            class="search-source-desc text-xs leading-snug mt-1 line-clamp-2"
          >{{ source.description }}</p>
        </a>
      </li>
    </ol>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { SearchSource } from '@/types/chat';

interface Props {
  sources?: SearchSource[]
  searchFailed?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  sources: () => [],
  searchFailed: false
});

const hasSources = computed<boolean>(() => props.sources.length > 0);

// URL → 仅展示 host，避免长 URL 撑爆卡片
const displayHost = (rawUrl: string): string => {
  try {
    const url = new URL(rawUrl);
    return url.host + (url.pathname !== '/' ? url.pathname : '');
  } catch {
    return rawUrl;
  }
};
</script>

<style scoped>
.search-warning {
  background: color-mix(in oklch, oklch(0.7 0.15 80 / 0.12), oklch(var(--background)) 85%);
  color: oklch(0.45 0.12 70);
}
:root.dark .search-warning {
  color: oklch(0.82 0.1 75);
}
.search-source-card {
  background: color-mix(in oklch, oklch(var(--primary) / 0.04), oklch(var(--background)) 92%);
}
:root.dark .search-source-card {
  background: color-mix(in oklch, oklch(var(--primary) / 0.08), oklch(var(--background)) 80%);
}
.search-source-title {
  color: color-mix(in oklch, oklch(var(--foreground)) 90%, oklch(var(--primary)) 10%);
}
.search-source-index {
  color: oklch(var(--primary));
}
.search-source-url {
  color: color-mix(in oklch, oklch(var(--foreground)) 55%, transparent);
}
.search-source-desc {
  color: color-mix(in oklch, oklch(var(--foreground)) 75%, transparent);
}
</style>
