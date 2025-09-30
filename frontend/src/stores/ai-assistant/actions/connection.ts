import { aiService } from '@/utils/aiService'
import type { AIAssistantState } from '../types'

export const createConnectionActions = (state: AIAssistantState) => ({
  async checkModelConnection() {
    try {
      state.isModelConnected = false
      const response = await aiService.checkModelConnection(state.selectedModel)

      console.log('模型连接检查响应:', response.data)

      if (response.data && typeof response.data === 'object') {
        if ('connected' in response.data) {
          state.isModelConnected = Boolean(response.data.connected)
          console.log('设置连接状态:', state.isModelConnected)
        } else if ('status' in response.data) {
          state.isModelConnected = response.data.status === 'connected'
          console.log('基于status设置连接状态:', state.isModelConnected)
        } else {
          console.error('无法识别的响应格式:', response.data)
          state.isModelConnected = false
        }

        return state.isModelConnected
      } else {
        console.error('响应数据不是有效对象:', response.data)
        state.isModelConnected = false
        return false
      }
    } catch (error) {
      console.error('检查AI模型连接失败:', error)
      state.isModelConnected = false
      return false
    }
  },

  async loadAvailableModels() {
    const MODELS_CACHE_KEY = 'ai_available_models'

    try {
      console.log('开始从后端加载模型列表...')
      const response = await aiService.getAvailableModels()

      if (response.data && Array.isArray(response.data.models)) {
        state.availableModels = response.data.models.map((model: any) => ({
          label: model.label,
          value: model.value,
          available: model.available !== false,
          description: model.description
        }))

        try {
          localStorage.setItem(MODELS_CACHE_KEY, JSON.stringify(state.availableModels))
          console.log('模型列表已缓存到localStorage')
        } catch (storageError) {
          console.warn('保存模型列表到localStorage失败:', storageError)
        }

        console.log('成功加载模型列表:', state.availableModels.length, '个模型')
      } else {
        console.warn('后端返回的模型数据格式异常')
        throw new Error('后端模型数据格式无效')
      }
    } catch (error: unknown) {
      console.error('从后端加载模型失败，尝试使用缓存:', error)

      try {
        const cachedModels = localStorage.getItem(MODELS_CACHE_KEY)
        if (cachedModels) {
          const parsedModels = JSON.parse(cachedModels)
          if (Array.isArray(parsedModels) && parsedModels.length > 0) {
            state.availableModels = parsedModels
            console.log('使用缓存的模型列表:', parsedModels.length, '个模型')
            return
          }
        }
      } catch (cacheError) {
        console.warn('读取缓存的模型列表失败:', cacheError)
      }

      console.warn('模型加载失败，使用最小默认配置')
    }

    if (state.availableModels.length === 0) {
      console.warn('没有可用模型，使用最小默认配置')
      state.availableModels = [
        { label: 'DeepSeek-V3', value: 'deepseek-chat', available: true }
      ]
    }
  }
})