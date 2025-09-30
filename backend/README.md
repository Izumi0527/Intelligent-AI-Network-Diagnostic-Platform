# AI智能网络故障分析平台 - 后端

本项目是AI智能网络故障分析平台的后端服务，基于Python FastAPI框架开发，为前端提供SSH/Telnet连接和AI模型集成功能。

## 功能特点

- **设备连接**：通过SSH和Telnet协议安全连接到网络设备
- **命令执行**：远程执行命令并返回结果
- **AI集成**：与Claude 3.7等大型语言模型集成，提供智能故障分析
- **流式响应**：支持AI模型的流式响应
- **WebSocket支持**：为终端交互提供实时通信能力
- **安全性**：加密存储凭证，防止敏感信息泄露
- **高性能Telnet连接**：优化的Telnet连接机制，大幅减少网络设备连接时间

## 项目结构

```
backend/
│
├── app/                    # 应用主目录
│   ├── __init__.py
│   ├── main.py             # 应用入口点
│   ├── config.py           # 配置管理
│   ├── api/                # API路由
│   │   ├── __init__.py
│   │   ├── terminal.py     # 终端连接API
│   │   ├── ai.py           # AI助手API
│   │   └── health.py       # 健康检查API
│   │
│   ├── core/               # 核心功能
│   │   ├── __init__.py
│   │   ├── ssh.py          # SSH连接实现
│   │   ├── telnet.py       # 优化的Telnet连接实现
│   │   └── security.py     # 安全相关功能
│   │
│   ├── models/             # 数据模型
│   │   ├── __init__.py
│   │   └── terminal.py     # 终端相关模型
│   │
│   ├── services/           # 业务逻辑服务
│   │   ├── __init__.py
│   │   ├── terminal.py     # 终端服务
│   │   └── ai_service.py   # AI助手服务
│   │
│   └── utils/              # 工具函数
│       ├── __init__.py
│       └── logger.py       # 日志工具
│
├── tests/                  # 测试目录
│   ├── __init__.py
│   ├── test_terminal.py
│   └── test_ai.py
│
├── .env.example            # 环境变量示例
├── .gitignore              # Git忽略文件
├── requirements.txt        # 依赖管理
├── setup.py                # 项目安装脚本
└── README.md               # 项目文档
```

## API 端点

### 健康检查
- `GET /api/health` - 检查服务健康状态

### 终端相关
- `POST /api/terminal/connect` - 连接到远程设备
- `POST /api/terminal/disconnect` - 断开设备连接
- `POST /api/terminal/execute` - 执行命令
- `WebSocket /api/terminal/ws/{session_id}` - 终端WebSocket连接

### AI助手相关
- `GET /ai/models` - 获取可用的AI模型列表
- `GET /ai/check-connection` - 检查AI模型连接状态
- `POST /ai/chat` - 发送消息到AI模型
- `WebSocket /ai/stream-chat` - 流式AI对话

## 安装和启动

### 环境要求
- Python 3.10+
- 虚拟环境工具 (推荐使用venv或conda)

### 安装步骤

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
.\venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑.env文件，设置必要的环境变量

# 启动服务
uvicorn app.main:app --reload
```

服务将在 `http://localhost:8000` 上运行，API文档可在 `http://localhost:8000/docs` 访问。

## 关键依赖

- FastAPI - Web框架
- Pydantic - 数据验证和设置管理
- Paramiko - SSH客户端实现
- Socket - 底层Socket实现
- concurrent.futures - 并发处理
- Anthropic - Claude API客户端
- Websockets - WebSocket支持
- Pytest - 测试框架

## 安全注意事项

- 所有敏感信息（如密码、API密钥）应存储在环境变量中
- SSH/Telnet密码不应明文存储
- 确保使用HTTPS和适当的身份验证机制
- 对AI请求和响应进行适当的过滤和安全检查

## Telnet连接优化

为解决网络设备Telnet连接时间过长的问题，我们实施了多轮优化方案：

### 第一轮优化
- 前端超时设置从60秒增加到150秒
- 增加取消连接功能，提升用户控制体验
- 优化连接检查机制

### 第二轮深度优化
- **并行连接策略**：同时尝试多种连接方法，采用最快成功的一个
- **直接Socket控制**：绕过telnetlib的部分限制
- **非阻塞操作**：使用非阻塞Socket操作和更激进的超时设置
- **线程池执行器**：处理并发连接尝试
- **快速网络可达性检测**：优先识别不可连接的目标
- **认证过程优化**：减少认证等待时间
- **改进错误处理**：更精确的错误反馈机制

这些优化显著减少了设备连接时间，提高了连接成功率和用户体验。

## 开发指南

### 添加新API端点

1. 在`app/api/`目录下创建路由
2. 在`app/main.py`中注册路由
3. 更新API文档

### 运行测试

```bash
pytest
```

### 构建和部署

```bash
# 构建项目
pip install -e .

# 生产环境启动
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 开发状态

目前已完成的组件:

- [x] 基础框架搭建 - FastAPI应用设置
- [x] 配置管理 - 环境变量和设置
- [x] 核心终端功能 - SSH和Telnet连接
- [x] AI服务集成 - Claude和GPT模型支持
- [x] API端点 - 健康检查、AI和网络终端
- [x] 工具类 - 日志和安全工具
- [x] 连接性能优化 - Telnet连接速度大幅提升
- [x] 用户体验改进 - 连接取消功能和状态提示
- [x] 错误处理和异常管理

待完成的组件:

- [ ] 前端集成测试
- [ ] WebSocket实时终端支持
- [ ] 用户认证和会话管理
- [ ] 监控和性能分析
- [ ] 容器化部署配置 