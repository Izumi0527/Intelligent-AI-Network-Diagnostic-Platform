<template>
  <Transition name="fade-up">
    <button
      v-if="visible"
      type="button"
      class="scroll-to-bottom absolute left-1/2 -translate-x-1/2 bottom-4 z-10 flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-border/60 bg-card/95 backdrop-blur-sm text-xs font-medium text-foreground/80 shadow-md hover:shadow-lg hover:bg-card hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60 transition-colors"
      :aria-label="ariaLabel"
      :title="ariaLabel"
      @click="onClick"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
        focusable="false"
      >
        <path d="M12 5v14" />
        <path d="m19 12-7 7-7-7" />
      </svg>
      <span>回到最新</span>
      <span
        v-if="unreadCount !== undefined && unreadCount > 0"
        class="ml-0.5 inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-primary text-primary-foreground text-[10px] font-semibold tabular-nums"
        :aria-label="`${unreadCount} 条新消息`"
      >{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
    </button>
  </Transition>
</template>

<script setup lang="ts">
import { computed } from 'vue';

interface Props {
  visible: boolean
  unreadCount?: number
}

const props = withDefaults(defineProps<Props>(), {
  unreadCount: 0
});

const emit = defineEmits<{
  scroll: []
}>();

const ariaLabel = computed<string>(() => {
  if (props.unreadCount !== undefined && props.unreadCount > 0) {
    return `回到最新（${props.unreadCount} 条新消息）`;
  }
  return '回到最新消息';
});

const onClick = (): void => {
  emit('scroll');
};
</script>

<style scoped>
.fade-up-enter-active,
.fade-up-leave-active {
  transition: opacity var(--dur-fast) var(--ease-out), transform var(--dur-fast) var(--ease-out);
}

.fade-up-enter-from,
.fade-up-leave-to {
  opacity: 0;
  transform: translate(-50%, 8px);
}

@media (prefers-reduced-motion: reduce) {
  .fade-up-enter-active,
  .fade-up-leave-active {
    transition: none !important;
  }
}
</style>
