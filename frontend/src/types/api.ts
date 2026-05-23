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

// 后端 /ai/models 响应附带的 provider 级状态 map
export interface ProviderStatus {
  connected: boolean;
  message?: string;
  last_check?: string;
}

export interface ModelsListResponse {
  models: ModelDescriptor[];
  status?: Record<string, ProviderStatus>;
}

// ───────────────────────────────── 对话 ─────────────────────────────────

/** 单条联网搜索来源（与后端 SearchSource 模型对齐） */
export interface SearchSource {
  title: string;
  url: string;
  description?: string;
}

/** 非流式 /ai/chat 与 /ai/chat (retry) 的返回 schema */
export interface ChatCompletionResponse {
  content?: string;
  message?: {
    content?: string;
  };
  /** 联网搜索引用的来源（enable_search 启用时） */
  sources?: SearchSource[];
  /** 联网搜索是否失败（启用但未取到结果或异常时为 true） */
  search_failed?: boolean;
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
  type: 'thinking' | 'content' | 'error' | 'done' | 'finish' | 'search_results';
  data: {
    thinking?: string;
    content?: string;
    error?: string;
    /** type=search_results 时携带 */
    sources?: SearchSource[];
    /** type=search_results 时携带 */
    search_failed?: boolean;
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

// ───────────────────────────────── 前端解析后的统一事件 ─────────────────────────────────

/**
 * aiService.ts SSE 状态机解析后通过 ReadableStream 输出的统一事件格式。
 * 每条事件序列化为一行 JSON（用 `\n` 分隔），由 messaging.ts 的 buffer+split 解析。
 *
 * 取代历史上的"层间 magic string"做法（`"🤔思考: ..."` / `"错误: ..."` 前缀），
 * 让事件类型回到结构化字段，避免 in-band signaling 与文本前缀冲突。
 *
 * Discriminated union：thinking/content/error 携带 text；search_results 携带 sources 与
 * searchFailed —— 让消费方按 type 强制 narrow 字段，避免可选字段污染。
 */
export type ParsedStreamEvent =
  | { type: 'thinking'; text: string }
  | { type: 'content'; text: string }
  | { type: 'error'; text: string }
  | { type: 'search_results'; sources: SearchSource[]; searchFailed: boolean };

/** 类型守卫：能否当作 ParsedStreamEvent 解释 */
export function isParsedStreamEvent(x: unknown): x is ParsedStreamEvent {
  if (x === null || typeof x !== 'object') { return false; }
  const obj = x as { type?: unknown; text?: unknown; sources?: unknown; searchFailed?: unknown };
  if (obj.type === 'thinking' || obj.type === 'content' || obj.type === 'error') {
    return typeof obj.text === 'string';
  }
  if (obj.type === 'search_results') {
    return Array.isArray(obj.sources) && typeof obj.searchFailed === 'boolean';
  }
  return false;
}
