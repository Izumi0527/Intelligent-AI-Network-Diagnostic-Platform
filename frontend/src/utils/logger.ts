/**
 * 前端分级日志器。
 *
 * 设计要点：
 * - level 可由 VITE_LOG_LEVEL 覆盖；未设置时开发态走 debug，生产态走 warn
 * - 每条日志带 traceId（UUID v4），方便与后端日志关联
 * - 生产态对 string payload 自动截断至 1000 字符，避免误印大体积响应
 * - 暂不上送远端，需要时在 emit() 内追加 fetch 即可
 */

export type LogLevel = 'debug' | 'info' | 'warn' | 'error'

const LEVEL_RANK: Record<LogLevel, number> = {
  debug: 10,
  info: 20,
  warn: 30,
  error: 40,
};

const DEFAULT_LEVEL: LogLevel = import.meta.env.DEV ? 'debug' : 'warn';
const PROD_TRUNCATE_LIMIT = 1000;

function resolveLevel(): LogLevel {
  const raw = (import.meta.env.VITE_LOG_LEVEL as string | undefined)?.toLowerCase();
  if (raw !== undefined && raw in LEVEL_RANK) {
    return raw as LogLevel;
  }
  return DEFAULT_LEVEL;
}

function newTraceId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  // 兜底：v4 风格但非密码学随机；浏览器 crypto.randomUUID 缺失时极少见
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

function truncate(payload: unknown): unknown {
  if (import.meta.env.DEV) { return payload; }
  if (typeof payload === 'string' && payload.length > PROD_TRUNCATE_LIMIT) {
    return `${payload.slice(0, PROD_TRUNCATE_LIMIT)}…[truncated ${payload.length - PROD_TRUNCATE_LIMIT}]`;
  }
  return payload;
}

class Logger {
  private readonly level: LogLevel;
  private readonly traceId: string;

  constructor(level: LogLevel, traceId?: string) {
    this.level = level;
    this.traceId = traceId ?? newTraceId();
  }

  /** 派生子 logger，复用 level 但生成新 traceId（用于划分独立请求/会话） */
  child(): Logger {
    return new Logger(this.level);
  }

  debug(message: string, ...args: unknown[]): void { this.emit('debug', message, args); }
  info(message: string, ...args: unknown[]): void { this.emit('info', message, args); }
  warn(message: string, ...args: unknown[]): void { this.emit('warn', message, args); }
  error(message: string, ...args: unknown[]): void { this.emit('error', message, args); }

  private emit(level: LogLevel, message: string, args: unknown[]): void {
    if (LEVEL_RANK[level] < LEVEL_RANK[this.level]) { return; }
    const tag = `[${level.toUpperCase()}][${this.traceId.slice(0, 8)}]`;
    const payload = args.map(truncate);
    const fn = level === 'debug' ? console.debug
      : level === 'info' ? console.info
        : level === 'warn' ? console.warn
          : console.error;
    fn(tag, message, ...payload);
  }
}

export const logger = new Logger(resolveLevel());
export const createLogger = (): Logger => logger.child();
