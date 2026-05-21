# AI智能网络故障分析平台架构与系统信息总览

## 文档生成边界

本文档基于项目代码、配置文件、依赖清单、启动脚本与测试文件扫描生成，未读取项目内任何既有 Markdown 文档内容。

本文档覆盖范围：

- 项目定位与核心能力
- 前后端技术栈
- 目录结构与模块职责
- 后端启动链路、API、服务层、模型层、网络连接层、日志与安全
- 前端启动链路、布局、状态管理、接口客户端与关键组件
- AI 大模型接入架构
- SSH、Telnet、Netmiko 三类网络交互路径
- 配置项、环境变量、脚本、测试与质量保障
- 当前代码中可见的风险、疑点与后续演进建议

## 1. 项目定位

本项目是一个前后端分离的 AI 智能网络故障分析平台。平台面向网络运维场景，核心目标是把网络设备终端操作与 AI 辅助分析放在同一工作台中，使用户可以连接交换机、路由器、防火墙等网络设备，执行排障命令，并将日志、配置片段或故障现象交给大模型分析。

当前系统具备以下核心能力：

- 网络设备终端连接：支持 SSH 与 Telnet。
- 终端命令执行：支持会话保持、命令历史、输出清洗、基础分页处理。
- AI 对话助手：支持模型列表加载、模型连通性检查、普通响应和流式响应。
- 多模型厂商接入：OpenAI、Anthropic Claude、DeepSeek。
- DeepSeek 专项网络日志分析：提供日志类型识别、错误分析、性能分析、安全分析等封装。
- 服务健康检查：提供后端健康状态、AI 服务状态、网络服务状态与连接统计。
- 日志系统：控制台彩色日志、文件轮转日志、访问日志、错误日志。
- 脚本化启动：提供 Windows PowerShell 与类 Unix Shell 的开发、生产统一启动脚本。

## 2. 总体架构

系统采用典型的前后端分离架构：

```text
浏览器
  |
  | Vue 3 + Pinia + Axios
  v
前端开发服务器 Vite
  |
  | /api 代理重写为 /api/v1
  v
FastAPI 后端
  |
  |-- AI 服务管理器
  |     |-- OpenAI Provider
  |     |-- Claude Provider
  |     |-- DeepSeek Provider
  |     `-- DeepSeek 网络日志分析封装
  |
  |-- 网络连接服务
  |     `-- Netmiko 通用 SSH/Telnet 连接
  |
  |-- 终端会话服务
  |     |-- Paramiko SSH 持久 Shell
  |     `-- Telnetlib Telnet 连接
  |
  `-- 日志、安全、配置、健康检查
```

后端真实 API 前缀为 `/api/v1`。前端在开发期通过 Vite 代理使用 `/api` 作为浏览器侧统一入口，并将其改写到后端 `/api/v1`。

## 3. 技术栈

### 3.1 后端技术栈

后端位于 `backend/`，主要技术栈如下：

- Python：要求 Python 3.9 及以上。
- Web 框架：FastAPI。
- ASGI 服务：Uvicorn。
- 数据校验：Pydantic 与 pydantic-settings。
- 配置加载：python-dotenv。
- AI HTTP 客户端：aiohttp、httpx、requests。
- 网络设备连接：
  - Netmiko：通用网络设备连接路径。
  - Paramiko：SSH 终端会话路径。
  - telnetlib：Telnet 终端会话路径。
- 认证与安全工具：
  - python-jose：JWT。
  - passlib、bcrypt：密码哈希。
- 测试工具：pytest、pytest-asyncio、pytest-cov。
- 代码质量工具：black、ruff、mypy。

### 3.2 前端技术栈

前端位于 `frontend/`，主要技术栈如下：

- Vue 3。
- TypeScript。
- Pinia 状态管理。
- Vite 构建与开发服务器。
- Axios HTTP 客户端。
- marked：AI Markdown 内容渲染。
- Tailwind CSS 相关工具链。
- Vue TSC 与 ESLint：类型检查和静态检查。

## 4. 顶层目录结构

项目当前主要目录职责如下：

```text
Project3/
  backend/        后端 FastAPI 应用、服务、模型、配置和运行入口
  frontend/       前端 Vue 应用、组件、状态管理和接口客户端
  scripts/        开发、生产启动脚本和维护脚本
  tests/          根目录测试集
  docs/           项目文档
  logs/           运行日志目录
  discuss/        讨论或规划资料目录
```

当前测试目录已经位于项目根目录 `tests/`，后端 `pyproject.toml` 的 pytest 配置使用 `../tests` 作为测试发现目录。

## 5. 后端架构

### 5.1 后端启动链路

后端主入口为 `backend/run.py`。

启动链路如下：

1. 计算后端目录。
2. 加载 `backend/.env`。
3. 导入全局 `settings`。
4. 初始化日志管理器。
5. 解析命令行参数：
   - `--host`
   - `--port`
   - `--reload`
6. 调用 Uvicorn 启动 `app.main:app`。

需要注意：`run.py` 中存在 `check_environment()` 函数，用于检查 AI API Key 和日志目录，但当前主流程没有调用该函数。

### 5.2 FastAPI 应用入口

FastAPI 应用入口为 `backend/app/main.py`。

应用初始化内容：

- 设置应用标题、版本、描述。
- 配置文档地址：
  - Swagger UI：`${API_V1_STR}/docs`
  - OpenAPI JSON：`${API_V1_STR}/openapi.json`
- 配置 CORS。
- 注册请求日志中间件。
- 挂载 `/api/v1` 路由。
- 注册启动与关闭事件。

启动事件中会创建后台任务，定期清理空闲终端会话。默认每 300 秒执行一次清理检查。

### 5.3 配置系统

主要配置类位于 `backend/app/config/settings.py`。

配置来源：

- 环境变量。
- `backend/.env`。
- `backend/.env.example` 提供示例变量。

关键配置分组：

- 应用基础配置：
  - `APP_ENV`
  - `DEBUG`
  - `API_PREFIX`
  - `APP_NAME`
  - `APP_VERSION`
- 服务监听配置：
  - `HOST`
  - `PORT`
- 跨域配置：
  - `CORS_ORIGINS`
- 安全配置：
  - `SECRET_KEY`
  - `JWT_ALGORITHM`
  - `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`
- AI 服务配置：
  - `AI_ENABLED`
  - `OPENAI_API_KEY`
  - `OPENAI_API_BASE`
  - `ANTHROPIC_API_KEY`
  - `ANTHROPIC_API_BASE`
  - `DEEPSEEK_API_KEY`
  - `DEEPSEEK_API_URL`
  - `OPENAI_MODELS`
  - `CLAUDE_MODELS`
  - `DEEPSEEK_MODELS`
  - 对应模型名称、描述、最大 token 配置
- 终端会话配置：
  - `SESSION_IDLE_TIMEOUT`
  - `MAX_TERMINAL_SESSIONS`
- 日志配置：
  - `LOG_LEVEL`
  - `LOG_FORMAT`

配置校验逻辑在 `model_post_init()` 中执行，会检查基础配置、API 前缀格式、AI 配置完整性，并规范化 `API_V1_STR`。

### 5.4 后端 API 路由

后端统一路由入口为 `backend/app/api/api_v1/api.py`。

当前挂载模块：

- `/ai`
- `/network`
- `/terminal`
- `/health`

### 5.5 AI API

AI 端点位于 `backend/app/api/api_v1/endpoints/ai.py`。

主要接口：

- `GET /api/v1/ai/models`
  - 获取所有可用模型。
  - 会检查各 Provider 连通性。
- `GET /api/v1/ai/models/{model_id}/status`
  - 检查指定模型状态。
- `POST /api/v1/ai/chat`
  - 非流式 AI 对话。
- `POST /api/v1/ai/chat/stream`
  - 流式 AI 对话。
- `POST /api/v1/ai/debug/request-format`
  - 返回请求格式诊断信息。
- `GET /api/v1/ai/deepseek/status`
  - DeepSeek 服务状态。
- `POST /api/v1/ai/deepseek/generate`
  - DeepSeek 文本生成。
- `POST /api/v1/ai/deepseek/analyze-network-log`
  - DeepSeek 网络日志分析。

AI Chat 请求模型主要由 `ChatRequest` 承载，包含模型、消息、最大 token、temperature、top_p、stream 等字段。

### 5.6 Network API

Network 端点位于 `backend/app/api/api_v1/endpoints/network.py`。

主要接口：

- `POST /api/v1/network/connect`
  - 使用 Netmiko 建立网络设备连接。
- `POST /api/v1/network/command`
  - 在指定连接上执行命令。
- `POST /api/v1/network/disconnect`
  - 断开指定连接。
- `GET /api/v1/network/connections`
  - 获取连接列表。
- `GET /api/v1/network/connections/{connection_id}`
  - 获取连接详情。

该模块面向更通用的网络设备连接管理，内部使用 `NetworkService` 与 Netmiko。

### 5.7 Terminal API

Terminal 端点位于 `backend/app/api/api_v1/endpoints/terminal.py`。

主要接口：

- `POST /api/v1/terminal/connect`
  - 建立 SSH 或 Telnet 终端会话。
- `POST /api/v1/terminal/cancel-connect`
  - 返回取消连接成功信息。
- `POST /api/v1/terminal/execute`
  - 在终端会话中执行命令。
- `POST /api/v1/terminal/disconnect`
  - 断开终端会话。
- `GET /api/v1/terminal/sessions`
  - 获取终端会话列表。
- `GET /api/v1/terminal/sessions/{session_id}`
  - 获取单个会话状态。
- `POST /api/v1/terminal/cleanup`
  - 清理空闲会话。

该模块面向前端虚拟终端体验，内部使用 `TerminalService`、`TerminalManager`、`SSHManager`、`TelnetManager`。

### 5.8 Health API

Health 端点位于 `backend/app/api/api_v1/endpoints/health.py`。

主要接口：

- `GET /api/v1/health`

返回信息包括：

- 服务状态。
- AI 服务状态。
- 网络服务状态。
- 当前网络连接数量。
- 可用模型数量。
- 版本信息。

## 6. 后端服务层

### 6.1 依赖注入

依赖注入位于 `backend/app/api/deps.py`。

当前使用模块级单例：

- `AIServiceManager`
- `NetworkService`
- `TerminalService`
- `DeepseekService`

这些服务均为进程内状态。若后续使用多 worker 部署，连接会话、终端会话与单例状态不会自动跨进程共享。

### 6.2 AIServiceManager

AI 服务管理器位于 `backend/app/services/ai/manager.py`。

职责：

- 根据 API Key 初始化 Provider。
- 聚合可用模型。
- 检查模型状态。
- 根据模型前缀路由到对应 Provider。
- 提供统一 `chat()` 与 `chat_stream()` 能力。

模型路由规则：

- `gpt-` 前缀路由到 OpenAI Provider。
- `claude-` 前缀路由到 Claude Provider。
- `deepseek-` 前缀路由到 DeepSeek Provider。
- 若前缀未命中，则遍历 Provider 的模型列表尝试匹配。

### 6.3 Provider 抽象

Provider 抽象位于 `backend/app/services/ai/base.py`。

核心抽象：

- `AIProviderBase`
- `ProviderType`
- 统一请求头构造。
- 统一 aiohttp 会话管理。
- HTTP 错误映射。

当前 Provider：

- `OpenAIProvider`
- `ClaudeProvider`
- `DeepseekProvider`

### 6.4 OpenAI Provider

OpenAI Provider 位于 `backend/app/services/ai/providers/openai_provider.py`。

职责：

- 使用 `OPENAI_API_BASE` 与 `OPENAI_API_KEY`。
- 调用 `/chat/completions`。
- 支持普通响应。
- 支持流式响应。
- 将 OpenAI 格式 chunk 转为内部字符串流。

### 6.5 Claude Provider

Claude Provider 位于 `backend/app/services/ai/providers/claude_provider.py`。

职责：

- 使用 `ANTHROPIC_API_BASE` 与 `ANTHROPIC_API_KEY`。
- 普通对话使用 Claude `/messages` 风格接口。
- 支持 Claude 原生流式事件解析。

当前可见疑点：

- 普通 chat 路径使用 Claude `/messages` 与 `x-api-key`。
- 连通性检查路径使用 `/chat/completions` 与 Bearer Authorization。
- 这两种协议风格不一致，可能导致状态检查与真实对话结果不一致。

### 6.6 DeepSeek Provider

DeepSeek Provider 位于 `backend/app/services/ai/providers/deepseek_provider.py`。

职责：

- 使用 `DEEPSEEK_API_URL` 与 `DEEPSEEK_API_KEY`。
- 调用 `/chat/completions`。
- 使用 httpx AsyncClient。
- 支持普通响应。
- 支持流式响应。
- 支持识别 `reasoning_content` 并转为内部思考事件。
- 连接检查使用当前配置的第一个 DeepSeek 模型。

当前模型配置包括：

- `deepseek-v4-pro`
- `deepseek-v4-flash`

### 6.7 模型配置解析

模型配置解析位于 `backend/app/utils/model_config.py`。

职责：

- 解析 `OPENAI_MODELS`、`CLAUDE_MODELS`、`DEEPSEEK_MODELS`。
- 解析对应模型名称、描述、最大 token。
- 在环境变量缺失或异常时使用内置默认值。
- 根据模型 ID 推导特性标签。

当前内置默认模型包括：

- OpenAI：
  - `gpt-5.5`
  - `gpt-5.4-mini`
- Claude：
  - `claude-opus-4-7`
  - `claude-sonnet-4-6`
  - `claude-haiku-4-5`
- DeepSeek：
  - `deepseek-v4-pro`
  - `deepseek-v4-flash`

### 6.8 DeepSeek 专项服务

DeepSeek 专项服务包括：

- `backend/app/services/deepseek_service.py`
- `backend/app/services/ai/deepseek/client.py`
- `backend/app/services/ai/deepseek/analyzer.py`

职责：

- 提供兼容旧接口的 DeepSeek 服务封装。
- 复用 `AIServiceManager` 中已有 DeepSeek Provider，避免重复初始化。
- 提供普通生成、流式生成、服务状态查询。
- 提供网络日志分析能力。

网络日志分析器支持的分析类型包括：

- 错误日志分析。
- 性能日志分析。
- 安全日志分析。
- 通用网络日志分析。

## 7. 网络连接与终端会话架构

### 7.1 两条连接路径

后端存在两套网络设备交互路径，需要明确区分：

- `NetworkService + Netmiko`
  - 对应 `/network/*` API。
  - 适合通用连接、命令执行、连接列表管理。
- `TerminalService + TerminalManager + SSH/Telnet Manager`
  - 对应 `/terminal/*` API。
  - 适合前端虚拟终端体验、命令历史、会话保持、输出清洗。

这两条路径都能连接网络设备，但状态、连接 ID、会话 ID 与底层库不同。

### 7.2 NetworkService

`NetworkService` 位于 `backend/app/services/network_service.py`。

职责：

- 使用 Netmiko `ConnectHandler` 建立 SSH/Telnet 连接。
- 维护进程内连接字典。
- 使用 `asyncio.Lock` 控制连接表并发访问。
- 使用 `asyncio.to_thread()` 包装阻塞连接与命令执行。
- 存储连接信息时会对密码做脱敏处理。

连接 ID 格式类似 `conn-xxxx`。

### 7.3 TerminalService

`TerminalService` 位于 `backend/app/services/terminal_service.py`。

职责：

- 封装终端连接、命令执行、断开连接、会话查询。
- 限制最大终端会话数量。
- 调用 `TerminalManager` 完成实际连接。
- 提供空闲会话清理。

### 7.4 TerminalManager

`TerminalManager` 位于 `backend/app/core/terminal.py`。

职责：

- 统一管理 SSH 与 Telnet 会话。
- 根据连接类型分发到 `SSHManager` 或 `TelnetManager`。
- 维护会话元数据。
- 定期检查会话活跃状态。
- 清理过期会话。

### 7.5 SSHManager

`SSHManager` 位于 `backend/app/core/ssh.py`。

职责：

- 使用 Paramiko 建立 SSH 连接。
- 使用 `invoke_shell()` 建立持久交互式 Shell。
- 连接前尝试检测常见错误协议，例如 Telnet 或 HTTP。
- 尝试执行 `display version` 获取设备信息。
- 支持命令执行、分页处理、输出清洗。
- 支持 Shell 失效后的重连尝试。
- 会对会话中的设备密码进行内存级加密封装。

SSH 分页能力已统一由 `backend/app/core/ssh.py` 提供，不再保留独立的历史分页实现文件。

### 7.6 TelnetManager

Telnet 实现主要位于：

- `backend/app/core/telnet.py`
- `backend/app/core/network/telnet/manager.py`
- `backend/app/core/network/telnet/connection.py`
- `backend/app/core/network/telnet/devices/huawei.py`
- `backend/app/core/network/telnet/protocols.py`

职责：

- 使用 telnetlib 建立 Telnet 连接。
- 提供通用 Telnet 连接实现。
- 提供 Huawei 设备专用实现。
- 根据设备类型选择连接类。
- 支持登录提示识别、命令执行、分页处理、ANSI 控制符清理。
- 定期清理过期会话。

需要注意：`telnetlib` 在较新的 Python 版本中属于逐步淘汰方向，后续升级 Python 时要关注替代方案。

## 8. 后端模型层

### 8.1 AI 模型

AI 模型定义位于 `backend/app/models/ai.py`。

核心模型：

- `AIModel`
  - `value`
  - `label`
  - `description`
  - `features`
  - `max_tokens`
- `Message`
  - `role`
  - `content`
  - `timestamp`
- `ChatRequest`
  - `model`
  - `messages`
  - `max_tokens`
  - `temperature`
  - `top_p`
  - `stream`
- `ChatResponse`
  - `message`
  - `model`
  - `finish_reason`
  - `usage`
  - `content`
- `StreamEvent`
  - `type`
  - `content`
  - `error`
  - `done`
  - `finish_reason`
  - `thinking`

### 8.2 Network 模型

Network 模型定义位于 `backend/app/models/network.py`。

核心模型：

- `Connection`
- `ConnectionRequest`
- `ConnectionResponse`
- `CommandRequest`
- `CommandResponse`
- `DisconnectRequest`
- `DisconnectResponse`
- `ConnectionsList`
- `NetworkEvent`

### 8.3 Terminal 模型

Terminal 模型定义位于 `backend/app/models/terminal.py`。

核心模型：

- `TerminalCredentials`
- `CommandRequest`
- `CommandResponse`
- `SessionInfo`
- `SessionList`
- `ConnectionResponse`

## 9. 日志与可观测性

日志工具位于 `backend/app/utils/logger.py`。

日志能力：

- 控制台日志。
- 文件日志。
- 访问日志。
- 错误日志。
- JSON 格式或标准格式。
- 日志轮转。
- 日志目录自动创建。
- 旧日志清理。
- 标准控制台日志可对重要级别加颜色。

日志目录结构：

```text
logs/
  app/
  access/
  error/
  backend/
  frontend/
```

当前测试已覆盖：

- 控制台重要日志级别应带 ANSI 颜色。
- 文件日志不应写入 ANSI 转义序列。

## 10. 安全机制

安全工具位于 `backend/app/utils/security.py`。

当前能力：

- bcrypt 密码哈希。
- JWT Token 创建与解析。
- 设备密码内存级封装。

需要注意：

- 设备密码封装使用随机 key 与 XOR 方式，且密文与 key 均保存在内存对象中。
- 该机制更接近防止明文直接暴露的弱混淆，不应视为强加密方案。
- API Key 与设备密码必须继续通过环境变量和请求体传递，不应写入代码或文档。

## 11. 前端架构

### 11.1 前端启动链路

前端入口为 `frontend/src/main.ts`。

启动链路：

1. 创建 Vue 应用。
2. 注册 Pinia。
3. 挂载 `App.vue`。
4. `App.vue` 渲染 `MainLayout`。

### 11.2 页面布局

主布局位于 `frontend/src/layouts/MainLayout.vue`。

布局结构：

- 顶部栏：
  - 平台标题。
  - 后端服务状态指示器。
  - 主题切换控制。
- 主体区域：
  - 左侧：网络终端，占主要宽度。
  - 右侧：AI 智能助手，占辅助宽度。

当前布局默认强制亮色主题，挂载时会移除 `dark` class 并清理本地主题缓存。

### 11.3 Vite 代理

Vite 配置位于 `frontend/vite.config.ts`。

开发代理配置：

- 浏览器请求前缀：`/api`
- 后端目标：`http://localhost:8000`
- 重写规则：`/api` -> `/api/v1`

因此前端代码中 Axios 或 fetch 使用 `/api/health`、`/api/ai/models` 等路径，在开发环境会被代理为后端真实 `/api/v1/health`、`/api/v1/ai/models`。

生产环境如果没有反向代理提供相同重写规则，需要额外配置网关或后端路径映射。

### 11.4 全局应用状态

全局应用状态位于 `frontend/src/stores/app.ts`。

职责：

- 维护服务器连接状态。
- 维护亮色或暗色主题状态。
- 通过 `/api/health` 检查服务器连接。
- 设置 HTML 根节点主题 class。

### 11.5 AI 助手状态

AI 助手状态位于：

- `frontend/src/stores/aiAssistant.ts`
- `frontend/src/stores/ai-assistant/index.ts`
- `frontend/src/stores/ai-assistant/state.ts`
- `frontend/src/stores/ai-assistant/actions/*`
- `frontend/src/stores/ai-assistant/types/index.ts`

职责：

- 当前模型选择。
- 可用模型列表。
- 模型连接状态。
- 流式响应开关。
- AI 回复状态。
- DeepSeek 思考内容状态。
- 对话消息列表。
- 本地会话 ID。
- 模型列表缓存。
- 对话历史保存和加载。

默认选中模型为 `deepseek-v4-pro`。

### 11.6 终端状态

终端状态位于 `frontend/src/stores/terminal.ts`。

职责：

- 连接状态：
  - `disconnected`
  - `connecting`
  - `connected`
  - `error`
- 连接类型：
  - `ssh`
  - `telnet`
- 设备地址、端口、用户名、密码。
- 终端输出。
- 命令历史。
- 当前会话 ID。
- 连接等待计时。
- 取消连接按钮状态。

终端连接等待期间，前端会向终端输出区域持续追加等待提示。

### 11.7 前端 API 客户端

#### AI 客户端

AI 客户端位于 `frontend/src/utils/aiService.ts`。

职责：

- 使用 Axios baseURL `/api`。
- 获取模型列表。
- 检查模型状态。
- 发送普通聊天请求。
- 发送流式聊天请求。
- 解析服务端流式响应。
- 兼容 OpenAI、DeepSeek、Claude 风格的流式片段。
- 将思考内容转换为前端可展示的状态。

#### 终端客户端

终端客户端位于 `frontend/src/utils/terminalService.ts`。

职责：

- 使用 Axios baseURL `/api`。
- 连接终端。
- 执行命令。
- 断开连接。
- 查询连接状态。
- 取消连接。

终端连接接口超时时间为 240 秒，以适配网络设备首次连接较慢的情况。

### 11.8 前端关键组件

#### NetworkTerminal

位置：`frontend/src/components/terminal/NetworkTerminal.vue`

职责：

- 提供 SSH/Telnet 连接表单。
- 输入设备地址、端口、用户名、密码。
- 展示连接状态诊断。
- 展示终端输出。
- 执行命令。
- 支持上下键浏览历史命令。
- 支持取消连接。
- 对错误、成功、警告、命令行输出做不同样式展示。

#### AIAssistant

位置：`frontend/src/components/ai-assistant/AIAssistant.vue`

职责：

- 加载模型列表。
- 检查模型连接。
- 切换模型。
- 切换流式响应。
- 发送消息。
- 清空对话。
- 展示 AI 消息和用户消息。
- 处理快捷键。

#### ChatMessages

位置：`frontend/src/components/ai-assistant/components/ChatMessages.vue`

职责：

- 展示用户消息与 AI 消息。
- 使用 marked 渲染 AI Markdown 内容。
- 展示 DeepSeek 思考过程。
- 展示 AI 正在输入、正在思考、正在接收流式内容等状态。
- 自动滚动到底部。

#### ServerStatusIndicator

位置：`frontend/src/components/common/ServerStatusIndicator.vue`

职责：

- 每 30 秒检查一次后端连接。
- 展示服务器已连接或未连接状态。

## 12. 关键业务数据流

### 12.1 AI 模型列表加载

```text
AIAssistant onMounted
  -> aiAssistantStore.loadAvailableModels()
  -> aiService.getAvailableModels()
  -> GET /api/ai/models
  -> Vite 代理重写为 /api/v1/ai/models
  -> AIServiceManager.get_models_response()
  -> 聚合 Provider 模型与状态
  -> 前端写入 availableModels
  -> localStorage 缓存 ai_available_models
```

### 12.2 AI 非流式对话

```text
用户输入消息
  -> aiAssistantStore.sendMessage()
  -> sendMessageRegular()
  -> aiService.sendMessageWithRetry()
  -> POST /api/ai/chat
  -> Vite 代理重写为 /api/v1/ai/chat
  -> AIServiceManager.chat()
  -> 根据模型路由 Provider
  -> Provider 调用外部模型接口
  -> ChatResponse 返回前端
  -> 前端追加 assistant 消息
  -> localStorage 保存会话
```

### 12.3 AI 流式对话

```text
用户输入消息
  -> aiAssistantStore.sendMessage()
  -> sendMessageStream()
  -> aiService.sendMessageStream()
  -> POST /api/ai/chat/stream
  -> Vite 代理重写为 /api/v1/ai/chat/stream
  -> AIServiceManager.chat_stream()
  -> Provider 流式请求外部模型接口
  -> 后端 StreamingResponse 输出内容
  -> 前端解析 chunk、SSE data 行与思考内容
  -> ChatMessages 实时展示回复和思考过程
```

### 12.4 终端连接

```text
用户填写连接信息
  -> terminalStore.connectToDevice()
  -> terminalService.connect()
  -> POST /api/terminal/connect
  -> Vite 代理重写为 /api/v1/terminal/connect
  -> TerminalService.connect()
  -> TerminalManager.connect()
  -> SSHManager 或 TelnetManager 建立会话
  -> 返回 session_id 与设备信息
  -> 前端进入 connected 状态
```

### 12.5 终端命令执行

```text
用户输入命令
  -> terminalStore.executeCommand()
  -> terminalService.execute()
  -> POST /api/terminal/execute
  -> Vite 代理重写为 /api/v1/terminal/execute
  -> TerminalService.execute_command()
  -> TerminalManager.execute_command()
  -> SSH 或 Telnet 会话执行命令
  -> 清洗输出
  -> 前端追加终端输出
```

### 12.6 Netmiko 通用网络命令

```text
外部调用 /network/connect
  -> NetworkService.connect()
  -> Netmiko ConnectHandler
  -> 保存 connection_id
  -> /network/command 使用 connection_id 执行 send_command
  -> /network/disconnect 释放连接
```

## 13. 脚本与运行方式

脚本位于 `scripts/`。

当前主要脚本：

- `dev.ps1`
  - Windows 开发环境启动。
  - 先启动后端。
  - 等待 `/api/v1/health` 健康检查通过。
  - 再启动前端 Vite。
- `prod.ps1`
  - Windows 生产预览启动。
  - 后端使用 production 环境变量。
  - 前端必要时安装依赖并构建。
  - 使用 Vite preview。
- `dev.sh`
  - 类 Unix 开发环境启动。
- `prod.sh`
  - 类 Unix 生产预览启动。
- `clean-python-cache.ps1`
  - Windows 清理 Python 缓存。
- `clean-python-cache.sh`
  - 类 Unix 清理 Python 缓存。

启动脚本共同特点：

- 检查 `backend/` 与 `frontend/` 是否存在。
- 检查 `backend/.env` 是否存在。
- 确保日志目录存在。
- 检查必要命令：
  - `uv`
  - `npm`
  - Shell 版本额外检查 `curl`
- 设置 `PYTHONDONTWRITEBYTECODE=1`，避免运行时生成 Python 字节码缓存。
- 后端先启动，健康检查通过后再启动前端。

## 14. 测试与质量保障

根目录测试位于 `tests/`。

当前 Python 测试：

- `tests/test_logger.py`
  - 验证控制台日志颜色。
  - 验证文件日志不包含 ANSI 转义序列。
- `tests/test_latest_model_config.py`
  - 验证示例环境变量中的模型配置。
  - 验证内置默认模型。
  - 验证 DeepSeek 连接检查使用第一个配置模型。

脚本静态验证：

- `tests/scripts/verify-launch-scripts.ps1`
  - 验证脚本目录保留统一入口。
  - 验证启动顺序、健康检查、Vite 调用方式和 Python 缓存设置。
- `tests/scripts/verify-backend-runtime-dependencies.ps1`
  - 验证后端运行时依赖声明在 `pyproject.toml` 的 `[project].dependencies`。

后端 pytest 配置位于 `backend/pyproject.toml`：

- 测试目录：`../tests`
- 默认覆盖率目标：`app`
- 默认输出：
  - 终端缺失覆盖率。
  - HTML 覆盖率报告。

## 15. 当前可见风险与疑点

以下问题均来自代码、配置和脚本扫描，不代表线上已经发生故障，但建议纳入后续治理。

### 15.1 API 前缀依赖代理重写

前端代码使用 `/api`，后端真实前缀为 `/api/v1`。

开发期由 Vite 代理完成 `/api` 到 `/api/v1` 的重写。生产环境如果直接部署静态资源，必须确保网关或反向代理也提供相同重写，否则接口会出现 404。

### 15.2 Terminal 断开连接参数可能不一致

前端 `terminalService.disconnect()` 通过 JSON Body 发送：

```json
{
  "session_id": "..."
}
```

后端 `POST /terminal/disconnect` 的函数参数是普通 `session_id: str`，未显式声明 Body 模型。FastAPI 默认更可能按 query 参数解析。该处存在前后端参数绑定不一致风险。

### 15.3 取消连接接口当前更像占位实现

前端提供取消连接按钮，并调用 `/terminal/cancel-connect`。

后端当前接口返回成功信息，但没有看到与正在进行连接任务的实际取消逻辑绑定。对于长时间 SSH/Telnet 连接，用户界面可以切回断开状态，但后端阻塞连接任务未必被真正终止。

### 15.4 Claude 连通性检查与真实请求协议不一致

Claude 普通对话使用 `/messages` 与 `x-api-key`，但连接检查使用 `/chat/completions` 与 Bearer Authorization。该差异可能导致模型状态显示失败，而真实对话路径可用，或反过来。

### 15.5 AI 流式前端实现可能不是真正增量

前端 `aiService` 使用 Axios 发送流式请求，并把响应文本包装为 `ReadableStream`。浏览器 Axios 对流式下载的支持与 fetch 原生流不同，实际表现可能是先等完整响应结束，再一次性包装成流。

如果需要真正 token 级增量体验，建议改为 fetch + ReadableStream 或标准 SSE 客户端。

### 15.6 Provider 统计方法字段疑点

`AIServiceManager.get_provider_stats()` 中存在使用 `model.id` 的逻辑，但 `AIModel` 当前字段为 `value`、`label` 等。该方法若被调用，可能触发属性错误。

### 15.7 Settings 对 load_dotenv 时序敏感

`Settings` 类中部分字段通过 `os.getenv()` 在类定义阶段给默认值。`run.py` 会先加载 `.env`，正常启动路径可用。但如果测试、脚本或交互环境直接导入配置模块且未先设置环境变量，可能触发配置缺失。

### 15.8 示例 AI Base URL 需要人工复核

示例环境配置中存在 Anthropic 与 OpenAI Base URL 看起来不符合常规厂商域名的情况。建议后续人工复核真实可用网关和目标协议，避免配置示例误导部署。

### 15.9 CORS 配置需要与凭证策略一起复核

后端 CORS 当前允许来源来自配置，并允许所有方法和所有请求头，同时启用 credentials。若来源配置包含通配符或过宽来源，生产环境存在跨域策略风险。

### 15.10 日志可能包含敏感请求摘要

AI、DeepSeek 和请求中间件会记录请求摘要、消息数量、模型名、部分 payload 信息。生产环境需要确认不会记录 API Key、设备密码、完整网络配置、敏感拓扑或客户数据。

### 15.11 设备密码内存封装不是强加密

当前设备密码封装更接近进程内弱混淆，不能抵御内存读取、调试器、dump 文件或代码级访问风险。后续如进入生产环境，应使用更严格的凭证管理方案。

### 15.12 Telnet 底层依赖需要关注 Python 升级

Telnet 连接使用 `telnetlib`。该库在新 Python 版本中的长期可用性需要关注，建议规划替代库或抽象兼容层。

### 15.13 Telnet 命令完成判断存在死代码疑点

`TelnetConnection._check_command_completion()` 中可见 return 之后仍有遗留代码块的迹象。虽然不一定影响当前执行路径，但会增加维护理解成本。

### 15.14 会话状态均为进程内状态

网络连接、终端会话和 Provider 实例均为进程内状态。若后续使用多进程、多实例或容器横向扩展，需要设计共享会话存储、连接路由或粘性会话策略。

## 16. 建议演进路线

### 16.1 短期优先级

建议优先处理会直接影响用户体验的问题：

- 修正 `/terminal/disconnect` 的请求体模型，确保前后端参数一致。
- 将 `/terminal/cancel-connect` 接入真实取消机制。
- 复核 Claude Provider 的连通性检查协议。
- 复核 `.env.example` 中 OpenAI 与 Anthropic Base URL。
- 为生产部署明确 `/api` 到 `/api/v1` 的代理规则。

### 16.2 中期优先级

建议提升可维护性和稳定性：

- 将 Settings 改为更标准的 pydantic-settings 字段加载方式，减少 `os.getenv()` 类定义时序风险。
- 将 AI 流式前端实现改为 fetch 原生流或 SSE。
- 清理 Telnet 命令完成判断中的遗留代码。
- 为 `AIServiceManager.get_provider_stats()` 增加测试并修复字段名。
- 统一 Network 与 Terminal 两套连接路径的边界说明或抽象复用。

### 16.3 长期优先级

建议围绕生产化能力演进：

- 引入集中凭证管理，避免设备凭证长时间留存在进程内。
- 引入结构化审计日志与敏感字段脱敏策略。
- 支持多实例部署下的会话管理策略。
- 补充端到端测试，覆盖终端连接、AI 模型加载、流式响应和异常状态。
- 规划 Telnet 替代实现或协议适配层。

## 17. 运维关注点

部署或联调时建议重点确认：

- 后端 `.env` 是否存在且完整。
- `AI_ENABLED` 与各厂商 API Key 是否符合预期。
- 前端访问路径 `/api` 是否能正确转发到后端 `/api/v1`。
- 日志目录是否可写。
- SSH/Telnet 目标设备端口是否开放。
- 防火墙是否允许后端访问网络设备。
- 生产环境是否禁用过宽 CORS。
- 生产日志是否脱敏。

## 18. 变更影响说明

本次文档整理同时移除了 `backend/README.md`，后续后端相关说明应集中维护在 `docs/` 下，避免同类信息分散在多个位置。

新增架构文档建议作为后续维护入口。后续若修改 API、模型列表、启动脚本或终端连接机制，应同步更新本文档。
