import type { AIAssistantState, ChatMessage, ApiError } from '../types'
import { generateId, isApiError } from '../../../utils/helpers'

export const createUtilActions = (state: AIAssistantState) => ({
  formatMessagesForAPI(messages: ChatMessage[]) {
    if (!messages || !Array.isArray(messages)) return []

    return messages.map(msg => {
      const role = msg.role === 'user' ? 'user' : 'assistant'
      return {
        role,
        content: msg.content
      }
    })
  },

  addUserMessage(content: string): ChatMessage {
    const userMessage: ChatMessage = {
      id: generateId(),
      role: 'user',
      content,
      timestamp: Date.now()
    }
    state.chatMessages.push(userMessage)
    return userMessage
  },

  addAssistantMessage(content: string) {
    const assistantMessage: ChatMessage = {
      id: generateId(),
      role: 'assistant',
      content,
      timestamp: Date.now()
    }
    state.chatMessages.push(assistantMessage)
  },

  addMessage(message: ChatMessage) {
    state.chatMessages.push(message)
  },

  toggleStreamingMode() {
    state.streamingEnabled = !state.streamingEnabled
  },

  setSelectedModel(modelValue: string) {
    state.selectedModel = modelValue
  },

  handleMessageError(error: ApiError | Error, _content: string): void {
    console.error('消息发送错误:', error)

    let errorMessage = '发生错误: '

    if (isApiError(error)) {
      const statusCode = error.response!.status

      if (statusCode === 422) {
        errorMessage += '请求参数验证失败'
        const responseData = error.response!.data as { detail?: string | Array<{ msg: string }> }
        if (responseData?.detail) {
          const details = Array.isArray(responseData.detail)
            ? responseData.detail[0]?.msg
            : responseData.detail
          if (details) {
            errorMessage += `: ${details}`
          }
        }
      } else if (statusCode === 500) {
        errorMessage += '服务器内部错误'
        const responseData = error.response!.data as { detail?: string }
        if (responseData?.detail) {
          errorMessage += `: ${responseData.detail}`
        }
      } else if (statusCode === 400) {
        errorMessage += '无效请求'
        const responseData = error.response!.data as { detail?: string }
        if (responseData?.detail) {
          errorMessage += `: ${responseData.detail}`
        }
      } else {
        errorMessage += `服务器返回${statusCode}错误`
      }
    } else {
      errorMessage += error.message || '无法连接到AI服务'
    }

    if (errorMessage.includes('Request failed with status code 500')) {
      errorMessage = '发生错误: 服务器内部错误，请稍后再试'
    }

    state.chatMessages.push({
      id: generateId(),
      role: 'assistant',
      content: errorMessage,
      timestamp: Date.now()
    })

    // 重置所有状态
    state.isLoading = false
    state.isAIResponding = false
    state.isStreamingContent = false
  },

  updateLastActivity(): void {
    // 更新最后活动时间
    console.log('更新最后活动时间:', new Date().toISOString())
  },

  validateMessage(content: string): boolean {
    // 验证消息内容
    if (!content || typeof content !== 'string') {
      return false
    }
    return content.trim().length > 0 && content.trim().length <= 4000
  }
})