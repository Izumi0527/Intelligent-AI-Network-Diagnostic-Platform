import { ref, watch, nextTick, onMounted, onBeforeUnmount, type Ref } from 'vue';

interface UseChatScrollOptions {
  /** 返回当前消息总数的 getter，用于在新消息到达时滚动 */
  messageCount: () => number
  /** 返回 "正在输入" 状态的 getter，用于在打字态出现/消失时滚动 */
  isTyping: () => boolean
  /** 返回 "正在接收流式内容" 状态的 getter，用于流式时持续粘底 */
  isStreamingContent: () => boolean
}

interface UseChatScrollReturn {
  containerRef: Ref<HTMLElement | null>
  scrollToBottom: () => Promise<void>
  /** 用户视口是否距列表底部 < 80px；ScrollToBottomButton 据此控制可见性 */
  isAtBottom: Ref<boolean>
}

/** 距底阈值：小于该值视为"已在底部"，不显示 ScrollToBottom 按钮 */
const BOTTOM_THRESHOLD_PX = 80;

/**
 * 聊天滚动容器 composable。
 *
 * 把返回值的 `containerRef` 绑到滚动容器，scroller 会在以下情况自动粘底：
 * - 消息数变化
 * - isTyping 切换
 * - isStreamingContent 切换
 *
 * 通过返回的 `scrollToBottom` 也可在外部主动触发（例如发送后立即滚动）。
 * `isAtBottom` 暴露用户是否在底部，供 ScrollToBottomButton 等组件消费。
 */
export function useChatScroll(options: UseChatScrollOptions): UseChatScrollReturn {
  const containerRef = ref<HTMLElement | null>(null);
  const isAtBottom = ref<boolean>(true);

  const computeIsAtBottom = (): void => {
    const el = containerRef.value;
    if (el === null) { return; }
    const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
    isAtBottom.value = distance < BOTTOM_THRESHOLD_PX;
  };

  const scrollToBottom = async (): Promise<void> => {
    await nextTick();
    if (containerRef.value) {
      containerRef.value.scrollTop = containerRef.value.scrollHeight;
      isAtBottom.value = true;
    }
  };

  const onScroll = (): void => { computeIsAtBottom(); };

  onMounted(() => {
    const el = containerRef.value;
    if (el !== null) {
      el.addEventListener('scroll', onScroll, { passive: true });
      computeIsAtBottom();
    }
  });

  onBeforeUnmount(() => {
    const el = containerRef.value;
    if (el !== null) {
      el.removeEventListener('scroll', onScroll);
    }
  });

  watch(options.messageCount, scrollToBottom);
  watch(options.isTyping, scrollToBottom);
  watch(options.isStreamingContent, scrollToBottom);

  return { containerRef, scrollToBottom, isAtBottom };
}
