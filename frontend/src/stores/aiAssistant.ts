// 兼容性重新导出 - 保持现有导入不变
export { useAiAssistantStore, type ChatMessage } from './ai-assistant'
export type { AIModel } from './ai-assistant/types'

// 向后兼容的导出别名 - 重新导入避免循环引用
import { useAiAssistantStore } from './ai-assistant'
export const useAIAssistantStore = useAiAssistantStore