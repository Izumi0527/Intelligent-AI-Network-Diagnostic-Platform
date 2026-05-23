import { aiService } from '@/utils/aiService';
import type { AIAssistantState, AIModel } from '@/types/chat';
import { logger } from '@/utils/logger';

interface ConnectionActions {
  checkModelConnection(): Promise<boolean>;
  loadAvailableModels(): Promise<void>;
}

export const createConnectionActions = (state: AIAssistantState): ConnectionActions => ({
  async checkModelConnection(): Promise<boolean> {
    try {
      state.isModelConnected = false;
      const response = await aiService.checkModelConnection(state.selectedModel);

      logger.debug('模型连接检查响应:', response.data);

      if (typeof response.data === 'object') {
        if ('connected' in response.data) {
          state.isModelConnected = Boolean(response.data.connected);
          logger.debug('设置连接状态:', state.isModelConnected);
        } else if ('status' in response.data) {
          state.isModelConnected = response.data.status === 'connected';
          logger.debug('基于status设置连接状态:', state.isModelConnected);
        } else {
          logger.error('无法识别的响应格式:', response.data);
          state.isModelConnected = false;
        }

        return state.isModelConnected;
      } else {
        logger.error('响应数据不是有效对象:', response.data);
        state.isModelConnected = false;
        return false;
      }
    } catch (error) {
      logger.error('检查AI模型连接失败:', error);
      state.isModelConnected = false;
      return false;
    }
  },

  async loadAvailableModels(): Promise<void> {
    const MODELS_CACHE_KEY = 'ai_available_models';

    try {
      logger.debug('开始从后端加载模型列表...');
      const response = await aiService.getAvailableModels();

      if (Array.isArray(response.data.models)) {
        state.availableModels = response.data.models.map((model) => ({
          label: model.label,
          value: model.value,
          available: model.available !== false,
          // exactOptionalPropertyTypes: 仅当 description 真实存在时才注入键
          ...(model.description !== undefined && { description: model.description })
        }));

        try {
          localStorage.setItem(MODELS_CACHE_KEY, JSON.stringify(state.availableModels));
          logger.debug('模型列表已缓存到localStorage');
        } catch (storageError) {
          logger.warn('保存模型列表到localStorage失败:', storageError);
        }

        logger.debug('成功加载模型列表:', state.availableModels.length, '个模型');
      } else {
        logger.warn('后端返回的模型数据格式异常');
        throw new Error('后端模型数据格式无效');
      }
    } catch (error: unknown) {
      logger.error('从后端加载模型失败，尝试使用缓存:', error);

      try {
        const cachedModels = localStorage.getItem(MODELS_CACHE_KEY);
        if (cachedModels !== null && cachedModels !== '') {
          const parsedModels: unknown = JSON.parse(cachedModels);
          if (Array.isArray(parsedModels) && parsedModels.length > 0) {
            // 缓存格式由本模块自己写入（见上方 setItem），故信任结构，断言为 AIModel[]
            state.availableModels = parsedModels as AIModel[];
            logger.debug('使用缓存的模型列表:', parsedModels.length, '个模型');
            return;
          }
        }
      } catch (cacheError) {
        logger.warn('读取缓存的模型列表失败:', cacheError);
      }

      logger.warn('模型加载失败，使用最小默认配置');
    }

    if (state.availableModels.length === 0) {
      logger.warn('没有可用模型，使用最小默认配置');
      state.availableModels = [
        { label: 'DeepSeek-V4-Flash', value: 'deepseek-v4-flash', available: true }
      ];
    }
  }
});
