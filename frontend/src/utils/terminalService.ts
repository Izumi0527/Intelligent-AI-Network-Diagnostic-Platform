import axios from 'axios';

const api = axios.create({
    baseURL: '/api',
    timeout: 30000,
});

export interface TerminalConnectParams {
    type: string;
    address: string;
    port: string;
    username: string;
    password: string;
}

export const terminalService = {
    async connect(params: TerminalConnectParams) {
        return api.post('/terminal/connect', params);
    },

    async execute(command: string) {
        return api.post('/terminal/execute', { command });
    },

    async disconnect() {
        return api.post('/terminal/disconnect');
    }
}; 