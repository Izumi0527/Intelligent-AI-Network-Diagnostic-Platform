import { aiService } from '@/utils/aiService';
import type { AIAssistantState, AIModel } from '@/types/chat';
import { logger } from '@/utils/logger';

interface ConnectionActions {
  checkModelConnection(): Promise<boolean>;
  loadAvailableModels(): Promise<void>;
}

export const createConnectionActions = (state: AIAssistantState): ConnectionActions => {
  // 同一 model 在飞行中复用同一 promise，避免 watch(selectedModel) 与显式调用同时
  // 发起重复 /status 请求（P2-ii 联调实测：模型切换时同 URL 出现 2 次）。
  let pendingCheck: Promise<boolean> | null = null;
  let pendingCheckModel: string | null = null;

  // 根据 model.value 前缀推断所属 provider，与 /api/ai/models 响应里的 status map key 对齐
  const providerOf = (value: string): string | null => {
    if (value.startsWith('gpt-')) { return 'openai'; }
    if (value.startsWith('claude-')) { return 'anthropic'; }
    if (value.startsWith('deepseek-')) { return 'deepseek'; }
    return null;
  };

  return {
    async checkModelConnection(): Promise<boolean> {
      const model = state.selectedModel;
      if (pendingCheck !== null && pendingCheckModel === model) {
        return pendingCheck;
      }

      pendingCheckModel = model;
      pendingCheck = (async (): Promise<boolean> => {
        try {
          state.isModelConnected = false;
          const response = await aiService.checkModelConnection(model);

          logger.debug('模型连接检查响应:', response.data);

          if (typeof response.data === 'object') {
            if ('connected' in response.data) {
              state.isModelConnected = Boolean(response.data.connected);
            } else if ('status' in response.data) {
              state.isModelConnected = response.data.status === 'connected';
            } else {
              logger.error('无法识别的响应格式:', response.data);
              state.isModelConnected = false;
            }

            // 单一真值源纠偏：单模型 status 端点（/api/ai/models/{model}/status）
            // 用 8s 超时确认了 provider 可用 → 同 provider 的所有模型应一并解锁"（未配置）"。
            // 避免 /api/ai/models 在冷启动时因 3-8s 超时把 available 误置为 false 后
            // UI 出现"徽章已连接 + 选项未配置"的矛盾态。
            // 只做 false→true 上调，不做下调：避免单模型测试失败误伤同 provider 其他模型。
            if (state.isModelConnected) {
              const provider = providerOf(model);
              if (provider !== null) {
                state.availableModels = state.availableModels.map((m) =>
                  providerOf(m.value) === provider && m.available === false
                    ? { ...m, available: true }
                    : m
                );
              }
            }

            return state.isModelConnected;
          }

          logger.error('响应数据不是有效对象:', response.data);
          state.isModelConnected = false;
          return false;
        } catch (error) {
          logger.error('检查AI模型连接失败:', error);
          state.isModelConnected = false;
          return false;
        } finally {
          // 只在 model 没被覆盖时才清空，避免新切换的 model 被旧 finally 抹掉
          if (pendingCheckModel === model) {
            pendingCheck = null;
            pendingCheckModel = null;
          }
        }
      })();

      return pendingCheck;
    },

    async loadAvailableModels(): Promise<void> {
      const MODELS_CACHE_KEY = 'ai_available_models';

      try {
        logger.debug('开始从后端加载模型列表...');
        const response = await aiService.getAvailableModels();

        if (Array.isArray(response.data.models)) {
          const statusMap = response.data.status;
          state.availableModels = response.data.models.map((model) => {
            // available 优先取后端显式字段；缺省时按 provider status 推断；都缺省视为可用
            let available = model.available !== false;
            if (model.available === undefined && statusMap !== undefined) {
              const provider = providerOf(model.value);
              if (provider !== null && statusMap[provider] !== undefined) {
                available = statusMap[provider].connected;
              }
            }
            return {
              label: model.label,
              value: model.value,
              available,
              // exactOptionalPropertyTypes: 仅当 description 真实存在时才注入键
              ...(model.description !== undefined && { description: model.description })
            };
          });

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
  };
};
