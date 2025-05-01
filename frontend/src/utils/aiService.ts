import axios, { AxiosResponse } from 'axios';

const api = axios.create({
    baseURL: '/api',
    timeout: 60000,
});

interface MessageHistoryItem {
    role: string;
    content: string;
}

interface SendMessageParams {
    model: string;
    messages: MessageHistoryItem[];
    stream?: boolean;
}

// 添加新的错误处理拦截器
api.interceptors.response.use(
    response => response,
    error => {
        // 特别处理422错误
        if (error.response && error.response.status === 422) {
            console.error('请求参数验证失败:', error.response.data);
            // 保留原始错误数据以便更详细的处理
            error.validationErrors = error.response.data.detail || [];
        }
        return Promise.reject(error);
    }
);

/**
 * 格式化消息历史，确保API兼容
 */
export function formatMessages(messages: any[]): Array<{ role: string, content: string }> {
    // 安全检查：确保messages是非空数组
    if (!messages || !Array.isArray(messages) || messages.length === 0) {
        console.warn('formatMessages接收到空消息列表，这可能导致请求失败');
        return [];
    }

    return messages.map(msg => {
        // 确保每条消息都有role和content字段
        if (!msg || typeof msg !== 'object') {
            console.warn('消息格式无效，跳过:', msg);
            return { role: 'user', content: '无效消息' };
        }

        const role = msg.role || 'user';
        // 确保content不为空或仅包含空白字符
        const content = msg.content && typeof msg.content === 'string'
            ? msg.content.trim()
            : '内容为空';

        if (!msg.content || msg.content.trim() === '') {
            console.warn(`发现空内容消息，role=${role}`);
        }

        return { role, content };
    }).filter(msg => msg && msg.content); // 过滤掉无效消息
}

export const aiService = {
    async checkModelConnection(model: string) {
        return api.get(`/ai/models/${model}/status`);
    },

    async sendMessageStream(params: SendMessageParams) {
        // 确保消息格式正确
        const formattedParams = {
            ...params,
            messages: formatMessages(params.messages),
            stream: true
        };

        try {
            console.log('发送流式请求:', {
                model: formattedParams.model,
                messageCount: formattedParams.messages.length
            });

            // 使用不同的方式处理流式响应
            const response = await api.post('/ai/chat/stream', formattedParams, {
                responseType: 'text', // 使用文本类型接收响应
                timeout: 120000 // 增加超时时间以处理长对话
            });

            // 创建一个可读流，用于处理SSE格式的数据
            const stream = new ReadableStream({
                start(controller) {
                    const encoder = new TextEncoder();
                    let buffer = ''; // 用于存储跨块的SSE数据

                    try {
                        // 处理单行SSE数据
                        const processLine = (line: string) => {
                            if (line === 'data: [DONE]' || line === '[DONE]') {
                                console.debug('接收到流结束标记');
                                return;
                            }

                            // 处理可能存在的多层嵌套data:前缀问题
                            let contentLine = line;
                            // 持续清除所有的data:前缀
                            while(contentLine.startsWith('data:')) {
                                contentLine = contentLine.substring(5).trim();
                            }

                            // 检查是否为空
                            if (!contentLine) return;

                            try {
                                // 尝试解析为JSON
                                if (contentLine.startsWith('{') || contentLine.startsWith('[')) {
                                    const data = JSON.parse(contentLine);

                                    // 处理不同AI服务的输出格式
                                    let content = '';

                                    // 处理Claude/Anthropic事件格式
                                    if (data.event === 'content_block_delta' && data.data?.delta?.text) {
                                        content = data.data.delta.text;
                                    } 
                                    // 处理DeepSeek/OpenAI格式
                                    else if (data.choices && data.choices.length > 0) {
                                        if (data.choices[0].delta && data.choices[0].delta.content) {
                                            content = data.choices[0].delta.content;
                                        }
                                    }
                                    // 处理错误信息
                                    else if (data.error) {
                                        content = `错误: ${typeof data.error === 'string' ? data.error : JSON.stringify(data.error)}`;
                                    }

                                    // 只有当提取到实际内容时才传递，按字符或小块分割以提高流畅性
                                    if (content) {
                                        // 对长内容进行细粒度处理，使显示更流畅
                                        if (content.length > 20) {
                                            const chunkSize = Math.min(20, Math.ceil(content.length / 3));
                                            for (let i = 0; i < content.length; i += chunkSize) {
                                                const chunk = content.substring(i, i + chunkSize);
                                                controller.enqueue(encoder.encode(chunk));
                                            }
                                        } else {
                                            controller.enqueue(encoder.encode(content));
                                        }
                                    }
                                } else {
                                    // 如果不是JSON但仍有内容，则直接传递
                                    if (contentLine && !contentLine.includes('[DONE]')) {
                                        // 纯文本也进行分块处理
                                        if (contentLine.length > 30) {
                                            const chunkSize = Math.min(30, Math.ceil(contentLine.length / 4));
                                            for (let i = 0; i < contentLine.length; i += chunkSize) {
                                                const chunk = contentLine.substring(i, i + chunkSize);
                                                controller.enqueue(encoder.encode(chunk));
                                            }
                                        } else {
                                            controller.enqueue(encoder.encode(contentLine));
                                        }
                                    }
                                }
                            } catch (e) {
                                // 解析失败时，直接传递原始内容
                                if (contentLine && !contentLine.includes('[DONE]')) {
                                    controller.enqueue(encoder.encode(contentLine));
                                }
                            }
                        };
                    
                        // 处理文本响应，将其转换为流
                        const textData = response.data;
                        console.debug('收到文本响应，长度：', textData.length);
                        
                        // 将文本按行分割
                        if (typeof textData === 'string') {
                            const lines = textData.split('\n');
                            for (const line of lines) {
                                if (line.trim()) {
                                    processLine(line.trim());
                                }
                            }
                        } else {
                            throw new Error(`响应数据类型意外：${typeof textData}`);
                        }
                        
                        // 处理完成后关闭控制器
                        controller.close();
                        
                        // 创建mock的pump函数避免后续代码错误
                        const pump = async () => {
                            // 不执行任何操作，因为已经处理完文本
                        };
                    } catch (error) {
                        console.error('处理流数据时出错:', error);
                        controller.error(error);
                    }
                }
            });

            return {
                data: stream,
                status: response.status,
                headers: response.headers
            };
        } catch (error) {
            console.error('流式请求失败:', error);
            
            // 错误信息也转换为流返回
            const errorStream = new ReadableStream({
                start(controller) {
                    const encoder = new TextEncoder();
                    let errorMessage = '错误: 无法连接到服务器';
                    
                    // 尝试提取更详细的错误信息
                    if (error.response) {
                        errorMessage = `错误: 服务器返回${error.response.status}错误`;
                        if (error.response.data) {
                            errorMessage += ` - ${error.response.data}`;
                        }
                    } else if (error.message) {
                        errorMessage = `错误: ${error.message}`;
                    }
                    
                    controller.enqueue(encoder.encode(errorMessage));
                    controller.close();
                }
            });
            
            return {
                data: errorStream,
                status: error.response?.status || 500,
                headers: error.response?.headers || {}
            };
        }
    },

    async sendMessage(params: SendMessageParams) {
        // 确保消息格式正确
        const formattedParams = {
            ...params,
            messages: formatMessages(params.messages)
        };

        try {
            return api.post('/ai/chat', formattedParams);
        } catch (error) {
            console.error('消息发送错误:', error);
            throw error;
        }
    },

    /**
     * 发送消息，带重试机制
     */
    async sendMessageWithRetry(params: SendMessageParams, maxRetries = 3): Promise<AxiosResponse> {
        // 参数验证
        if (!params.model) {
            const error = new Error('未指定模型参数');
            console.error('发送消息失败:', error);
            throw error;
        }

        // 确保消息列表不为空
        if (!params.messages || !Array.isArray(params.messages) || params.messages.length === 0) {
            const error = new Error('消息列表不能为空');
            console.error('发送消息失败:', error);
            throw error;
        }

        // 格式化消息
        const formattedMessages = formatMessages(params.messages);

        // 格式化后的消息列表不能为空
        if (formattedMessages.length === 0) {
            const error = new Error('格式化后的消息列表为空，无法发送请求');
            console.error('发送消息失败:', error);
            throw error;
        }

        let retries = 0;
        let lastError = null;

        while (retries < maxRetries) {
            try {
                const formattedParams = {
                    ...params,
                    messages: formattedMessages
                };

                console.log(`发送聊天请求 (尝试 ${retries + 1}/${maxRetries}):`, {
                    model: formattedParams.model,
                    messageCount: formattedParams.messages.length
                });

                const response = await api.post('/ai/chat', formattedParams);

                // 验证响应结构
                if (response.data) {
                    // 优先使用content字段，其次使用message.content结构
                    if (!response.data.content && response.data.message?.content) {
                        response.data.content = response.data.message.content;
                    }

                    // 如果仍然没有content，记录响应并标记为错误
                    if (!response.data.content) {
                        console.error('响应中缺少content字段', response.data);
                        throw new Error('响应格式异常：缺少内容');
                    }
                }

                return response;
            } catch (error) {
                lastError = error;

                // 记录详细错误信息
                if (axios.isAxiosError(error) && error.response) {
                    const statusCode = error.response.status;
                    const data = error.response.data;

                    // 特别处理422错误，详细记录错误信息
                    if (statusCode === 422) {
                        console.error('请求参数验证失败 (422错误):', {
                            status: statusCode,
                            data: data,
                            params: {
                                model: params.model,
                                messageCount: params.messages?.length || 0,
                                messagesPreview: params.messages?.slice(0, 2).map(m => ({ role: m.role, contentLength: m.content?.length || 0 }))
                            }
                        });

                        // 如果是参数验证错误，不再重试
                        throw error;
                    }

                    console.error(`请求失败 (尝试 ${retries + 1}/${maxRetries}):`, {
                        status: statusCode,
                        data: data
                    });
                } else {
                    console.error(`请求失败 (尝试 ${retries + 1}/${maxRetries}):`, error);
                }

                // 网络错误或服务器错误才重试
                if (!axios.isAxiosError(error) || !error.response || error.response.status >= 500) {
                    retries++;
                    if (retries < maxRetries) {
                        // 延迟重试，随重试次数增加等待时间
                        const delay = 1000 * retries;
                        console.log(`等待 ${delay}ms 后重试...`);
                        await new Promise(resolve => setTimeout(resolve, delay));
                        continue;
                    }
                }

                throw error;
            }
        }

        throw lastError;
    }
}; 