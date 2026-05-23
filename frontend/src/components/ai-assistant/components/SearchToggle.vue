<template>
  <div class="flex items-center gap-2">
    <search-icon class="text-foreground/60" :size="14" aria-hidden="true" />
    <span :id="labelId" class="text-sm text-foreground/70">联网搜索</span>
    <button
      class="relative h-6 w-11 rounded-full transition-colors focus-visible:outline-none"
      :class="enabled ? 'bg-primary shadow-glow-sm' : 'bg-muted/70'"
      type="button"
      role="switch"
      :aria-checked="enabled"
      :aria-labelledby="labelId"
      @click="$emit('toggle')"
    >
      <span
        class="absolute left-0.5 top-0.5 flex h-5 w-5 items-center justify-center rounded-full bg-white shadow-sm transition-transform duration-200"
        :class="enabled ? 'translate-x-5' : 'translate-x-0'"
      >
        <span
          class="h-2.5 w-2.5 rounded-full"
          :class="enabled ? 'bg-primary' : 'bg-muted-foreground'"
        ></span>
      </span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { SearchIcon } from '@/components/common/icons';

defineProps<{
  enabled: boolean
}>();

defineEmits<{
  toggle: []
}>();

// 静态 ID：组件每实例一次即可；当前页面布局只有一份 SearchToggle，不会冲突
const labelId = 'search-toggle-label';
</script>
