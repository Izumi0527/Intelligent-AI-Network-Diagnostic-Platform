# AI 智能网络故障分析平台架构与系统信息总览

> 更新时间：2026-05-31
> 当前版本：0.2.1
> 覆盖范围：当前仓库代码、配置、脚本与测试。本文档是系统架构说明，不替代根目录 `README.md` 的快速开始。

## 1. 项目定位

本项目是一个前后端分离的 AI 智能网络故障分析平台，面向网络运维、网络故障诊断和网络安全治理场景。平台将网络设备终端、AI 辅助分析、联网搜索与多模型流式对话整合在同一工作台中。

核心目标：

- 让用户通过浏览器连接 SSH / Telnet 网络设备；
- 在同一界面执行排障命令、查看终端输出；
- 将日志、配置片段或故障现象交给 AI 助手分析；
- 通过「高级网络安全架构师」角色提示词，让 AI 回复兼顾网络架构、协议、性能、排障、安全风险与合规边界。

当前核心能力：

- SSH / Telnet 终端会话；
- 通用 NetworkService + Netmiko 连接路径；
- AI SSE 流式对话；
- OpenAI / Anthropic Claude / DeepSeek 多 provider 接入；
- Brave Search 联网搜索增强；
- DeepSeek 网络日志分析器；
- 工业 HUD 前端 UI，支持浅色 / 深色主题；
- 后端内部鉴权、终端连接策略、日志与错误脱敏；
- 跨平台脚本化启动、构建、lint 与后端质量门禁。

## 2. 总体架构

```text
浏览器
  |
  | Vue 3 + Pinia + TypeScript
  | fetch / axios 请求 /api/*
  v
Vite 开发服务器
  |
  | proxy: /api -> http://localhost:8000/api/v1
  v
FastAPI 后端
  |
  |-- API 路由层
  |     |-- /ai
  |     |-- /terminal
  |     |-- /network
  |     `-- /health
  |
  |-- AIApplicationService
  |     |-- Brave Search 注入搜索上下文
  |     |-- 注入高级网络安全架构师 persona
  |     `-- AIServiceManager
  |           |-- OpenAIProvider
  |           |-- ClaudeProvider
  |           `-- DeepseekProvider
  |
  |-- DeepSeek 网络日志分析器
  |
  |-- TerminalService
  |     |-- TerminalManager
  |     |-- SSHManager / Paramiko
  |     `-- TelnetManager / telnetlib
  |
  |-- NetworkService / Netmiko
  |
  `-- settings / logger / security / terminal_policy
```

开发期浏览器侧统一使用 `/api`，Vite 将其重写到后端 `/api/v1`。生产部署时需要由网关或反向代理提供等价路径映射。

## 3. 技术栈

### 3.1 前端

- Vue 3.5
- TypeScript 5.8（strict）
- Pinia 2.3
- Vite 6
- Tailwind CSS v4 + `@tailwindcss/postcss`
- marked + DOMPurify
- Axios：普通 HTTP 请求
- fetch + `ReadableStream`：AI SSE 流式响应
- ESLint 9 flat config
- vue-tsc

### 3.2 后端

- Python `>=3.9,<3.13`
- FastAPI 0.115
- Uvicorn 0.34
- Pydantic 2.11 + pydantic-settings 2.9
- Netmiko 4.5
- Paramiko 3.5
- telnetlib（需要关注 Python 后续版本兼容性）
- aiohttp / httpx / requests
- python-jose / passlib / bcrypt
- pytest / pytest-asyncio / pytest-cov
- Ruff / Black / MyPy
- uv

## 4. 顶层目录职责

```text
Project3/
  backend/        FastAPI 后端、AI provider、网络连接、配置和运行入口
  frontend/       Vue 前端应用、组件、状态管理、类型和接口客户端
  docs/           长期文档、截图、实现计划
  discuss/        讨论、验证报告、临时草案
  scripts/        跨平台运行、构建、lint、测试和维护脚本
  tests/          根目录测试集
  logs/           运行日志（被 .gitignore 排除）
```

文档归属：

- 根 `README.md`：项目总入口、快速开始、核心能力和 API 摘要；
- `docs/project-architecture-and-system-overview.md`：系统架构、模块边界、数据流与风险说明；
- `docs/plans/`：设计计划与实现记录；
- `discuss/`：临时讨论与验证报告。

前端说明集中维护在根 README 与本文档，避免同类信息分散在多个入口中重复漂移。

## 5. 后端架构

### 5.1 启动链路

入口：`backend/run.py`

主要流程：

1. 计算后端目录；
2. 加载 `backend/.env`；
3. 导入 `settings`；
4. 初始化日志系统；
5. 解析 `--host`、`--port`、`--reload`；
6. 使用 Uvicorn 启动 `app.main:app`。

项目常规启动不直接调用底层命令，而是通过根目录脚本：

- `scripts/dev.ps1` / `scripts/dev.sh`
- `scripts/prod.ps1` / `scripts/prod.sh`

开发脚本会先启动后端，等待 `/api/v1/health` 通过后再启动前端。

### 5.2 FastAPI 应用入口

入口：`backend/app/main.py`

职责：

- 创建 FastAPI 应用；
- 配置文档地址；
- 配置 CORS；
- 注册请求日志中间件；
- 挂载 `/api/v1` 路由；
- 注册启动 / 关闭生命周期；
- 创建空闲终端会话清理任务。

### 5.3 配置系统

配置类：`backend/app/config/settings.py`

配置来源：

- 环境变量；
- `backend/.env`；
- `backend/.env.example`。

关键配置分组：

- 基础：`APP_ENV`、`DEBUG`、`API_PREFIX`、`API_V1_STR`、`HOST`、`PORT`；
- 安全：`SECRET_KEY`、`API_AUTH_ENABLED`、`INTERNAL_API_TOKEN`、JWT 配置；
- AI：`AI_ENABLED`、OpenAI / Anthropic / DeepSeek API Key、Base URL、模型列表；
- Brave Search：联网搜索 API Key 与开关；
- 终端策略：允许主机、CIDR、SSH/Telnet 端口、命令长度、高危命令正则；
- 日志：`LOG_LEVEL`、日志格式与文件输出。

### 5.4 API 路由

统一入口：`backend/app/api/api_v1/api.py`

挂载模块：

- `/ai`
- `/terminal`
- `/network`
- `/health`

主要端点：

| 模块 | 端点 |
|------|------|
| Health | `GET /api/v1/health`、`GET /api/v1/health/ready` |
| AI | `GET /ai/models`、`GET /ai/models/{model_id}/status`、`POST /ai/chat/stream`、`POST /ai/debug/request-format`、`GET /ai/deepseek/status`、`POST /ai/deepseek/analyze-network-log` |
| Terminal | `POST /terminal/connect`、`POST /terminal/cancel-connect`、`POST /terminal/execute`、`POST /terminal/disconnect`、`GET /terminal/sessions`、`GET /terminal/sessions/{session_id}`、`POST /terminal/cleanup` |
| Network | `POST /network/connect`、`POST /network/command`、`POST /network/disconnect`、`GET /network/connections`、`GET /network/connections/{connection_id}` |

所有路径均在 `/api/v1` 前缀下。

## 6. AI 子系统

### 6.1 AIApplicationService

文件：`backend/app/services/ai/application_service.py`

职责：

- 承载路由之外的 AI 对话编排；
- 统一处理模型检查、请求日志、SSE 编码和客户端安全错误文案；
- 在 `enable_search=true` 时调用 Brave Search；
- 将搜索结果作为 system message 注入；
- 无条件注入「高级网络安全架构师」persona；
- 调用 `AIServiceManager.chat_stream()` 获取 provider 事件；
- 将 provider 事件统一转换为 SSE：`search_results`、`thinking`、`content`、`error`、`done`。

消息顺序：

```text
[persona(system), search_context(system)?, ...user/assistant history]
```

这样保证稳定角色设定优先于临时搜索上下文。

### 6.2 角色提示词

文件：`backend/app/services/ai/prompts.py`

常量：

- `NETWORK_SECURITY_ARCHITECT_PERSONA`：主聊天助手 persona；
- `NETWORK_LOG_ANALYST_SYSTEM`：DeepSeek 日志分析器 system；
- `_ARCHITECT_IDENTITY`：共享角色称谓。

角色定位：高级网络安全架构师，兼具资深网络工程师的体系化排障功底与安全架构师的纵深防御视角。网络架构、协议、故障诊断与性能是主体，安全风险与加固建议是并列增强维度。

### 6.3 AIServiceManager 与 Provider

文件：`backend/app/services/ai/manager.py`

职责：

- 根据 API Key 初始化 provider；
- 聚合可用模型；
- 检查模型连接状态；
- 根据模型 ID 前缀路由：
  - `gpt-` → OpenAIProvider；
  - `claude-` → ClaudeProvider；
  - `deepseek-` → DeepseekProvider；
- 暴露统一 `chat_stream()`。

Provider 文件：

- `backend/app/services/ai/providers/openai_provider.py`
- `backend/app/services/ai/providers/claude_provider.py`
- `backend/app/services/ai/providers/deepseek_provider.py`

Provider 只负责把已编排好的 `request.messages` 转发到上游模型，并把上游流式响应转换为内部 `StreamEvent`。

### 6.4 Brave Search 增强

Brave Search client 位于 `backend/app/services/search/brave_search.py`。

当 `ChatRequest.enable_search=true` 且 Brave 已启用：

1. 后端取最后一条 user message 作为 query；
2. 调用 Brave Search；
3. 构造 `SearchSource[]` 返回给前端；
4. 注入包含当前真实时间、搜索结果标题、URL、摘要的 system block；
5. 前端收到 `search_results` SSE 事件并展示来源卡片。

搜索失败或未配置时不会中断 AI 对话，而是返回 `search_failed=true`。

### 6.5 DeepSeek 网络日志分析器

文件：`backend/app/services/ai/deepseek/analyzer.py`

能力：

- `error_analysis`
- `performance_analysis`
- `security_analysis`
- 自动日志类型分类；
- IP、时间戳、错误码、接口、协议等模式提取；
- 非流式与流式日志分析均使用 `NETWORK_LOG_ANALYST_SYSTEM`。

## 7. 前端架构

### 7.1 启动链路

入口：

- `frontend/src/main.ts`
- `frontend/src/App.vue`
- `frontend/src/layouts/MainLayout.vue`

启动流程：

1. 创建 Vue 应用；
2. 注册 Pinia；
3. 加载 `main.css`；
4. 渲染 `MainLayout`；
5. 加载终端区与 AI 助手区。

开发服务默认：`http://localhost:5180`。

### 7.2 布局与主题

主布局：`frontend/src/layouts/MainLayout.vue`

布局区域：

- 顶栏：NETOPS 品牌、副标题、时间、后端状态、命令面板、主题切换；
- 左侧：网络终端；
- 右侧：AI 助手；
- 响应式：桌面双栏，移动端通过 tab / 折叠状态适配。

主题状态：`frontend/src/stores/app.ts`

- 默认浅色；
- 用户切换后写入 `localStorage.theme`；
- 深色模式通过 `document.documentElement.classList.add('dark')` 生效。

### 7.3 状态管理

Pinia store：

- `stores/app.ts`：服务器连接状态与主题；
- `stores/terminal.ts`：终端连接、会话、命令、输出与历史；
- `stores/ai-assistant/`：AI 助手状态、模型、流式响应、搜索开关、消息与错误。

AI 助手默认选中模型：`deepseek-v4-flash`。

### 7.4 API 客户端

AI 客户端：`frontend/src/utils/aiService.ts`

- Axios：模型列表与状态检查；
- fetch：`POST /api/ai/chat/stream` 真流式响应；
- SSE 状态机解析 `event:` / `data:`；
- 将后端事件转换为前端统一 JSON 行：`thinking`、`content`、`error`、`search_results`。

终端客户端：`frontend/src/utils/terminalService.ts`

- 使用 Axios；
- 连接、执行命令、断开、查询会话；
- 连接接口超时更长，以适配网络设备首次连接慢的问题。

### 7.5 组件结构

主要组件：

- `components/terminal/NetworkTerminal.vue`：终端壳组件；
- `components/terminal/components/*`：连接表单、输出、命令输入、状态栏；
- `components/ai-assistant/AIAssistant.vue`：AI 助手壳组件；
- `components/ai-assistant/components/*`：头部、消息区、输入框、模型选择、搜索/流式控件等；
- `components/common/ServerStatusIndicator.vue`：后端状态指示；
- `components/ui/*`：HUD / 视觉增强组件。

## 8. 网络设备连接架构

后端存在两条网络设备交互路径：

### 8.1 Terminal 路径

对应前端虚拟终端体验。

```text
前端 Terminal UI
  -> terminalService
  -> /api/v1/terminal/*
  -> TerminalService
  -> TerminalManager
  -> SSHManager / TelnetManager
  -> 网络设备
```

特点：

- 持久会话；
- 命令历史；
- 输出清洗；
- 会话超时与空闲清理；
- 更贴近用户在页面中操作终端的体验。

### 8.2 Network 路径

对应通用连接与命令执行 API。

```text
外部/内部调用 /api/v1/network/*
  -> NetworkService
  -> Netmiko ConnectHandler
  -> 网络设备
```

特点：

- 使用 Netmiko；
- 维护连接字典；
- `asyncio.to_thread()` 包装阻塞连接与命令执行；
- 适合结构化 API 调用。

这两条路径的连接 ID、会话状态与底层库不同，不能混用。

## 9. 数据模型

### 9.1 AI 模型

文件：`backend/app/models/ai.py`

核心模型：

- `AIModel`
- `Message`
- `ChatRequest`
- `SearchSource`
- `ModelsResponse`
- `ModelConnectionStatus`
- `StreamEvent`

`ChatRequest` 关键字段：

- `model`
- `messages`
- `max_tokens`
- `temperature`
- `top_p`
- `stream`
- `enable_search`

约束：

- 单条消息最大 8000 字符；
- 消息总长度最大 32000 字符；
- 最多 50 条消息；
- `max_tokens` 最大 8192。

### 9.2 Terminal / Network 模型

- `backend/app/models/terminal.py`：终端凭证、命令请求、响应、会话信息；
- `backend/app/models/network.py`：连接请求、连接响应、命令请求、连接列表等。

## 10. 日志与安全

### 10.1 日志

工具：`backend/app/utils/logger.py`

能力：

- 控制台日志；
- 文件日志；
- 访问日志；
- 错误日志；
- 日志目录自动创建；
- 日志敏感字段脱敏；
- 客户端安全错误文案。

日志输出目录：`logs/`。该目录被 `.gitignore` 排除，不进入版本控制。

### 10.2 安全边界

安全相关模块：

- `backend/app/utils/security.py`
- `backend/app/utils/terminal_policy.py`
- `backend/app/services/ai/base.py`
- `backend/app/core/rate_limit.py`

主要机制：

- 内部 API Token；
- JWT 工具；
- 终端目标主机 / CIDR / 端口限制；
- 命令长度限制；
- 高风险命令正则拦截；
- AI 上游错误脱敏；
- 日志脱敏；
- 设备密码不写入代码或版本库。

注意：设备密码的进程内封装更偏向避免明文直接暴露，不应视为强加密或 secret manager。

## 11. 安装、运行与脚本

本项目约定所有 Run / Debug / Test / Build 操作优先通过根目录 `scripts/` 封装脚本执行，避免不同环境直接调用底层 `npm`、`uv`、`python` 等命令导致行为漂移。

### 11.1 环境要求

- Python 3.9–3.12；
- Node.js 20+；
- uv；
- npm；
- Windows PowerShell 7+（Windows 推荐）或 Bash / Git Bash。

### 11.2 环境变量

后端：

```powershell
Copy-Item backend/.env.example backend/.env
```

前端：

```powershell
Copy-Item frontend/.env.example frontend/.env.local
```

后端常用配置：

| 变量 | 说明 |
|------|------|
| `INTERNAL_API_TOKEN` | 内部接口 Bearer Token；前端 `VITE_INTERNAL_API_TOKEN` 需与它一致 |
| `API_AUTH_ENABLED` | 是否启用内部 API 鉴权，生产环境应启用 |
| `DEEPSEEK_API_KEY` / `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | 按实际启用 provider 配置 |
| `BRAVE_SEARCH_ENABLED` / `BRAVE_SEARCH_API_KEY` | Brave Search 联网搜索增强 |
| `TERMINAL_ALLOWED_HOSTS` / `TERMINAL_ALLOWED_CIDRS` | 限制可连接网络设备范围 |
| `TERMINAL_ALLOWED_SSH_PORTS` / `TERMINAL_ALLOWED_TELNET_PORTS` | 限制 SSH / Telnet 端口 |
| `TERMINAL_COMMAND_MAX_LENGTH` | 终端命令最大长度 |
| `TERMINAL_BLOCKED_COMMAND_PATTERNS` | 高风险命令拦截正则 |
| `LOG_LEVEL` | 日志级别 |

前端当前实际消费：

| 变量 | 说明 |
|------|------|
| `VITE_INTERNAL_API_TOKEN` | 内部接口访问 Token，需与后端 `INTERNAL_API_TOKEN` 一致 |

### 11.3 启动脚本

脚本目录：`scripts/`

| 脚本 | 作用 |
|------|------|
| `dev.ps1` / `dev.sh` | 开发环境：后端热重载 + 前端 Vite |
| `prod.ps1` / `prod.sh` | 生产预览：后端 production + 前端 preview |
| `build.ps1` / `build.sh` | 前端生产构建与 dist 统计 |
| `lint.ps1` / `lint.sh` | 前端 vue-tsc + ESLint |
| `backend-check.ps1` / `backend-check.sh` | 后端依赖、ruff、pytest、脚本契约门禁 |
| `clean-python-cache.ps1` / `clean-python-cache.sh` | 清理 Python 缓存 |
| `p3_axe_audit.py` / `p6_axe_audit.py` | Playwright + axe 验证脚本 |

Windows PowerShell：

```powershell
.\scripts\dev.ps1
.\scripts\dev.ps1 -BackendPort 8080 -FrontendPort 5181
.\scripts\prod.ps1
.\scripts\build.ps1
.\scripts\lint.ps1
.\scripts\backend-check.ps1
```

Linux / macOS / Git Bash：

```bash
./scripts/dev.sh
./scripts/prod.sh
./scripts/build.sh
./scripts/lint.sh
./scripts/backend-check.sh
```

启动脚本共同约定：

- 检查项目布局；
- 检查 `backend/.env` 是否存在；
- 检查必要命令：`uv`、`npm`，Shell 脚本额外检查 `curl`；
- 自动创建日志目录；
- 后端先启动，健康检查通过后再启动前端；
- 设置 `PYTHONDONTWRITEBYTECODE=1`，减少运行时缓存污染。

### 11.4 访问地址

默认端口：

- 前端：`http://localhost:5180`；
- 后端健康检查：`http://localhost:8000/api/v1/health`；
- 后端 readiness：`http://localhost:8000/api/v1/health/ready`；
- API 文档：`http://localhost:8000/api/v1/docs`。

开发模式下，前端浏览器侧统一请求 `/api/*`，由 Vite 代理重写到后端 `/api/v1/*`。

### 11.5 日志与缓存

- 运行日志输出到 `logs/`，目录已加入 `.gitignore`；
- `backend/.env`、`frontend/.env.local`、`.venv`、`node_modules` 均不进入版本控制；
- 启动脚本设置 `PYTHONDONTWRITEBYTECODE=1`；
- Python 缓存可通过 `clean-python-cache.ps1` / `clean-python-cache.sh` 清理。

## 12. 测试与质量保障

根目录测试：`tests/`

当前测试覆盖主题：

- AI SSE 契约与错误脱敏；
- AI persona 与 Brave Search 注入顺序；
- Brave Search client；
- Pydantic v2 模型；
- 后端包元数据与运行依赖；
- 启动脚本契约；
- Python 字节码缓存策略；
- 终端连接策略与 Telnet 登录策略；
- Health readiness；
- request id tracing；
- logger 行为；
- 架构边界。

主要验证入口：

```powershell
.\scripts\lint.ps1
.\scripts\build.ps1
.\scripts\backend-check.ps1
```

## 13. 关键数据流

### 13.1 AI 流式对话

```text
用户输入
  -> ai-assistant store
  -> aiService.sendMessageStream()
  -> fetch('/api/ai/chat/stream')
  -> Vite proxy 到 /api/v1/ai/chat/stream
  -> AIApplicationService.chat_stream()
  -> Brave Search? + persona 注入
  -> AIServiceManager.chat_stream()
  -> Provider 调用上游模型
  -> 后端 SSE event
  -> 前端 SSE 状态机解析
  -> ChatMessages 渲染 thinking/content/search sources
```

### 13.2 联网搜索增强

```text
enable_search=true
  -> 取最后一条 user message
  -> BraveSearchClient.search(query)
  -> 格式化搜索 system block（含当前真实时间）
  -> request.messages 插入 search context
  -> 前端先收到 search_results 事件
  -> AI 回复末尾可引用来源
```

### 13.3 终端连接

```text
用户填写 SSH/Telnet 信息
  -> terminalStore.connectToDevice()
  -> terminalService.connect()
  -> POST /api/terminal/connect
  -> TerminalService.connect()
  -> TerminalManager.connect()
  -> SSHManager 或 TelnetManager
  -> 返回 session_id
  -> 前端进入 connected 状态
```

### 13.4 终端命令执行

```text
用户输入命令
  -> terminalStore.executeCommand()
  -> terminalService.execute()
  -> POST /api/terminal/execute
  -> TerminalService.execute_command()
  -> TerminalManager.execute_command()
  -> SSH/Telnet 会话执行
  -> 清洗输出
  -> 前端追加终端输出
```

## 14. 当前关注点与后续演进建议

以下是从当前代码结构可见的维护关注点，并非线上故障结论。

### 14.1 生产代理路径

前端开发期依赖 Vite 将 `/api` 重写到 `/api/v1`。生产部署必须提供同等代理规则，或者同步调整前端 baseURL 与后端 API 前缀。

### 14.2 两套网络连接路径边界

`/terminal/*` 与 `/network/*` 都能连接设备，但状态模型和底层库不同。后续应继续保持文档化边界，避免在业务层混用连接 ID / session ID。

### 14.3 终端取消连接

`/terminal/cancel-connect` 当前更接近 API 层占位能力。若需要真正取消正在进行的底层连接，应继续完善任务取消机制。

### 14.4 多实例部署

AI provider、终端会话、网络连接等状态目前主要在进程内。多 worker / 多实例部署需要共享状态、粘性会话或连接路由设计。

### 14.5 Telnet 依赖演进

Telnet 路径仍依赖 `telnetlib`。后续升级 Python 版本时应提前评估替代库或兼容层。

### 14.6 凭证管理

当前设备密码和 API Key 依赖环境变量、请求体和进程内状态。生产环境应优先考虑 secret manager、审计日志和更强凭证生命周期管理。

## 15. 文档维护规则

当修改以下内容时，应同步更新本文档和根 `README.md`：

- API 路径或请求 / 响应模型；
- AI provider、模型列表、persona 或搜索注入逻辑；
- 前端主题、布局、状态管理或运行端口；
- 启动脚本和质量门禁；
- 终端连接策略、安全策略或日志策略；
- 测试目录和验证入口。
