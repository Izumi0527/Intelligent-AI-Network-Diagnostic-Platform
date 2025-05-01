# AI智能网络故障分析平台

本项目是一个结合AI与网络管理的智能平台，用于连接网络设备并提供AI辅助的故障分析功能。系统支持多种大语言模型（Claude、GPT、Deepseek等）进行智能分析，提供流式响应界面，实现实时网络设备连接和命令执行。

## 项目结构

项目由前端和后端两部分组成：

```
project/
├── frontend/           # Vue 3 + TypeScript前端应用
│   ├── src/            # 源代码目录
│   │   ├── components/ # 组件
│   │   │   ├── ai-assistant/ # AI助手相关组件
│   │   │   ├── terminal/     # 终端相关组件
│   │   │   └── common/       # 通用组件（包含icons等）
│   │   ├── assets/     # 静态资源
│   │   ├── composables/ # 可组合函数
│   │   ├── layouts/    # 布局组件
│   │   ├── stores/     # Pinia状态管理
│   │   ├── utils/      # 工具函数
│   │   ├── types/      # TypeScript类型定义
│   │   ├── views/      # 页面视图组件
│   │   ├── App.vue     # 应用主组件
│   │   └── main.ts     # 应用入口
│   ├── public/         # 公共静态资源
│   ├── lib/            # 第三方库
│   ├── vite.config.ts  # Vite配置
│   ├── tailwind.config.js # Tailwind配置
│   ├── package.json    # 前端依赖配置
│   └── index.html      # HTML入口
└── backend/            # FastAPI后端应用
    ├── app/            # 主应用目录
    │   ├── api/        # API路由
    │   │   └── api_v1/ # V1版本API
    │   │       └── endpoints/ # API端点
    │   │           ├── ai.py        # AI助手相关接口
    │   │           ├── health.py    # 健康检查接口
    │   │           ├── network.py   # 网络设备连接接口
    │   │           └── terminal.py  # 终端会话管理接口
    │   ├── services/   # 业务服务层
    │   ├── models/     # 数据模型
    │   ├── core/       # 核心功能
    │   ├── utils/      # 工具函数
    │   ├── config/     # 配置
    │   ├── main.py     # 应用主入口
    │   └── config.py   # 主配置文件
    ├── run.py          # 启动脚本
    └── requirements.txt # 后端依赖配置
```

## 功能特点

- **网络连接**：支持SSH和Telnet协议连接到各种网络设备
- **命令执行**：远程执行网络命令并获取结果
- **AI分析**：支持多种大型语言模型进行智能故障分析
  - Claude (Anthropic)
  - GPT (OpenAI)
  - Deepseek
- **流式响应**：AI回复实时流式显示
- **多主题**：响应式设计，支持明暗主题切换
- **终端会话**：支持多终端会话管理和超时控制
- **安全认证**：JWT认证系统保障安全访问

## 技术栈

### 前端

- **框架**：Vue 3.3+ + TypeScript 5.2+
- **UI**：Inspira UI + TailwindCSS 3.3+
- **状态管理**：Pinia 2.1+
- **构建工具**：Vite 5.0+
- **HTTP客户端**：Axios 1.6+
- **工具库**：
  - VueUse 10.7+
  - clsx 2.0+
  - tailwind-merge 2.0+
  - class-variance-authority 0.7+
  - tailwindcss-animate 1.0+

### 后端

- **框架**：FastAPI 0.104+ + Pydantic 2.4+
- **服务器**：Uvicorn 0.23+
- **网络工具**：
  - Paramiko 3.3+ (SSH连接)
  - Netmiko 4.2+ (网络设备连接)
- **AI集成**：
  - Anthropic API (Claude)
  - OpenAI API (GPT)
  - Deepseek API
- **异步处理**：
  - aiohttp 3.8+
  - sse-starlette 1.6+ (服务器发送事件)
- **HTTP客户端**：
  - aiohttp 3.8+
  - httpx 0.24+
  - requests 2.31+
- **安全**：
  - python-jose 3.3+ (JWT)
  - passlib 1.7+ (密码)
  - bcrypt 4.0+
- **环境配置**：python-dotenv 1.0+

## 快速开始

### 后端

```bash
cd backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
.\venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置.env文件
cp .env.example .env
# 编辑.env文件，设置API密钥等

# 启动服务器
python run.py
```

### 前端

```bash
cd frontend

# 安装依赖
npm install

# 开发模式启动
npm run dev

# 构建生产版本
npm run build
```

## 环境变量配置

后端支持以下主要环境变量：

- `APP_ENV`: 应用环境 (development/production)
- `AI_ENABLED`: 是否启用AI功能
- `ANTHROPIC_API_KEY`: Claude API密钥
- `CLAUDE_MODEL_VERSION`: Claude模型版本
- `OPENAI_API_KEY`: OpenAI API密钥
- `DEEPSEEK_API_KEY`: Deepseek API密钥
- `SECRET_KEY`: 应用密钥
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`: JWT令牌过期时间
- `MAX_TERMINAL_SESSIONS`: 最大终端会话数
- `SESSION_IDLE_TIMEOUT`: 会话闲置超时时间(秒)
- `HOST`: 监听主机地址（默认: 0.0.0.0）
- `PORT`: 监听端口（默认: 8000）
- `LOG_LEVEL`: 日志级别

## 访问应用

- 前端：默认运行在 http://localhost:5173
- 后端API：默认运行在 http://localhost:8000
- API文档：http://localhost:8000/api/v1/docs

## 项目接口

主要API端点包括：

- `/api/v1/health`: 健康检查
- `/api/v1/network`: 网络设备连接接口
- `/api/v1/terminal`: 终端会话管理
- `/api/v1/ai`: AI助手接口

## 开发说明

### 后端开发

后端使用FastAPI框架，采用RESTful API设计风格。主要文件包括：
- `app/main.py`: 应用主入口，包含FastAPI实例创建和中间件配置
- `app/api/api_v1/endpoints/`: 包含所有API端点处理函数
- `run.py`: 服务器启动脚本，处理命令行参数和环境变量

### 前端开发

前端使用Vue 3的组合式API和基于TypeScript的类型系统。主要包括：
- 基于Pinia的状态管理
- 响应式布局设计，支持多种设备
- 组件化结构，便于维护和扩展

## 许可证

[MIT](LICENSE) 