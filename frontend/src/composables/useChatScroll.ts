import { ref, watch, nextTick } from 'vue';

interface UseChatScrollOptions {
  /** 返回当前消息总数的 getter，用于在新消息到达时滚动 */
  messageCount: () => number
  /** 返回 "正在输入" 状态的 getter，用于在打字态出现/消失时滚动 */
  isTyping: () => boolean
  /** 返回 "正在接收流式内容" 状态的 getter，用于流式时持续粘底 */
  isStreamingContent: () => boolean
}

/**
 * 聊天滚动容器 composable。
 *
 * 把返回值的 `containerRef` 绑到滚动容器，scroller 会在以下情况自动粘底：
 * - 消息数变化
 * - isTyping 切换
 * - isStreamingContent 切换
 *
 * 通过返回的 `scrollToBottom` 也可在外部主动触发（例如发送后立即滚动）。
 */
export function useChatScroll(options: UseChatScrollOptions) {
  const containerRef = ref<HTMLElement | null>(null);

  const scrollToBottom = async (): Promise<void> => {
    await nextTick();
    if (containerRef.value) {
      containerRef.value.scrollTop = containerRef.value.scrollHeight;
    }
  };

  watch(options.messageCount, scrollToBottom);
  watch(options.isTyping, scrollToBottom);
  watch(options.isStreamingContent, scrollToBottom);

  return { containerRef, scrollToBottom };
}
