// AI智能网络故障分析平台 - 类型定义文件
// 生成时间: 2025-09-07 22:15

// 导入依赖类型
import type { ApiError, ChatData, ChatMessage, FormattedMessage } from './chat';

// 网络终端相关类型
export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';
export type ConnectionType = 'ssh' | 'telnet';

export interface TerminalConnectionParams {
    type: ConnectionType;
    address: string;
    port: string;
    username: string;
    password: string;
}

export interface TerminalResponse {
    success: boolean;
    message?: string;
    error?: string;
    output?: string;
    welcome?: string;
}

// AI助手相关类型 - 重新导出统一类型
export type {
    ChatMessage,
    Message,
    FormattedMessage,
    MessageHistoryItem,
    ChatData,
    ChatSettings
} from './chat'

export {
    isApiError,
    isChatMessage,
    formatMessagesForAPI
} from './chat'

export interface AIModel {
    id: string;
    label: string;
    value: string;
    description?: string;
    maxTokens?: number;
    available: boolean;
}

export interface AIResponse {
    success: boolean;
    message: string;
    model: string;
    tokens?: {
        prompt: number;
        completion: number;
        total: number;
    };
    processingTime?: number;
}

export interface ModelConnectionResponse {
    connected: boolean;
    message?: string;
}

// 错误处理类型
export interface ErrorInfo {
    code: string;
    message: string;
    details?: string;
    stack?: string;
    timestamp: string;
}

// 本地存储类型
export interface LocalStorageUtils {
    saveChat: (key: string, chatData: ChatData | ChatMessage[]) => boolean;
    loadChat: (key: string) => ChatData | ChatMessage[] | null;
    removeChat: (key: string) => boolean;
    clearChat: (key: string) => boolean;
    getAllChats: () => Record<string, ChatData | ChatMessage[]>;
    clearAllChats: () => boolean;
}

// Store状态类型
export interface StoreActions {
    utilActions: {
        handleMessageError: (error: ErrorInfo | ApiError, content: string) => void;
        updateLastActivity: () => void;
        validateMessage: (content: string) => boolean;
    };
    storageActions: {
        saveToStorage: (data: ChatData) => void;
        loadFromStorage: (id: string) => ChatData | null;
        removeFromStorage: (id: string) => void;
    };
}

// 异步操作选项
export interface AsyncOperationOptions {
    timeout?: number;
    retries?: number;
    onProgress?: (progress: number) => void;
    signal?: AbortSignal;
}

// 网络分析相关类型
export interface NetworkAnalysisResult {
    analysis: string;
    recommendations: string[];
    severity: 'low' | 'medium' | 'high' | 'critical';
    confidence: number;
    metrics: Record<string, string | number>;
}

// Timeout引用类型 (用于替代any)
export type TimeoutRef = ReturnType<typeof setTimeout> | null;
export type IntervalRef = ReturnType<typeof setInterval> | null;

// 事件处理器类型
export type EventHandler<T = Event> = (event: T) => void;
export type AsyncEventHandler<T = Event> = (event: T) => Promise<void>;

// 通用回调类型
export type Callback<T = void> = () => T;
export type AsyncCallback<T = void> = () => Promise<T>;
export type CallbackWithParam<P, T = void> = (param: P) => T;
export type AsyncCallbackWithParam<P, T = void> = (param: P) => Promise<T>;

// 工具函数类型
export type MessageFormatter = (messages: ChatMessage[]) => FormattedMessage[];
export type ErrorHandler = (error: ErrorInfo | ApiError, context: string) => void;

// 组件Props基类
export interface BaseComponentProps {
    class?: string;
    style?: Record<string, string | number>;
    disabled?: boolean;
    loading?: boolean;
}

// HTTP响应类型
export interface HttpResponse<T = unknown> {
    data: T;
    status: number;
    statusText: string;
    headers: Record<string, string>;
}

// 表单字段类型
export interface FormField<T = unknown> {
    name: string;
    value: T;
    error?: string;
    touched: boolean;
    valid: boolean;
}

// 主题配置类型
export interface ThemeConfig {
    colors: Record<string, string>;
    fonts: Record<string, string>;
    spacing: Record<string, string>;
    borderRadius: Record<string, string>;
    animations: Record<string, string>;
} 