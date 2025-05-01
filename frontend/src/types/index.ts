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

// AI助手相关类型
export interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
}

export interface AIModel {
    label: string;
    value: string;
}

export interface AIResponse {
    message: string;
    model: string;
}

export interface ModelConnectionResponse {
    connected: boolean;
    message?: string;
} 