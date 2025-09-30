import { defineStore } from 'pinia';
import { terminalService } from '@/utils/terminalService';
import type { TimeoutRef } from '@/types';
import { extractErrorMessage } from '@/utils/helpers';

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';
type ConnectionType = 'ssh' | 'telnet';

export const useTerminalStore = defineStore('terminal', {
    state: () => ({
        connectionStatus: 'disconnected' as ConnectionStatus,
        connectionType: 'ssh' as ConnectionType,
        deviceAddress: '',
        port: '',
        username: '',
        password: '',
        terminalOutput: [] as string[],
        commandHistory: [] as string[],
        historyIndex: -1,
        sessionId: null as string | null,
        connectionStartTime: 0,
        connectionTimeoutRef: null as TimeoutRef,
        canCancelConnection: false,
    }),

    getters: {
        isConnected: (state) => state.connectionStatus === 'connected',
        isConnecting: (state) => state.connectionStatus === 'connecting',
        connectionError: (state) => state.connectionStatus === 'error',
    },

    actions: {
        async connectToDevice() {
            if (this.connectionStatus === 'connected') {
                // 如果已经连接，则断开连接
                return this.disconnect();
            }

            if (!this.deviceAddress) {
                this.terminalOutput.push('错误: 设备地址不能为空');
                this.connectionStatus = 'error';
                return;
            }

            // 重置状态
            this.connectionStatus = 'connecting';
            this.connectionStartTime = Date.now();
            this.canCancelConnection = true;
            this.terminalOutput.push(`正在连接到 ${this.deviceAddress}...`);
            this.terminalOutput.push('请耐心等待，网络设备连接可能需要较长时间（最多4分钟）...');
            this.terminalOutput.push('提示: 可以点击"取消连接"按钮终止连接过程');
            
            // 设置一个定时器，在连接期间提供状态更新
            const connectionTimer = setInterval(() => {
                if (this.connectionStatus !== 'connecting') {
                    clearInterval(connectionTimer);
                    return;
                }
                
                const elapsedSeconds = Math.floor((Date.now() - this.connectionStartTime) / 1000);
                
                // 根据等待时间添加不同的提示信息
                if (elapsedSeconds === 30) {
                    this.terminalOutput.push(`连接仍在进行中，已等待 ${elapsedSeconds} 秒...`);
                    this.terminalOutput.push('连接网络设备可能需要较长时间，特别是首次连接...');
                } else if (elapsedSeconds === 60) {
                    this.terminalOutput.push(`连接仍在进行中，已等待 ${elapsedSeconds} 秒...`);
                    this.terminalOutput.push('提示: 某些网络设备响应较慢，正在尝试建立连接...');
                } else if (elapsedSeconds === 120) {
                    this.terminalOutput.push(`连接仍在进行中，已等待 ${elapsedSeconds} 秒...`);
                    this.terminalOutput.push('提示: 长时间无响应可能是网络问题或设备配置问题...');
                } else if (elapsedSeconds % 30 === 0) {
                    this.terminalOutput.push(`连接仍在进行中，已等待 ${elapsedSeconds} 秒...`);
                }
            }, 1000);

            try {
                const response = await terminalService.connect({
                    type: this.connectionType,
                    address: this.deviceAddress,
                    port: this.port || (this.connectionType === 'ssh' ? '22' : '23'),
                    username: this.username,
                    password: this.password
                });

                clearInterval(connectionTimer);
                this.canCancelConnection = false;
                
                const data = response.data;
                if (data.success) {
                    this.sessionId = data.session_id;
                    this.connectionStatus = 'connected';
                    const connTime = Math.floor((Date.now() - this.connectionStartTime) / 1000);
                    this.terminalOutput.push(`成功连接到 ${this.deviceAddress}（用时: ${connTime}秒）`);
                    if (data.device_info) {
                        this.terminalOutput.push(data.device_info);
                    }
                } else {
                    this.connectionStatus = 'error';
                    this.terminalOutput.push(`连接失败: ${data.message || '未知错误'}`);
                }
            } catch (error: unknown) {
                clearInterval(connectionTimer);
                this.connectionStatus = 'error';
                this.canCancelConnection = false;
                
                const errorMessage = error instanceof Error ? error.message : String(error);
                if (errorMessage && errorMessage.includes('timeout')) {
                    this.terminalOutput.push(`连接超时: 请检查设备地址和端口是否正确，或者设备是否响应缓慢`);
                    this.terminalOutput.push(`建议: 请确认设备可访问性，或稍后重试`);
                } else if (errorMessage && errorMessage.includes('Network Error')) {
                    this.terminalOutput.push(`网络错误: 无法连接到服务器或设备`);
                    this.terminalOutput.push(`建议: 请检查网络连接和防火墙设置`);
                } else {
                    this.terminalOutput.push(`连接错误: ${errorMessage || '未知错误'}`);
                }
                console.error('连接错误:', error);
            }
        },

        async cancelConnection() {
            if (this.connectionStatus !== 'connecting') {
                return;
            }

            try {
                // 调用取消API
                await terminalService.cancelConnection();
                this.terminalOutput.push('已取消连接尝试');
            } catch (error: unknown) {
                console.error('取消连接出错:', error);
            } finally {
                this.connectionStatus = 'disconnected';
                this.canCancelConnection = false;
            }
        },

        async disconnect() {
            if (this.connectionStatus !== 'connected' || !this.sessionId) {
                return;
            }

            try {
                await terminalService.disconnect(this.sessionId);
                this.terminalOutput.push(`已断开与 ${this.deviceAddress} 的连接`);
            } catch (error: unknown) {
                this.terminalOutput.push(`断开连接时发生错误: ${extractErrorMessage(error)}`);
                console.error('断开连接错误:', error);
            } finally {
                this.connectionStatus = 'disconnected';
                this.sessionId = null;
            }
        },

        async executeCommand(cmd: string) {
            if (!this.sessionId || this.connectionStatus !== 'connected') {
                return;
            }

            // 添加到命令历史
            this.commandHistory.unshift(cmd);
            if (this.commandHistory.length > 50) {
                this.commandHistory.pop();
            }
            this.historyIndex = -1;

            // 在终端显示命令
            this.terminalOutput.push(`>${cmd}`);

            try {
                const response = await terminalService.execute(this.sessionId, cmd);
                const data = response.data;
                
                if (data.is_error) {
                    this.terminalOutput.push(`错误: ${data.output}`);
                    
                    // 如果是会话失效错误，更新连接状态
                    if (data.output.includes('会话不存在') || data.output.includes('已过期')) {
                        this.connectionStatus = 'disconnected';
                        this.sessionId = null;
                        this.terminalOutput.push('会话已断开，请重新连接');
                    }
                } else {
                    // 分割输出并添加到终端
                    const outputLines = data.output.split('\n');
                    for (const line of outputLines) {
                        if (line.trim()) {
                            this.terminalOutput.push(this.stripAnsiCodes(line));
                        }
                    }
                }
            } catch (error: unknown) {
                this.terminalOutput.push(`执行命令错误: ${extractErrorMessage(error)}`);
                console.error('执行命令错误:', error);
            }
        },

        getPreviousCommand() {
            if (this.commandHistory.length === 0) {
                return '';
            }
            
            this.historyIndex = Math.min(this.historyIndex + 1, this.commandHistory.length - 1);
            return this.commandHistory[this.historyIndex];
        },

        getNextCommand() {
            if (this.historyIndex <= 0) {
                this.historyIndex = -1;
                return '';
            }
            
            this.historyIndex--;
            return this.commandHistory[this.historyIndex];
        },

        clearTerminal() {
            this.terminalOutput = [];
        },
        
        // 移除ANSI控制码的辅助方法
        stripAnsiCodes(text: string): string {
            // 移除ANSI转义序列
            return text.replace(/\u001b\[\d{1,2}m/g, '')
                      .replace(/\u001b\[K/g, '')
                      .replace(/\u001b\[\d+;\d+H/g, '')
                      .replace(/\u001b\[\??\d+[hl]/g, '')
                      .replace(/\u001b\[\d+[ABCD]/g, '');
        }
    }
}); 