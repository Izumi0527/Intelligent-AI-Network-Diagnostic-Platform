import { defineStore } from 'pinia';
import { aiService } from '@/utils/aiService';
import { localStorageUtils } from '@/utils/localStorageUtils';

export interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
}

export interface AIModel {
    label: string;
    value: string;
}

export const useAIAssistantStore = defineStore('aiAssistant', {
    state: () => ({
        selectedModel: 'deepseek-chat',
        availableModels: [
            { label: 'Claude 3.7', value: 'claude-3.7' },
            { label: 'DeepSeek-R1', value: 'deepseek-reasoner' },
            { label: 'DeepSeek-V3-0324', value: 'deepseek-chat' },
            { label: 'Claude 3 Sonnet', value: 'claude-3-sonnet' },
            { label: 'Claude 3.5 Sonnet', value: 'claude-3.5-sonnet' },
            { label: 'GPT-4o', value: 'gpt-4o' },
        ] as AIModel[],
        isModelConnected: false,
        streamingEnabled: true,
        isAIResponding: false,
        chatMessages: [] as ChatMessage[],
        isLoading: false,
        error: null,
    }),

    actions: {
        async checkModelConnection() {
            try {
                this.isModelConnected = false;
                const response = await aiService.checkModelConnection(this.selectedModel);

                // 在控制台输出响应，帮助调试
                console.log('模型连接检查响应:', response.data);

                // 添加对响应格式的强健处理
                if (response.data && typeof response.data === 'object') {
                    if ('connected' in response.data) {
                        // 标准格式处理
                        this.isModelConnected = Boolean(response.data.connected);
                        console.log('设置连接状态:', this.isModelConnected);
                    } else if ('status' in response.data) {
                        // 兼容处理，如果有status字段
                        this.isModelConnected = response.data.status === 'connected';
                        console.log('基于status设置连接状态:', this.isModelConnected);
                    } else {
                        console.error('无法识别的响应格式:', response.data);
                        this.isModelConnected = false;
                    }

                    return this.isModelConnected;
                } else {
                    console.error('响应数据不是有效对象:', response.data);
                    this.isModelConnected = false;
                    return false;
                }
            } catch (error) {
                console.error('检查AI模型连接失败:', error);
                this.isModelConnected = false;
                return false;
            }
        },

        async sendMessage(content: string) {
            if (!content.trim() || !this.isModelConnected || this.isAIResponding) {
                return;
            }

            // 添加用户消息
            this.chatMessages.push({
                role: 'user',
                content,
            });

            // 保存到本地存储
            this.saveConversationToStorage();

            // 设置响应状态
            this.isAIResponding = true;

            try {
                if (this.streamingEnabled) {
                    await this.sendMessageStream(content);
                } else {
                    // 使用重试功能的方法发送消息
                    await this.sendMessageRegular(content);
                }
            } catch (error: any) {
                console.error('消息发送错误:', error);

                this.handleMessageError(error, content);
            } finally {
                this.isAIResponding = false;
                // 保存到本地存储
                this.saveConversationToStorage();
            }
        },

        async sendMessageStream(content: string) {
            // 创建一个唯一的消息会话ID，用于日志
            const sessionId = Date.now().toString();
            console.log(`开始流式会话 ${sessionId}`);

            try {
                // 创建一个空的助手消息
                const assistantMessage: ChatMessage = {
                    role: 'assistant',
                    content: ''
                };

                // 添加到聊天历史
                this.chatMessages.push(assistantMessage);

                // 获取历史消息，格式化为API所需格式 (不包括刚刚添加的空助手消息)
                const messageHistory = this.formatMessagesForAPI(
                    this.chatMessages.filter(msg => msg !== assistantMessage)
                );

                // 记录日志
                console.log(`发送流式请求，消息数: ${messageHistory.length}，会话ID: ${sessionId}`);

                try {
                    // 发送流式请求
                    const response = await aiService.sendMessageStream({
                        model: this.selectedModel,
                        messages: messageHistory,
                        stream: true
                    });

                    // 确保有正确的响应和数据
                    if (!response || !response.data) {
                        throw new Error('流式响应无效');
                    }

                    // 处理ReadableStream
                    if (response.data instanceof ReadableStream) {
                        const reader = response.data.getReader();
                        const decoder = new TextDecoder('utf-8');

                        console.log(`开始读取流，会话ID: ${sessionId}`);

                        let contentReceived = false;
                        let isFirstChunk = true;

                        try {
                            while (true) {
                                const { value, done } = await reader.read();

                                if (done) {
                                    console.log(`流读取完成，会话ID: ${sessionId}`);
                                    break;
                                }

                                if (value) {
                                    // 解码文本块
                                    const chunk = decoder.decode(value, { stream: true });
                                    
                                    if (chunk) {
                                        // 首个数据块额外调试
                                        if (isFirstChunk) {
                                            console.debug(`首个数据块 (${chunk.length}字符)：`, chunk.substring(0, 100));
                                            isFirstChunk = false;
                                        }
                                        
                                        // 检查是否为结束标记
                                        if (chunk.includes('[DONE]')) {
                                            console.log('收到流结束标记');
                                            continue;
                                        }
                                        
                                        // 检查是否为错误消息
                                        if (chunk.startsWith('错误:')) {
                                            console.error(`收到错误消息: ${chunk}`);
                                            assistantMessage.content += `\n${chunk}`;
                                            contentReceived = true;
                                            
                                            // 强制刷新UI
                                            this.chatMessages = [...this.chatMessages];
                                            continue;
                                        }
                                        
                                        // 正常内容，直接追加
                                        assistantMessage.content += chunk;
                                        contentReceived = true;
                                        
                                        // 强制每次收到内容都刷新UI，确保实时显示
                                        this.chatMessages = [...this.chatMessages];
                                        
                                        // 调试输出块长度，监控流量
                                        if (chunk.length > 50) {
                                            console.debug(`接收到较大数据块: ${chunk.length}字符`);
                                        }
                                    }
                                }
                            }

                            // 读取结束，进行最终解码
                            const finalChunk = decoder.decode();
                            if (finalChunk && finalChunk.trim()) {
                                console.debug(`最终数据块 (${finalChunk.length}字符)：`, finalChunk.substring(0, 100));
                                
                                // 检查最终块中的特殊标记
                                if (!finalChunk.includes('[DONE]') && !finalChunk.startsWith('错误:')) {
                                    assistantMessage.content += finalChunk;
                                    contentReceived = true;
                                    
                                    // 最终更新确保显示完整内容
                                    this.chatMessages = [...this.chatMessages];
                                }
                            }

                            // 检查是否接收到内容
                            if (!contentReceived || !assistantMessage.content.trim()) {
                                console.warn(`未接收到有效内容，会话ID: ${sessionId}`);

                                // 移除空助手消息
                                const index = this.chatMessages.indexOf(assistantMessage);
                                if (index !== -1) {
                                    this.chatMessages.splice(index, 1);
                                }

                                // 添加错误消息
                                this.chatMessages.push({
                                    role: 'assistant',
                                    content: '发生错误: 未接收到有效内容'
                                });
                            } else {
                                console.log(`成功接收内容，总长度: ${assistantMessage.content.length}字符`);
                            }
                            
                            // 无论成功与否，确保清理状态
                            this.isAIResponding = false;
                            
                        } catch (e) {
                            console.error(`流读取错误: ${e}, 会话ID: ${sessionId}`);

                            // 移除可能的空助手消息
                            const index = this.chatMessages.indexOf(assistantMessage);
                            if (index !== -1) {
                                this.chatMessages.splice(index, 1);
                            }

                            // 添加错误消息
                            this.chatMessages.push({
                                role: 'assistant',
                                content: `发生错误: 读取流数据失败 - ${e}`
                            });
                            
                            // 确保清理状态
                            this.isAIResponding = false;
                        }
                    } else {
                        console.error(`响应不是ReadableStream，会话ID: ${sessionId}，实际类型: ${typeof response.data}`);

                        // 移除助手消息
                        const index = this.chatMessages.indexOf(assistantMessage);
                        if (index !== -1) {
                            this.chatMessages.splice(index, 1);
                        }

                        // 添加错误消息
                        this.chatMessages.push({
                            role: 'assistant',
                            content: '发生错误: 服务器返回的不是流式数据'
                        });
                        
                        // 确保清理状态
                        this.isAIResponding = false;
                    }

                    // 保存对话
                    this.saveConversationToStorage();
                    console.log(`流式响应处理完成，会话ID: ${sessionId}`);
                } catch (error) {
                    // 处理错误
                    console.error(`流式响应错误: ${error}, 会话ID: ${sessionId}`);

                    // 移除可能的空助手消息
                    const index = this.chatMessages.indexOf(assistantMessage);
                    if (index !== -1) {
                        this.chatMessages.splice(index, 1);
                    }
                    
                    // 确保清理状态
                    this.isAIResponding = false;
                    
                    // 添加错误消息到UI
                    this.chatMessages.push({
                        role: 'assistant',
                        content: `发生错误: ${error.message || '请求失败'}`
                    });
                }
            } catch (error) {
                // 确保清理状态
                this.isAIResponding = false;
                console.error(`流式会话整体错误: ${error}`);
            }
        },

        async sendMessageRegular(content: string) {
            try {
                // 标记发送状态
                this.isLoading = true;
                this.error = null;

                // 格式化历史消息
                const messageHistory = this.formatMessagesForAPI(this.chatMessages);

                // 注意: 不要使用slice(0, -1)，它会在只有一条消息时返回空数组
                let messagesToSend = [...messageHistory];

                // 安全检查：确保至少包含一条消息
                if (messagesToSend.length === 0) {
                    console.warn('消息历史为空，将只发送当前用户消息');
                    messagesToSend = [
                        {
                            role: 'user',
                            content: content
                        }
                    ];
                }

                console.log(`发送非流式请求，消息数: ${messagesToSend.length}`);

                // 使用重试机制发送请求
                const response = await aiService.sendMessageWithRetry({
                    model: this.selectedModel,
                    messages: messagesToSend
                }, 3); // 最多重试3次

                // 处理响应
                const assistantContent = response.data?.content || response.data?.message?.content;
                if (assistantContent) {
                    this.addAssistantMessage(assistantContent);
                } else {
                    console.error('响应格式异常，无法获取内容:', response.data);
                    throw new Error('响应格式异常：缺少内容');
                }

                this.isLoading = false;
            } catch (error) {
                // 错误处理
                this.handleMessageError(error, content);
            }
        },

        clearConversation() {
            this.chatMessages = [];
            this.saveConversationToStorage();
        },

        saveConversationToStorage() {
            // 使用选择的模型作为key的一部分，这样不同模型的对话可以分开存储
            const storageKey = `chat_history_${this.selectedModel}`;
            localStorageUtils.saveChat(storageKey, this.chatMessages);
        },

        loadConversationFromStorage() {
            const storageKey = `chat_history_${this.selectedModel}`;
            const savedMessages = localStorageUtils.loadChat(storageKey);

            if (savedMessages && Array.isArray(savedMessages)) {
                this.chatMessages = savedMessages;
            } else {
                this.chatMessages = [];
            }
        },

        // 当用户切换模型时调用此方法
        changeModel(modelValue: string) {
            this.selectedModel = modelValue;
            this.loadConversationFromStorage();
            this.checkModelConnection();
        },

        // 添加新方法：格式化消息，确保兼容Deepseek等不同API格式
        formatMessagesForAPI(messages: ChatMessage[]) {
            if (!messages || !Array.isArray(messages)) return [];

            return messages.map(msg => {
                // 确保role只包含user或assistant
                const role = msg.role === 'user' ? 'user' : 'assistant';

                // 返回标准格式 (不包含timestamp，只保留核心字段)
                return {
                    role,
                    content: msg.content
                };
            });
        },

        addUserMessage(content: string): ChatMessage {
            const userMessage: ChatMessage = {
                role: 'user',
                content,
            };
            this.chatMessages.push(userMessage);
            return userMessage;
        },

        addAssistantMessage(content: string) {
            const assistantMessage: ChatMessage = {
                role: 'assistant',
                content,
            };
            this.chatMessages.push(assistantMessage);
        },

        handleMessageError(error: any, content: string) {
            console.error('消息发送错误:', error);

            // 增强错误处理，处理不同类型的错误
            let errorMessage = '发生错误: ';

            if (error.response) {
                // 服务器响应了但状态码不是2xx
                const statusCode = error.response.status;

                if (statusCode === 422) {
                    errorMessage += '请求参数验证失败';
                    if (error.response.data?.detail) {
                        const details = Array.isArray(error.response.data.detail)
                            ? error.response.data.detail[0]?.msg
                            : error.response.data.detail;
                        if (details) {
                            errorMessage += `: ${details}`;
                        }
                    }
                } else if (statusCode === 500) {
                    errorMessage += '服务器内部错误';
                    // 尝试提取更详细的错误信息
                    if (error.response.data?.detail) {
                        errorMessage += `: ${error.response.data.detail}`;
                    }
                } else if (statusCode === 400) {
                    errorMessage += '无效请求';
                    if (error.response.data?.detail) {
                        errorMessage += `: ${error.response.data.detail}`;
                    }
                } else {
                    errorMessage += `服务器返回${statusCode}错误`;
                }
            } else if (error.request) {
                // 请求已发送但没有收到响应
                errorMessage += '服务器无响应，请检查网络连接';
            } else {
                errorMessage += error.message || '无法连接到AI服务';
            }
            // 使用更友好的消息格式
            if (errorMessage.includes('Request failed with status code 500')) {
                errorMessage = '发生错误: 服务器内部错误，请稍后再试';
            }
            // 添加错误消息
            this.chatMessages.push({
                role: 'assistant',
                content: errorMessage
            });

            this.isLoading = false;
        }
    }
}); 