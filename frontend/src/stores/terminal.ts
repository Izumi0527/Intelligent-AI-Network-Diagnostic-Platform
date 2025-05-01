import { defineStore } from 'pinia';
import { terminalService } from '@/utils/terminalService';

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

            this.connectionStatus = 'connecting';
            this.terminalOutput.push(`正在连接到 ${this.deviceAddress}...`);

            try {
                const response = await terminalService.connect({
                    type: this.connectionType,
                    address: this.deviceAddress,
                    port: this.port || (this.connectionType === 'ssh' ? '22' : '23'),
                    username: this.username,
                    password: this.password
                });

                if (response.data.success) {
                    this.connectionStatus = 'connected';
                    this.terminalOutput.push(`成功连接到 ${this.deviceAddress}`);
                    this.terminalOutput.push(response.data.welcome || '');
                } else {
                    this.connectionStatus = 'error';
                    this.terminalOutput.push(`连接失败: ${response.data.error || '未知错误'}`);
                }
            } catch (error: any) {
                this.connectionStatus = 'error';
                this.terminalOutput.push(`连接错误: ${error.message || '未知错误'}`);
                console.error('连接错误:', error);
            }
        },

        async disconnect() {
            if (this.connectionStatus !== 'connected') {
                return;
            }

            try {
                await terminalService.disconnect();
                this.terminalOutput.push(`已断开与 ${this.deviceAddress} 的连接`);
            } catch (error: any) {
                this.terminalOutput.push(`断开连接时发生错误: ${error.message || '未知错误'}`);
                console.error('断开连接错误:', error);
            } finally {
                this.connectionStatus = 'disconnected';
            }
        },

        async executeCommand(command: string) {
            if (this.connectionStatus !== 'connected') {
                this.terminalOutput.push('错误: 未连接到设备');
                return;
            }

            // 添加到命令历史记录
            this.commandHistory.push(command);
            if (this.commandHistory.length > 50) {
                this.commandHistory.shift(); // 保持历史记录不超过50条
            }
            this.historyIndex = this.commandHistory.length;

            // 在输出中回显命令
            this.terminalOutput.push(`> ${command}`);

            try {
                const response = await terminalService.execute(command);

                if (response.data.success) {
                    const output = response.data.output || '';
                    // 处理多行输出
                    const lines = output.split('\n');
                    for (const line of lines) {
                        this.terminalOutput.push(line);
                    }
                } else {
                    this.terminalOutput.push(`执行命令失败: ${response.data.error || '未知错误'}`);
                }
            } catch (error: any) {
                this.terminalOutput.push(`执行命令出错: ${error.message || '未知错误'}`);
                console.error('执行命令错误:', error);
            }

            // 如果输出行数太多，裁剪一些旧的行
            if (this.terminalOutput.length > 1000) {
                this.terminalOutput = this.terminalOutput.slice(-1000);
            }
        },

        clearTerminal() {
            this.terminalOutput = [];
        },

        // 浏览命令历史记录的方法
        getPreviousCommand() {
            if (this.historyIndex > 0) {
                this.historyIndex--;
                return this.commandHistory[this.historyIndex];
            }
            return '';
        },

        getNextCommand() {
            if (this.historyIndex < this.commandHistory.length - 1) {
                this.historyIndex++;
                return this.commandHistory[this.historyIndex];
            }
            this.historyIndex = this.commandHistory.length;
            return '';
        }
    }
}); 