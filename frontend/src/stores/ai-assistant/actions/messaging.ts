import { aiService } from '@/utils/aiService'
import type { AIAssistantState, ChatMessage, StoreActions, ApiError } from '../types'
import { generateId } from '../../../utils/helpers'
import { nextTick } from 'vue'

export const createMessagingActions = (
  state: AIAssistantState,
  utilActions: StoreActions['utilActions'],
  storageActions: StoreActions['storageActions']
) => {
  const actions = {
    async sendMessage(content: string) {
      if (!content.trim() || !state.isModelConnected || state.isAIResponding) {
        console.log('[消息发送] 拒绝发送消息，原因:', {
          noContent: !content.trim(),
          notConnected: !state.isModelConnected,
          isResponding: state.isAIResponding
        })
        return
      }

      console.log('[消息发送] 开始发送消息，流式模式:', state.streamingEnabled)

      state.chatMessages.push({
        id: generateId(),
        role: 'user',
        content,
        timestamp: Date.now()
      })

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
      })

      // 设置为思考状态
      state.isAIResponding = true
      state.isStreamingContent = false
      console.log('[消息发送] 设置思考状态 - isAIResponding: true, isStreamingContent: false')

      try {
        if (state.streamingEnabled) {
          console.log('[消息发送] 调用流式发送方法')
          await actions.sendMessageStream(content)
        } else {
          console.log('[消息发送] 调用非流式发送方法')
          await actions.sendMessageRegular(content)
        }
      } catch (error: unknown) {
        console.error('消息发送错误:', error)
        utilActions.handleMessageError(error as ApiError | Error, content)
      } finally {
        state.isAIResponding = false
        state.isStreamingContent = false  // 确保流式状态也被重置
        console.log('[消息发送] 重置所有状态 - isAIResponding: false, isStreamingContent: false')
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
        })
      }
    },

    async sendMessageStream(content: string) {
      const sessionId = Date.now().toString()
      console.log(`开始流式会话 ${sessionId}`)

      try {
        const assistantMessage: ChatMessage = {
          id: generateId(),
          role: 'assistant',
          content: '',
          timestamp: Date.now()
        }

        state.chatMessages.push(assistantMessage)

        const messageHistory = state.chatMessages
          .filter(msg => msg !== assistantMessage)
          .map(msg => ({
            role: msg.role === 'system' ? 'user' : msg.role,
            content: msg.content
          }));

        console.log(`发送流式请求，消息数: ${messageHistory.length}，会话ID: ${sessionId}`)

        try {
          const response = await aiService.sendMessageStream({
            model: state.selectedModel,
            messages: messageHistory,
            stream: true
          })

          console.log(`[流式诊断] 响应对象:`, response)
          console.log(`[流式诊断] response.data 类型:`, typeof response.data)
          console.log(`[流式诊断] 是否为 ReadableStream:`, response.data instanceof ReadableStream)
          console.log(`[流式诊断] 构造函数名称:`, response.data?.constructor?.name)

          if (!response || !response.data) {
            throw new Error('流式响应无效')
          }

          if (response.data instanceof ReadableStream) {
            // 立即切换到流式接收状态 - 添加详细日志
            console.log(`[流式状态] 开始接收流式内容，会话ID: ${sessionId}`)
            console.log(`[流式状态] 切换前状态 - isAIResponding: ${state.isAIResponding}, isStreamingContent: ${state.isStreamingContent}`)

            // 更新状态：停止思考，开始流式接收
            state.isAIResponding = false  // 不再显示"思考中"
            state.isStreamingContent = true  // 开始流式内容接收

            console.log(`[流式状态] 切换后状态 - isAIResponding: ${state.isAIResponding}, isStreamingContent: ${state.isStreamingContent}`)

            // 强制触发响应式更新
            await nextTick()
            console.log(`[流式状态] nextTick后状态 - isAIResponding: ${state.isAIResponding}, isStreamingContent: ${state.isStreamingContent}`)

            await actions._handleStreamResponse(response.data, assistantMessage, sessionId)
          } else {
            console.error(`[流式错误] 响应不是ReadableStream，会话ID: ${sessionId}`)
            console.error(`[流式错误] 实际类型: ${typeof response.data}`)
            const dataType = response.data ? Object.prototype.toString.call(response.data) : 'null'
            console.error(`[流式错误] 构造函数: ${dataType}`)

            console.error(`[流式错误] 响应数据:`, response.data)
            actions._handleStreamError(assistantMessage, '服务器返回的不是流式数据')
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
          })
          console.log(`流式响应处理完成，会话ID: ${sessionId}`)
        } catch (error) {
          console.error(`流式响应错误: ${error}, 会话ID: ${sessionId}`)
          actions._handleStreamError(assistantMessage, (error as Error).message || '请求失败')
        }
      } catch (error) {
        state.isAIResponding = false
        state.isStreamingContent = false
        console.error(`流式会话整体错误: ${error}`)
      }
    },

    async _handleStreamResponse(stream: ReadableStream, assistantMessage: ChatMessage, sessionId: string) {
      const reader = stream.getReader()
      const decoder = new TextDecoder('utf-8')

      console.log(`[流式处理] 开始读取流，会话ID: ${sessionId}`)

      let contentReceived = false
      let isFirstChunk = true
      let thinkingContent = ''

      try {
        while (true) {
          const { value, done } = await reader.read()

          if (done) {
            console.log(`[流式处理] 流读取完成，会话ID: ${sessionId}`)
            break
          }

          if (value) {
            const chunk = decoder.decode(value, { stream: true })

            if (chunk) {
              if (isFirstChunk) {
                console.log(`[流式处理] 接收到首个数据块 (${chunk.length}字符)，会话ID: ${sessionId}`)
                isFirstChunk = false
              }

              if (chunk.includes('[DONE]')) {
                console.log('[流式处理] 收到流结束标记')
                continue
              }

              if (chunk.startsWith('错误:')) {
                console.error(`[流式处理] 收到错误消息: ${chunk}`)
                assistantMessage.content += `\n${chunk}`
                contentReceived = true

                // 强制触发响应式更新
                const messageIndex = state.chatMessages.findIndex(msg => msg.id === assistantMessage.id)
                if (messageIndex !== -1) {
                  state.chatMessages[messageIndex] = { ...assistantMessage }
                  state.chatMessages = [...state.chatMessages]
                }
                continue
              }

              // 处理思考内容
              if (chunk.startsWith('🤔思考: ')) {
                const thinkingText = chunk.substring(6) // 去掉 "🤔思考: " 前缀
                thinkingContent += thinkingText

                // 更新当前思考内容状态
                state.isThinking = true
                state.currentThinkingContent = thinkingContent

                // 更新消息中的思考内容
                if (!assistantMessage.thinking) {
                  assistantMessage.thinking = {
                    content: thinkingContent,
                    isComplete: false,
                    timestamp: Date.now()
                  }
                } else {
                  assistantMessage.thinking.content = thinkingContent
                }

                // 强制触发响应式更新
                const messageIndex = state.chatMessages.findIndex(msg => msg.id === assistantMessage.id)
                if (messageIndex !== -1) {
                  state.chatMessages[messageIndex] = { ...assistantMessage }
                  state.chatMessages = [...state.chatMessages]
                }
                continue
              }

              // 逐字符添加内容来实现打字机效果
              await actions._addContentCharByChar(assistantMessage, chunk)
              contentReceived = true

              if (chunk.length > 50) {
                console.debug(`[流式处理] 接收到较大数据块: ${chunk.length}字符`)
              }
            }
          }
        }

        const finalChunk = decoder.decode()
        if (finalChunk && finalChunk.trim()) {
          console.log(`[流式处理] 处理最终数据块 (${finalChunk.length}字符)，会话ID: ${sessionId}`)

          if (!finalChunk.includes('[DONE]') && !finalChunk.startsWith('错误:') && !finalChunk.startsWith('🤔思考: ')) {
            await actions._addContentCharByChar(assistantMessage, finalChunk)
            contentReceived = true
          }
        }

        // 完成思考内容
        if (thinkingContent && assistantMessage.thinking) {
          assistantMessage.thinking.isComplete = true
          state.isThinking = false
          state.currentThinkingContent = ''
        }

        if (!contentReceived || !assistantMessage.content.trim()) {
          console.warn(`[流式处理] 未接收到有效内容，会话ID: ${sessionId}`)
          actions._handleStreamError(assistantMessage, '未接收到有效内容')
        } else {
          console.log(`[流式处理] 成功接收内容，总长度: ${assistantMessage.content.length}字符，会话ID: ${sessionId}`)
        }

        // 流式内容接收完成，重置状态
        console.log(`[流式状态] 流式接收完成，重置状态，会话ID: ${sessionId}`)
        state.isAIResponding = false
        state.isStreamingContent = false
        state.isThinking = false
        state.currentThinkingContent = ''

      } catch (e) {
        console.error(`[流式处理] 流读取错误: ${e}, 会话ID: ${sessionId}`)
        actions._handleStreamError(assistantMessage, `读取流数据失败 - ${e}`)
        state.isAIResponding = false
        state.isStreamingContent = false
        state.isThinking = false
        state.currentThinkingContent = ''
      }
    },

    // 逐字符添加内容的方法
    async _addContentCharByChar(assistantMessage: ChatMessage, chunk: string) {
      const chars = chunk.split('')

      for (let i = 0; i < chars.length; i++) {
        assistantMessage.content += chars[i]

        // 每添加一个字符，更新一次UI
        const messageIndex = state.chatMessages.findIndex(msg => msg.id === assistantMessage.id)
        if (messageIndex !== -1) {
          state.chatMessages[messageIndex] = { ...assistantMessage }
          state.chatMessages = [...state.chatMessages]
        }

        // 添加小延迟模拟打字机效果
        await new Promise(resolve => setTimeout(resolve, 20))
      }
    },

    _handleStreamError(assistantMessage: ChatMessage, errorMsg: string) {
      const index = state.chatMessages.indexOf(assistantMessage)
      if (index !== -1) {
        state.chatMessages.splice(index, 1)
      }

      state.chatMessages.push({
        id: generateId(),
        role: 'assistant',
        content: `发生错误: ${errorMsg}`,
        timestamp: Date.now()
      })

      // 重置所有状态
      state.isAIResponding = false
      state.isStreamingContent = false
      state.isThinking = false
      state.currentThinkingContent = ''
    },

    async sendMessageRegular(content: string) {
      try {
        state.isLoading = true
        state.error = null

        const messageHistory = state.chatMessages.map(msg => ({
          role: msg.role === 'system' ? 'user' : msg.role,
          content: msg.content
        }))
        let messagesToSend = [...messageHistory]

        if (messagesToSend.length === 0) {
          console.warn('消息历史为空，将只发送当前用户消息')
          messagesToSend = [{
            role: 'user',
            content: content
          }]
        }

        console.log(`发送非流式请求，消息数: ${messagesToSend.length}`)

        const response = await aiService.sendMessageWithRetry({
          model: state.selectedModel,
          messages: messagesToSend
        }, 3)

        const assistantContent = response.data?.content || response.data?.message?.content
        if (assistantContent) {
          state.chatMessages.push({
            id: generateId(),
            role: 'assistant',
            content: assistantContent,
            timestamp: Date.now()
          })
        } else {
          console.error('响应格式异常，无法获取内容:', response.data)
          throw new Error('响应格式异常：缺少内容')
        }

        state.isLoading = false
      } catch (error) {
        utilActions.handleMessageError(error as ApiError | Error, content)
      }
    }
  }

  return actions
}