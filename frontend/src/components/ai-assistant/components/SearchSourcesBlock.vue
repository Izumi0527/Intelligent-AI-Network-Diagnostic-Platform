<template>
  <section
    class="search-sources"
    aria-label="联网搜索来源"
  >
    <div
      v-if="searchFailed && !hasSources"
      role="status"
      class="search-warning"
    >
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
        <line x1="12" y1="9" x2="12" y2="13"/>
        <line x1="12" y1="17" x2="12.01" y2="17"/>
      </svg>
      <span>联网搜索失败或未取到结果，本次回答未引用网络</span>
    </div>
    <ol
      v-else
      class="search-list"
    >
      <li
        v-for="(source, idx) in sources"
        :key="`${source.url}-${idx}`"
        class="search-card"
      >
        <a
          :href="source.url"
          target="_blank"
          rel="noopener noreferrer"
          class="search-card__link"
        >
          <img
            class="search-card__favicon"
            :src="faviconUrl(source.url)"
            alt=""
            loading="lazy"
            referrerpolicy="no-referrer"
            @error="onFaviconError"
          />
          <div class="search-card__body">
            <div class="search-card__title-row">
              <span class="search-card__index" aria-hidden="true">{{ idx + 1 }}</span>
              <span class="search-card__title">{{ source.title }}</span>
            </div>
            <div class="search-card__url">{{ displayHost(source.url) }}</div>
            <p
              v-if="source.description !== undefined && source.description !== ''"
              class="search-card__desc"
            >{{ source.description }}</p>
          </div>
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

const displayHost = (rawUrl: string): string => {
  try {
    const url = new URL(rawUrl);
    return url.host;
  } catch {
    return rawUrl;
  }
};

const faviconUrl = (rawUrl: string): string => {
  try {
    const url = new URL(rawUrl);
    return `https://www.google.com/s2/favicons?domain=${url.host}&sz=32`;
  } catch {
    return '';
  }
};

const onFaviconError = (event: Event): void => {
  const img = event.target as HTMLImageElement;
  img.style.visibility = 'hidden';
};
</script>

<style scoped>
.search-sources {
  margin-top: 8px;
  margin-left: 28px;
}

.search-warning {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border: 1px solid color-mix(in oklch, var(--warning) 45%, transparent);
  border-radius: var(--radius);
  background-color: color-mix(in oklch, var(--warning) 10%, transparent);
  color: var(--warning);
  font-size: 11px;
}

.search-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.search-card {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--background);
  transition:
    border-color var(--dur-enter) var(--ease-standard),
    background-color var(--dur-enter) var(--ease-standard);
}

.search-card:hover {
  border-color: color-mix(in oklch, var(--primary) 45%, transparent);
  background-color: color-mix(in oklch, var(--primary) 4%, transparent);
}

.search-card__link {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 8px 10px;
  text-decoration: none;
  color: inherit;
  border-radius: var(--radius);
}

.search-card__link:focus-visible {
  outline: 2px solid color-mix(in oklch, var(--primary) 55%, transparent);
  outline-offset: -2px;
}

.search-card__favicon {
  width: 16px;
  height: 16px;
  border-radius: 3px;
  flex-shrink: 0;
  margin-top: 2px;
  background-color: var(--muted);
}

.search-card__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.search-card__title-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
}

.search-card__index {
  flex-shrink: 0;
  font-family: var(--app-font-mono);
  font-size: 10px;
  color: var(--muted-foreground);
  font-weight: 500;
  min-width: 14px;
  text-align: right;
}

.search-card__title {
  font-size: 12px;
  font-weight: 500;
  color: var(--foreground);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.search-card__url {
  font-family: var(--app-font-mono);
  font-size: 10.5px;
  color: var(--muted-foreground);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.search-card__desc {
  font-size: 11px;
  color: color-mix(in oklch, var(--foreground) 70%, transparent);
  line-height: 1.45;
  margin: 2px 0 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

@media (max-width: 640px) {
  .search-sources {
    margin-left: 24px;
  }
  .search-card__link {
    padding: 6px 8px;
    gap: 8px;
  }
  .search-card__favicon {
    width: 14px;
    height: 14px;
    margin-top: 1px;
  }
  .search-card__title {
    font-size: 11.5px;
  }
  .search-card__desc {
    font-size: 10.5px;
    -webkit-line-clamp: 1;
  }
}
</style>
