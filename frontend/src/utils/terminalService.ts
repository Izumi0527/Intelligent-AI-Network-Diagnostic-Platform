import axios, { AxiosHeaders } from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

const internalApiToken = import.meta.env.VITE_INTERNAL_API_TOKEN as string | undefined;

api.interceptors.request.use((config) => {
  if (!internalApiToken) {
    return config;
  }

  config.headers = AxiosHeaders.from(config.headers);
  config.headers.set('Authorization', `Bearer ${internalApiToken}`);

  return config;
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
    return api.post('/terminal/connect', {
      connection_type: params.type,
      device_address: params.address,
      port: parseInt(params.port) || (params.type === 'ssh' ? 22 : 23),
      username: params.username,
      password: params.password
    }, {
      timeout: 240000  // 增加到4分钟
    });
  },

  async execute(sessionId: string, command: string) {
    return api.post('/terminal/execute', {
      session_id: sessionId,
      command: command
    });
  },

  async disconnect(sessionId: string) {
    return api.post('/terminal/disconnect', {
      session_id: sessionId
    });
  },

  // 新增: 检查连接状态
  async checkConnectionStatus(sessionId: string) {
    return api.get(`/terminal/sessions/${sessionId}`);
  },

  // 新增: 取消正在进行的连接
  async cancelConnection() {
    return api.post('/terminal/cancel-connect');
  }
};
