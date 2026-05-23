import { aiService } from '@/utils/aiService';
import type { AIAssistantState, ChatMessage, StoreActions, ApiError } from '@/types/chat';
import type { ParsedStreamEvent } from '@/types/api';
import { isParsedStreamEvent } from '@/types/api';
import { generateId } from '../../../utils/helpers';
import { logger } from '../../../utils/logger';
import { nextTick } from 'vue';

interface MessagingActions {
  sendMessage(content: string): Promise<void>;
  sendMessageStream(content: string): Promise<void>;
  stopGeneration(): void;
  retryLastMessage(): Promise<void>;
  copyMessage(id: string): void;
  _handleStreamResponse(
    stream: ReadableStream<Uint8Array>,
    assistantMessage: ChatMessage,
    sessionId: string
  ): Promise<void>;
  _addContentCharByChar(assistantMessage: ChatMessage, chunk: string): Promise<void>;
  _handleStreamError(assistantMessage: ChatMessage, errorMsg: string): void;
  sendMessageRegular(content: string): Promise<void>;
}

export const createMessagingActions = (
  state: AIAssistantState,
  utilActions: StoreActions['utilActions'],
  storageActions: StoreActions['storageActions']
): MessagingActions => {
  const actions: MessagingActions = {
    async sendMessage(content: string): Promise<void> {
      if (!content.trim() || !state.isModelConnected || state.isAIResponding) {
        logger.debug('[消息发送] 拒绝发送消息，原因:', {
          noContent: !content.trim(),
          notConnected: !state.isModelConnected,
          isResponding: state.isAIResponding
        });
        return;
      }

      logger.debug('[消息发送] 开始发送消息，流式模式:', state.streamingEnabled);

      state.chatMessages.push({
        id: generateId(),
        role: 'user',
        content,
        timestamp: Date.now(),
        status: 'done'
      });

      storageActions.saveToStorage({
        id: state.conversationId,
        title: content.substring(0, 50) + '...',
        messages: state.chatMessages,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        model: state.selectedModel,
        settings: {
          temperature: 0.7,
          maxTokens: 1000,
          streamMode: state.streamingEnabled,
          model: state.selectedModel
        }
      });

      // 为本次会话创建 AbortController；同时保留本地引用，避免 ESLint 路径分析
      // 与 await 期间 state.abortController 被异步置空时的类型推断冲突。
      const abortController = new AbortController();
      state.abortController = abortController;

      // 设置为思考状态
      state.isAIResponding = true;
      state.isStreamingContent = false;
      logger.debug('[消息发送] 设置思考状态 - isAIResponding: true, isStreamingContent: false');

      try {
        if (state.streamingEnabled) {
          logger.debug('[消息发送] 调用流式发送方法');
          await actions.sendMessageStream(content);
        } else {
          logger.debug('[消息发送] 调用非流式发送方法');
          await actions.sendMessageRegular(content);
        }
      } catch (error: unknown) {
        // 用户主动中断不视为错误：用本地 abortController 引用，避开异步置空的歧义
        if (abortController.signal.aborted) {
          logger.debug('[消息发送] 用户已主动停止生成');
        } else {
          logger.error('消息发送错误:', error);
          utilActions.handleMessageError(error as ApiError | Error, content);
        }
      } finally {
        state.isAIResponding = false;
        state.isStreamingContent = false;
        state.abortController = null;
        logger.debug('[消息发送] 重置所有状态 - isAIResponding: false, isStreamingContent: false');
        storageActions.saveToStorage({
          id: state.conversationId,
          title: content.substring(0, 50) + '...',
          messages: state.chatMessages,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          model: state.selectedModel,
          settings: {
            temperature: 0.7,
            maxTokens: 1000,
            streamMode: state.streamingEnabled,
            model: state.selectedModel
          }
        });
      }
    },

    async sendMessageStream(content: string): Promise<void> {
      const sessionId = Date.now().toString();
      logger.debug(`开始流式会话 ${sessionId}`);

      try {
        const assistantMessage: ChatMessage = {
          id: generateId(),
          role: 'assistant',
          content: '',
          timestamp: Date.now(),
          status: 'streaming'
        };

        state.chatMessages.push(assistantMessage);

        const messageHistory = state.chatMessages
          .filter(msg => msg !== assistantMessage)
          .map(msg => ({
            role: msg.role === 'system' ? 'user' : msg.role,
            content: msg.content
          }));

        logger.debug(`发送流式请求，消息数: ${messageHistory.length}，会话ID: ${sessionId}`);

        try {
          // 把 AbortController 的 signal 传给 aiService，使 axios 请求阶段可中断。
          // 仅在 signal 存在时构造 options，避免 exactOptionalPropertyTypes 报错。
          const signal = state.abortController?.signal;
          const response = await aiService.sendMessageStream(
            {
              model: state.selectedModel,
              messages: messageHistory,
              stream: true,
              enable_search: state.searchEnabled
            },
            signal !== undefined ? { signal } : {}
          );

          logger.debug('[流式诊断] 响应对象:', response);
          logger.debug('[流式诊断] response.data 类型:', typeof response.data);
          logger.debug('[流式诊断] 是否为 ReadableStream:', response.data instanceof ReadableStream);
          logger.debug('[流式诊断] 构造函数名称:', response.data.constructor.name);

          // StreamSendResult 类型已保证 response.data 是 ReadableStream<Uint8Array>，
          // 兜底防线只需保留 instanceof 检查（处理上游契约破坏的极端情况）。
          if (response.data instanceof ReadableStream) {
            // 立即切换到流式接收状态 - 添加详细日志
            logger.debug(`[流式状态] 开始接收流式内容，会话ID: ${sessionId}`);
            logger.debug(`[流式状态] 切换前状态 - isAIResponding: ${state.isAIResponding}, isStreamingContent: ${state.isStreamingContent}`);

            // 更新状态：停止思考，开始流式接收
            state.isAIResponding = false;  // 不再显示"思考中"
            state.isStreamingContent = true;  // 开始流式内容接收

            logger.debug(`[流式状态] 切换后状态 - isAIResponding: ${state.isAIResponding}, isStreamingContent: ${state.isStreamingContent}`);

            // 强制触发响应式更新
            await nextTick();
            logger.debug(`[流式状态] nextTick后状态 - isAIResponding: ${state.isAIResponding}, isStreamingContent: ${state.isStreamingContent}`);

            await actions._handleStreamResponse(response.data, assistantMessage, sessionId);
          } else {
            logger.error(`[流式错误] 响应不是ReadableStream，会话ID: ${sessionId}`);
            logger.error(`[流式错误] 实际类型: ${typeof response.data}`);
            logger.error('[流式错误] 响应数据:', response.data);
            actions._handleStreamError(assistantMessage, '服务器返回的不是流式数据');
          }

          storageActions.saveToStorage({
            id: state.conversationId,
            title: content.substring(0, 50) + '...',
            messages: state.chatMessages,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            model: state.selectedModel,
            settings: {
              temperature: 0.7,
              maxTokens: 1000,
              streamMode: state.streamingEnabled,
              model: state.selectedModel
            }
          });
          logger.debug(`流式响应处理完成，会话ID: ${sessionId}`);
        } catch (error) {
          const errMsg = error instanceof Error ? error.message : String(error);
          logger.error(`流式响应错误: ${errMsg}, 会话ID: ${sessionId}`);
          actions._handleStreamError(assistantMessage, error instanceof Error ? error.message : '请求失败');
        }
      } catch (error) {
        state.isAIResponding = false;
        state.isStreamingContent = false;
        const errMsg = error instanceof Error ? error.message : String(error);
        logger.error(`流式会话整体错误: ${errMsg}`);
      }
    },

    async _handleStreamResponse(stream: ReadableStream<Uint8Array>, assistantMessage: ChatMessage, sessionId: string): Promise<void> {
      const reader = stream.getReader();
      const decoder = new TextDecoder('utf-8');
      const signal = state.abortController?.signal;

      logger.debug(`[流式处理] 开始读取流，会话ID: ${sessionId}`);

      let contentReceived = false;
      let isFirstChunk = true;
      let thinkingContent = '';
      // buffer 暂存跨 chunk 的不完整 JSON 行——aiService.ts 发的每条事件以 \n 结尾，
      // 但 TextDecoder.decode 可能在任意字节切片，必须自己重组行边界。
      let buffer = '';

      // 强制触发响应式更新（chatMessages 数组引用替换）
      const refreshMessage = (): void => {
        const idx = state.chatMessages.findIndex(msg => msg.id === assistantMessage.id);
        if (idx !== -1) {
          state.chatMessages[idx] = { ...assistantMessage };
          state.chatMessages = [...state.chatMessages];
        }
      };

      const dispatchEvent = async (event: ParsedStreamEvent): Promise<void> => {
        if (event.type === 'error') {
          logger.error(`[流式处理] 收到错误事件: ${event.text}`);
          assistantMessage.content += `\n${event.text}`;
          contentReceived = true;
          refreshMessage();
          return;
        }
        if (event.type === 'thinking') {
          thinkingContent += event.text;
          state.isThinking = true;
          state.currentThinkingContent = thinkingContent;
          // 重建整个 thinking 对象（而非 mutate .content）：refreshMessage 做 { ...assistantMessage }
          // 浅拷贝后 chatMessages[idx].thinking 仍指向同一子对象，Vue lazy proxify 嵌套对象时
          // 通过原对象 mutate 属性绕过 proxy set trap，触发不了渲染——必须替换整个 thinking 引用。
          assistantMessage.thinking = {
            content: thinkingContent,
            isComplete: false,
            timestamp: assistantMessage.thinking?.timestamp ?? Date.now()
          };
          refreshMessage();
          return;
        }
        // 类型已 narrow 到 'content'：error/thinking 上面均 return
        await actions._addContentCharByChar(assistantMessage, event.text);
        contentReceived = true;
      };

      try {
        for (;;) {
          // 用户主动中断：立即取消 reader 并退出循环
          if (signal?.aborted === true) {
            logger.debug(`[流式处理] 检测到 abort，停止读取，会话ID: ${sessionId}`);
            await reader.cancel();
            assistantMessage.aborted = true;
            assistantMessage.status = 'aborted';
            if (assistantMessage.content.trim() === '') {
              assistantMessage.content = '（已停止生成）';
            } else {
              assistantMessage.content += '\n\n（已停止生成）';
            }
            refreshMessage();
            break;
          }

          const { value, done } = await reader.read();

          if (done) {
            logger.debug(`[流式处理] 流读取完成，会话ID: ${sessionId}`);
            // 末尾 buffer 若残留完整 JSON 行也要解析
            const tail = buffer.trim();
            if (tail !== '' && !tail.includes('[DONE]')) {
              try {
                const parsed: unknown = JSON.parse(tail);
                if (isParsedStreamEvent(parsed)) {
                  await dispatchEvent(parsed);
                }
              } catch (e) {
                logger.warn(`[流式处理] 末尾残行解析失败: ${tail.substring(0, 80)}`, e);
              }
            }
            buffer = '';
            break;
          }

          // ReadableStream<Uint8Array> 的契约：done=false 时 value 一定是 Uint8Array
          const chunk = decoder.decode(value, { stream: true });

          if (chunk === '') { continue; }

          if (isFirstChunk) {
            logger.debug(`[流式处理] 接收到首个数据块 (${chunk.length}字符)，会话ID: ${sessionId}`);
            isFirstChunk = false;
          }

          // 按 \n 切行；最后一段（可能不完整）留到下次 read 拼回
          buffer += chunk;
          const lines = buffer.split('\n');
          buffer = lines.pop() ?? '';

          for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed === '' || trimmed.includes('[DONE]')) { continue; }

            try {
              const parsed: unknown = JSON.parse(trimmed);
              if (isParsedStreamEvent(parsed)) {
                await dispatchEvent(parsed);
              } else {
                logger.warn(`[流式处理] 非 ParsedStreamEvent 形态，丢弃: ${trimmed.substring(0, 80)}`);
              }
            } catch (e) {
              logger.warn(`[流式处理] JSON 解析失败: ${trimmed.substring(0, 80)}`, e);
            }
          }
        }

        // flush decoder 最终状态（可能含跨字节字符的尾部）
        const finalChunk = decoder.decode();
        if (finalChunk.trim() !== '' && !finalChunk.includes('[DONE]')) {
          buffer += finalChunk;
          const tail = buffer.trim();
          if (tail !== '') {
            try {
              const parsed: unknown = JSON.parse(tail);
              if (isParsedStreamEvent(parsed)) {
                await dispatchEvent(parsed);
              }
            } catch (e) {
              logger.warn(`[流式处理] finalChunk 解析失败: ${tail.substring(0, 80)}`, e);
            }
          }
        }

        // 完成思考内容（重建对象，避免嵌套 mutate 触发不了响应式——见上方 dispatchEvent 注释）
        if (thinkingContent !== '' && assistantMessage.thinking !== undefined) {
          assistantMessage.thinking = {
            content: assistantMessage.thinking.content,
            isComplete: true,
            timestamp: assistantMessage.thinking.timestamp
          };
          refreshMessage();
          state.isThinking = false;
          state.currentThinkingContent = '';
        }

        // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition -- contentReceived 在 dispatchEvent 闭包内被改，ESLint 无法追踪
        if (!contentReceived || assistantMessage.content.trim() === '') {
          logger.warn(`[流式处理] 未接收到有效内容，会话ID: ${sessionId}`);
          actions._handleStreamError(assistantMessage, '未接收到有效内容');
        } else {
          logger.debug(`[流式处理] 成功接收内容，总长度: ${assistantMessage.content.length}字符，会话ID: ${sessionId}`);
          // 成功完成：标记 status = 'done' 让 UI 据此停止流式态显示
          assistantMessage.status = 'done';
          refreshMessage();
        }

        // 流式内容接收完成，重置状态
        logger.debug(`[流式状态] 流式接收完成，重置状态，会话ID: ${sessionId}`);
        state.isAIResponding = false;
        state.isStreamingContent = false;
        state.isThinking = false;
        state.currentThinkingContent = '';

      } catch (e) {
        const errMsg = e instanceof Error ? e.message : String(e);
        logger.error(`[流式处理] 流读取错误: ${errMsg}, 会话ID: ${sessionId}`);
        actions._handleStreamError(assistantMessage, `读取流数据失败 - ${errMsg}`);
        state.isAIResponding = false;
        state.isStreamingContent = false;
        state.isThinking = false;
        state.currentThinkingContent = '';
      }
    },

    // 逐字符添加内容的方法
    async _addContentCharByChar(assistantMessage: ChatMessage, chunk: string): Promise<void> {
      const chars = chunk.split('');
      const signal = state.abortController?.signal;

      for (let i = 0; i < chars.length; i++) {
        // 用户中断时立即停止打字机循环，避免继续填充已废弃的消息
        if (signal?.aborted === true) {
          logger.debug('[打字机] 检测到 abort，停止逐字添加');
          return;
        }
        assistantMessage.content += chars[i];

        // 每添加一个字符，更新一次UI
        const messageIndex = state.chatMessages.findIndex(msg => msg.id === assistantMessage.id);
        if (messageIndex !== -1) {
          state.chatMessages[messageIndex] = { ...assistantMessage };
          state.chatMessages = [...state.chatMessages];
        }

        // 添加小延迟模拟打字机效果
        await new Promise(resolve => setTimeout(resolve, 20));
      }
    },

    _handleStreamError(assistantMessage: ChatMessage, errorMsg: string): void {
      // 不再 splice + push 新错误消息；直接给原 assistant 消息打 error 标记
      // 以便 UI 在该消息位置渲染 MessageActions 的 retry 按钮（P2 接入）
      const idx = state.chatMessages.findIndex(msg => msg.id === assistantMessage.id);
      if (idx !== -1) {
        const original = state.chatMessages[idx];
        if (original !== undefined) {
          const prefix = original.content.trim() !== '' ? `${original.content}\n\n` : '';
          state.chatMessages[idx] = {
            ...original,
            content: `${prefix}⚠️ ${errorMsg}`,
            error: { type: 'server', message: errorMsg, retryable: true },
            status: 'error'
          };
          state.chatMessages = [...state.chatMessages];
        }
      }

      // 重置所有状态
      state.isAIResponding = false;
      state.isStreamingContent = false;
      state.isThinking = false;
      state.currentThinkingContent = '';
      state.abortController = null;
    },

    async sendMessageRegular(content: string): Promise<void> {
      try {
        state.isLoading = true;
        state.error = null;

        const messageHistory = state.chatMessages.map(msg => ({
          role: msg.role === 'system' ? 'user' : msg.role,
          content: msg.content
        }));
        let messagesToSend = [...messageHistory];

        if (messagesToSend.length === 0) {
          logger.warn('消息历史为空，将只发送当前用户消息');
          messagesToSend = [{
            role: 'user',
            content: content
          }];
        }

        logger.debug(`发送非流式请求，消息数: ${messagesToSend.length}`);

        const response = await aiService.sendMessageWithRetry({
          model: state.selectedModel,
          messages: messagesToSend,
          enable_search: state.searchEnabled
        }, 3);

        const assistantContent = response.data.content ?? response.data.message?.content;
        if (assistantContent !== undefined && assistantContent !== '') {
          state.chatMessages.push({
            id: generateId(),
            role: 'assistant',
            content: assistantContent,
            timestamp: Date.now(),
            status: 'done'
          });
        } else {
          logger.error('响应格式异常，无法获取内容:', response.data);
          throw new Error('响应格式异常：缺少内容');
        }

        state.isLoading = false;
      } catch (error) {
        utilActions.handleMessageError(error as ApiError | Error, content);
      }
    },

    // 用户主动停止生成：abort 进行中的 axios 请求，标记最后一条助手消息为 aborted。
    // 流式 reader 与打字机循环会在下一次 check 时看到 signal.aborted 并跳出。
    stopGeneration(): void {
      const controller = state.abortController;
      if (controller !== null && !controller.signal.aborted) {
        logger.debug('[停止生成] 触发 AbortController.abort()');
        controller.abort();
      }

      // 立即给最后一条 assistant 消息打 aborted 标记（在 _handleStreamResponse 的 abort 分支里
      // 也会做相同处理，但若 axios 还未返回时 abort，那里不会执行，所以此处兜底）
      const lastIdx = state.chatMessages.length - 1;
      const lastMsg = lastIdx >= 0 ? state.chatMessages[lastIdx] : undefined;
      if (lastMsg !== undefined && lastMsg.role === 'assistant' && lastMsg.status !== 'aborted') {
        const prefix = lastMsg.content.trim() !== '' ? `${lastMsg.content}\n\n` : '';
        state.chatMessages[lastIdx] = {
          ...lastMsg,
          content: `${prefix}（已停止生成）`,
          aborted: true,
          status: 'aborted'
        };
        state.chatMessages = [...state.chatMessages];
      }

      state.isAIResponding = false;
      state.isStreamingContent = false;
      state.isThinking = false;
      state.currentThinkingContent = '';
      // abortController 在 sendMessage 的 finally 中清理；此处不立即置 null 避免竞态
    },

    // 复制消息：UI 层（MessageActions）已通过 navigator.clipboard 完成实际复制并显示反馈；
    // store 侧只记录可观测性事件，为未来埋点 / 多选复制 / 复制审计预留扩展点。
    copyMessage(id: string): void {
      const msg = state.chatMessages.find(m => m.id === id);
      logger.debug('[复制消息] id:', id, 'role:', msg?.role, 'len:', msg?.content.length ?? 0);
    },

    // 重试最后一次失败/中断的发送：定位末尾最近的 user 消息内容，删除该 user 及其后所有消息，
    // 然后重新走 sendMessage 流程（自动重新 push user + 发起请求）。
    async retryLastMessage(): Promise<void> {
      if (state.isAIResponding || state.isStreamingContent) {
        logger.debug('[重试] AI 正在响应中，跳过重试');
        return;
      }

      let userIdx = -1;
      for (let i = state.chatMessages.length - 1; i >= 0; i--) {
        if (state.chatMessages[i]?.role === 'user') {
          userIdx = i;
          break;
        }
      }
      if (userIdx < 0) {
        logger.debug('[重试] 没有可重试的 user 消息');
        return;
      }
      const userContent = state.chatMessages[userIdx]?.content ?? '';
      if (userContent.trim() === '') {
        logger.warn('[重试] user 消息内容为空，跳过重试');
        return;
      }
      // 删除该 user 及其后所有消息（含失败/中断的 assistant）
      state.chatMessages.splice(userIdx);
      state.chatMessages = [...state.chatMessages];
      logger.debug(`[重试] 重新发送 user 消息: "${userContent.substring(0, 30)}..."`);
      await actions.sendMessage(userContent);
    }
  };

  return actions;
};