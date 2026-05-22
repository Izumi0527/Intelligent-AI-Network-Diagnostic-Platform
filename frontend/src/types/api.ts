/**
 * 后端 API 响应 schema。
 *
 * 与 backend/app/api 下 FastAPI 的 Pydantic 模型字段对齐，
 * 用作 axios generic 参数，使 response.data 在前端代码里得到强类型。
 *
 * 设计原则：
 * - 大部分字段标 optional，前端只依赖契约的"最小子集"；
 *   后端字段新增不破坏类型，前端少了字段会在守卫里被识别为缺失
 * - 不引入运行时校验依赖（zod 等），只做编译期类型边界
 * - 流式 SSE 走 unknown + 类型守卫，因为同一端点会返回三种厂商原始格式
 */

// ───────────────────────────────── AI 模型 ─────────────────────────────────

export interface ModelStatusResponse {
  connected?: boolean;
  status?: string;
}

export interface ModelDescriptor {
  label: string;
  value: string;
  available?: boolean;
  description?: string;
}

export interface ModelsListResponse {
  models: ModelDescriptor[];
}

// ───────────────────────────────── 对话 ─────────────────────────────────

/** 非流式 /ai/chat 与 /ai/chat (retry) 的返回 schema */
export interface ChatCompletionResponse {
  content?: string;
  message?: {
    content?: string;
  };
}

// ───────────────────────────────── 终端 ─────────────────────────────────

export interface TerminalConnectResponse {
  success: boolean;
  session_id?: string;
  device_info?: string;
  message?: string;
}

export interface TerminalExecuteResponse {
  is_error: boolean;
  output: string;
}

// ───────────────────────────────── 流式 SSE ─────────────────────────────────

/**
 * 后端 (services/ai_service) 统一封装的 StreamEvent 格式。
 * 同一 SSE 连接也可能透传上游厂商原始格式，由调用方做 fallback 兼容。
 */
export interface StreamEvent {
  type: 'thinking' | 'content' | 'error' | 'done' | 'finish';
  data: {
    thinking?: string;
    content?: string;
    error?: string;
  };
}

/** 类型守卫：能否当作 StreamEvent 解释 */
export function isStreamEvent(x: unknown): x is StreamEvent {
  if (x === null || typeof x !== 'object') { return false; }
  const obj = x as { type?: unknown; data?: unknown };
  return typeof obj.type === 'string' && typeof obj.data === 'object' && obj.data !== null;
}

/** Claude/Anthropic SSE 原始 chunk */
export interface ClaudeStreamChunk {
  event?: string;
  data?: {
    delta?: {
      text?: string;
    };
  };
}

/** DeepSeek/OpenAI SSE 原始 chunk */
export interface OpenAIStreamChunk {
  choices?: Array<{
    delta?: {
      content?: string;
      reasoning_content?: string;
    };
  }>;
}

/** 兜底错误字段 */
export interface StreamErrorChunk {
  error?: string | { message?: string };
}
