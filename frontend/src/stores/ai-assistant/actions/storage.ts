import { localStorageUtils } from '@/utils/localStorageUtils'
import type { AIAssistantState, ChatData } from '../types'

export const createStorageActions = (state: AIAssistantState) => ({
  saveToStorage(chatData: ChatData) {
    const storageKey = `chat_history_${state.selectedModel}`
    localStorageUtils.saveChat(storageKey, chatData)
  },

  saveConversationToStorage() {
    const chatData: ChatData = {
      id: state.conversationId,
      title: state.chatMessages.length > 0 ? 
        (state.chatMessages[state.chatMessages.length - 1]?.content?.substring(0, 50) ?? '新对话') + '...' : 
        '新对话',
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
    }
    
    this.saveToStorage(chatData)
  },

  loadFromStorage(id: string): ChatData | null {
    const storageKey = `chat_history_${id}`
    const savedData = localStorageUtils.loadChat(storageKey)
    
    if (savedData) {
      if (Array.isArray(savedData)) {
        // 如果是 ChatMessage[] 格式，转换为 ChatData
        return {
          id,
          title: '加载的对话',
          messages: savedData,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          model: state.selectedModel,
          settings: {
            temperature: 0.7,
            maxTokens: 1000,
            streamMode: state.streamingEnabled,
            model: state.selectedModel
          }
        }
      } else if (savedData.messages && Array.isArray(savedData.messages)) {
        // 如果是 ChatData 格式
        return savedData
      }
    }
    return null
  },

  loadConversationFromStorage() {
    const storageKey = `chat_history_${state.selectedModel}`
    const savedData = localStorageUtils.loadChat(storageKey)

    if (savedData) {
      if (Array.isArray(savedData)) {
        state.chatMessages = savedData
      } else if (savedData.messages && Array.isArray(savedData.messages)) {
        state.chatMessages = savedData.messages
      } else {
        state.chatMessages = []
      }
    } else {
      state.chatMessages = []
    }
  },

  removeFromStorage(id: string) {
    const storageKey = `chat_history_${id}`
    localStorageUtils.removeChat(storageKey)
  },

  clearConversation() {
    state.chatMessages = []
    // Note: saveConversationToStorage will be called by the main store
  }
})