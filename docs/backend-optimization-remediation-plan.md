# 后端优化整改持续计划

> 本文档是 Project3 后端整改的持久任务板。后续无论是否重开会话，都应先读取本文件，按未完成的 `- [ ]` 条目继续推进；每完成一条，必须改为 `- [x]`，并在文末追加执行记录。

## 使用规则

- 每次开工前先查看本文件和 `git status --short`，不要覆盖用户或其他代理的未提交改动。
- 每完成一项任务，立即把对应清单从 `- [ ]` 改为 `- [x]`。
- 每完成一个阶段或一组相关任务，在“执行记录”追加日期、完成项、验证命令和结果摘要。
- 不要提交 `backend/.env`；当前审查发现其中存在真实形态第三方 AI 密钥，应由用户在外部平台轮换。
- 本计划采用“严格优先”策略：非测试环境默认安全 fail-closed。

## 当前基线

- 后端技术栈：FastAPI、Pydantic v2、pydantic-settings、uvicorn、aiohttp、paramiko、netmiko。
- 后端代码入口：`backend/app/main.py`、`backend/run.py`。
- API 聚合入口：`backend/app/api/api_v1/api.py`。
- 核心风险域：内部接口鉴权、终端 SSH/Telnet 连接、网络设备命令执行、AI 调用成本与敏感日志。
- 已验证基线：在项目虚拟环境中运行 `python -m pytest tests -q` 曾得到 `38 passed`，同时存在 Pydantic/FastAPI/telnetlib 弃用警告。
- 当前质量现状：`ruff check backend/app tests` 存在大量历史问题，本轮不要求一次性清空；新增或修改文件应尽量保持局部可检查。

## Phase 1：安全严格整改

- [x] 统一内部接口鉴权默认策略
  - 涉及范围：`backend/app/config/settings.py`、`backend/app/api/deps.py`、安全测试。
  - 目标：非 `test` 环境默认要求 `API_AUTH_ENABLED=true` 和有效 `INTERNAL_API_TOKEN`。
  - 验收：development/staging/production 漏配或使用占位 Token 时 `Settings()` 失败；test 环境仍可显式关闭鉴权。

- [x] 收紧终端连接目标策略为 fail-closed
  - 涉及范围：`backend/app/utils/terminal_policy.py`、终端安全测试。
  - 目标：`TERMINAL_ALLOWED_HOSTS` 或 `TERMINAL_ALLOWED_CIDRS` 至少配置一项，否则拒绝连接。
  - 验收：未配置允许列表时拒绝任意 SSH/Telnet 目标；配置命中允许列表时保留原有连接路径。

- [x] 将终端命令策略从黑名单改为只读白名单
  - 涉及范围：`backend/app/config/settings.py`、`backend/app/utils/terminal_policy.py`、终端命令测试。
  - 目标：默认仅允许受控诊断命令，例如 `display`、`show`、`ping`、`traceroute`、`tracert`。
  - 验收：允许 `display version`、`show version`；拒绝 `save`、`copy`、`delete`、`reboot`、`system-view`、`display current-configuration`。

- [x] 增加 AI 请求成本和资源边界
  - 涉及范围：`backend/app/models/ai.py`、`backend/app/api/api_v1/endpoints/ai.py`、AI 接口测试。
  - 目标：限制消息数量、单条内容长度、总内容长度、`max_tokens`、`temperature`、`top_p`。
  - 验收：超长消息、超多 messages、非法采样参数和超大 `max_tokens` 返回 422。

- [x] 统一第三方 AI 上游错误脱敏
  - 涉及范围：`backend/app/services/ai/base.py`、各 provider、AI 错误测试。
  - 目标：客户端只收到通用错误和 `request_id`，不透传上游原始错误。
  - 验收：模拟上游错误包含 Token、URL、账号信息时，响应体不包含敏感原文。

- [x] 建立全局日志脱敏机制
  - 涉及范围：`backend/app/utils/logger.py`、SSH/Telnet/AI 日志调用点、日志测试。
  - 目标：formatter 或 filter 层统一脱敏 `password`、`token`、`api_key`、`secret`、`Authorization`、用户 Prompt 和模型输出。
  - 验收：普通 `logger.info/debug/error` 写入敏感字段后，格式化输出不包含明文。

- [x] 关闭或保护生产环境 API 文档入口
  - 涉及范围：`backend/app/main.py`、配置测试。
  - 目标：production 中禁用或鉴权保护 `/api/v1/docs`、`/api/v1/redoc`、`/api/v1/openapi.json`。
  - 验收：production 配置下未授权访问文档入口不可枚举内部接口。

## Phase 2：架构与生命周期重构

- [x] 将 FastAPI startup/shutdown 迁移到 lifespan
  - 涉及范围：`backend/app/main.py`、生命周期测试。
  - 目标：替代已弃用的 `@app.on_event`，统一创建和取消后台任务。
  - 验收：测试启动时创建清理任务；shutdown 后任务被取消且不产生未处理异常。

- [x] 统一服务实例生命周期
  - 涉及范围：`backend/app/api/deps.py`、`backend/app/main.py`、服务管理测试。
  - 目标：减少模块级全局单例，优先通过 `app.state` 管理 `TerminalService`、`AIServiceManager` 等服务。
  - 验收：TestClient 生命周期内服务可替换、可清理；导入模块不提前创建网络资源。

- [x] 移除核心管理器构造阶段的隐式后台任务
  - 涉及范围：`backend/app/core/terminal.py`、`backend/app/core/network/telnet/manager.py`。
  - 目标：`__init__` 和连接成功路径不直接 `create_task`，任务由应用生命周期统一控制。
  - 验收：单独实例化 manager 不创建后台任务；应用启动后只存在预期清理任务。

- [x] 服务层领域异常替代直接 HTTPException
  - 涉及范围：`backend/app/services/terminal_service.py`、API 路由异常映射测试。
  - 目标：新增领域异常，例如 `TerminalPolicyViolation`、`SessionNotFound`、`TerminalConnectionFailed`。
  - 验收：服务层不再依赖 FastAPI；路由层或全局 exception handler 负责映射 HTTP 状态码。

- [x] 拆薄 AI 路由层
  - 涉及范围：`backend/app/api/api_v1/endpoints/ai.py`、AI 应用服务或 helper。
  - 目标：路由只负责依赖注入和协议响应，聊天编排、DeepSeek 兼容入口、日志摘要、响应补齐下沉到服务层。
  - 验收：路由单测可用 fake service 验证委托行为；业务分支不散落在路由函数中。

- [x] 统一 SSE 事件编码契约
  - 涉及范围：AI 流式响应 helper、前后端契约测试。
  - 目标：为 `content`、`thinking`、`error`、`done` 定义稳定 SSE 输出格式。
  - 验收：流式接口不混合裸文本和 SSE；错误事件也保持一致事件结构。

- [x] 收口 legacy NetworkService
  - 涉及范围：`backend/app/services/network_service.py`、`backend/app/api/api_v1/endpoints/network.py`。
  - 目标：确认 `/network` 旧写接口已废弃后，将旧服务隔离到 legacy 包或删除运行时入口。
  - 验收：旧连接能力不会被健康检查或依赖层误初始化；`/network` 写接口继续返回 410。

## Phase 3：运行质量与测试治理

- [x] 迁移 Pydantic v2 写法
  - 涉及范围：`backend/app/models/ai.py`、`backend/app/models/terminal.py`、相关测试。
  - 目标：`@validator` 改为 `@field_validator`，`class Config` 改为 `ConfigDict`。
  - 验收：相关 Pydantic 弃用警告消失，模型行为保持兼容或按新安全策略明确返回 422。

- [x] 收紧 Python 版本声明
  - 涉及范围：`backend/pyproject.toml`、依赖校验测试。
  - 目标：在替换 `telnetlib` 前，将 `requires-python` 收紧为 `>=3.9,<3.13`。
  - 验收：包元数据测试同步更新；依赖检查通过。

- [x] 明确依赖单一权威来源
  - 涉及范围：`backend/pyproject.toml`、`backend/requirements.txt`、依赖同步测试。
  - 目标：以 `pyproject.toml + uv.lock` 为权威；若保留 `requirements.txt`，标记为生成文件并增加同步校验。
  - 验收：运行依赖不会在两个文件中无声漂移。

- [x] 调整 pytest coverage 默认行为
  - 涉及范围：`backend/pyproject.toml`、`pytest.ini`。
  - 目标：普通测试不默认生成 `htmlcov`；覆盖率通过显式命令运行。
  - 验收：`pytest -q --no-cov -p no:cacheprovider` 不生成 coverage 产物；覆盖率命令仍可单独执行。

- [x] 新增后端质量检查脚本
  - 涉及范围：`scripts/backend-check.ps1`、`scripts/backend-check.sh`、脚本验证测试。
  - 目标：串联 `uv pip check`、后端定向 `ruff`、pytest、现有 runtime/launch 校验。
  - 验收：脚本可在 Windows PowerShell 和类 Unix shell 下执行，失败时返回非零退出码。

- [x] 建立架构边界测试
  - 涉及范围：`tests/` 下新增 AST 或 import 检查。
  - 目标：防止 `services/*` 导入 FastAPI、`models/*` 导入 logger、`core/*` 依赖 API 层。
  - 验收：违反边界时测试失败并指出具体文件。

- [x] 增加后端真实启动链路测试
  - 涉及范围：`backend/run.py`、启动脚本测试。
  - 目标：覆盖参数解析、`.env` 加载、`uvicorn.run` 参数传递。
  - 验收：不真正占用端口即可验证启动参数。

## Phase 4：后续演进优化

- [x] 替换 `telnetlib`
  - 目标：Python 3.13 前迁移到可维护 Telnet 实现或自有最小协议层。
  - 验收：移除 `telnetlib` 弃用警告，并放宽 Python 上限前完成兼容测试。

- [x] 引入可插拔限流后端
  - 目标：内存限流先落地，后续可替换为 Redis 或网关限流。
  - 验收：AI 和终端接口都有清晰限流策略、响应头和 429 测试。

- [x] 增加协议级假服务测试
  - 目标：用 fake SSH/Telnet/AI provider 覆盖超时、断连、分页、流式错误。
  - 验收：核心连接和 provider 解析逻辑不依赖真实外部服务即可回归。

- [x] 标准化 API 错误响应
  - 目标：统一错误结构为 `{ "error": { "code": "...", "message": "...", "request_id": "...", "details": [] } }`。
  - 验收：FastAPI validation、鉴权、业务异常、上游异常都使用统一结构。

- [x] 增加请求追踪 ID
  - 目标：支持 `X-Request-ID` 透传，无请求头时自动生成。
  - 验收：响应头、应用日志、AI 上游调用日志、终端操作日志都包含同一 request_id。

- [x] 扩展健康检查分级
  - 目标：保留轻量 `/health`，新增或扩展 readiness 检查配置和资源状态。
  - 验收：健康检查不会触发昂贵外部 AI 调用；ready 检查能发现关键配置缺失。

## 常用验证命令

从后端目录运行：

```powershell
cd "C:/cascadeProjects/Project3/backend"
uv pip check
uv run --no-sync python -m pytest -q --no-cov -p no:cacheprovider
```

从仓库根目录运行：

```powershell
cd "C:/cascadeProjects/Project3"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "tests/scripts/verify-backend-runtime-dependencies.ps1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "tests/scripts/verify-launch-scripts.ps1"
```

需要覆盖率时单独运行：

```powershell
cd "C:/cascadeProjects/Project3/backend"
uv run --no-sync python -m pytest --cov=app --cov-report=term-missing
```

局部质量检查建议：

```powershell
cd "C:/cascadeProjects/Project3/backend"
uv run --no-sync python -m ruff check app tests
```

## 执行记录

- 2026-05-22：创建后端优化整改持续计划文档；当前仅新增计划文件，尚未执行代码整改。
- 2026-05-22：完成 Phase 1 前三项安全整改：非 test 环境强制内部接口鉴权、终端连接目标 fail-closed、终端命令只读白名单；验证 `tests/test_backend_security_and_connection_policy.py` 为 `26 passed`，完整 `tests` 为 `44 passed`，`uv pip check` 通过，修改文件 `ruff check` 通过，`verify-backend-runtime-dependencies.ps1` 与 `verify-launch-scripts.ps1` 通过。
- 2026-05-22：完成 Phase 1 第 4-6 项整改：AI 请求限制消息数量、单条/总内容长度、`max_tokens`、`temperature`、`top_p`；第三方 AI 上游错误统一返回通用文案和 `request_id`，连接状态接口不再透传敏感上游错误；日志 formatter 增加普通文本、结构化字段和异常栈脱敏。验证 `tests/test_logger.py tests/test_backend_security_and_connection_policy.py` 为 `41 passed`，完整 `tests` 为 `57 passed`，局部 `ruff check` 通过，`uv pip check` 通过，`verify-backend-runtime-dependencies.ps1` 与 `verify-launch-scripts.ps1` 通过。
- 2026-05-22：完成 Phase 1 最后一项整改：新增应用工厂，根据 `APP_ENV=production` 禁用 `/api/v1/docs`、`/api/v1/redoc`、`/api/v1/openapi.json`，根路径在生产环境只返回服务状态；验证 `tests/test_logger.py tests/test_backend_security_and_connection_policy.py` 为 `42 passed`，完整 `tests` 为 `58 passed`，局部 `ruff check` 通过，`uv pip check` 通过，`verify-backend-runtime-dependencies.ps1` 与 `verify-launch-scripts.ps1` 通过。
- 2026-05-22：完成 Phase 2 第一项整改：将 FastAPI `startup/shutdown` 迁移为 `lifespan` 上下文，保留终端空闲会话清理任务的启动与取消逻辑，并新增无 `on_event` 弃用警告的回归测试；验证 `tests/test_backend_security_and_connection_policy.py` 为 `39 passed`，完整 `tests` 为 `59 passed`，局部 `ruff check` 通过，`uv pip check` 通过，`verify-backend-runtime-dependencies.ps1` 与 `verify-launch-scripts.ps1` 通过。
- 2026-05-22：完成 Phase 2 第二项整改：服务实例统一由 `lifespan` 创建并挂载到 `app.state`，依赖函数优先从当前应用实例读取服务，移除 AI manager 导入即创建的模块级全局单例，并在 shutdown 时统一调用服务 `cleanup`；验证 `tests/test_backend_security_and_connection_policy.py` 为 `42 passed`，完整 `tests` 为 `62 passed`，局部 `ruff check` 通过，`uv pip check` 通过，`verify-backend-runtime-dependencies.ps1` 与 `verify-launch-scripts.ps1` 通过。
- 2026-05-22：完成 Phase 2 第三、第四项整改：核心终端和 Telnet 管理器构造阶段不再隐式创建后台任务，任务由应用 `lifespan` 显式启动并在 shutdown 清理；新增终端领域异常层，`TerminalService` 不再导入 FastAPI 或直接抛 `HTTPException`，终端路由统一将领域异常映射为 HTTP 响应。验证 `tests/test_terminal_connection_regressions.py tests/test_backend_security_and_connection_policy.py` 为 `54 passed`，完整 `tests` 为 `68 passed`，局部 `ruff check` 通过，`uv pip check` 通过，`verify-backend-runtime-dependencies.ps1` 与 `verify-launch-scripts.ps1` 通过。
- 2026-05-22：完成 Phase 2 第五项整改：新增 `AIApplicationService` 承载模型状态脱敏、聊天请求摘要、响应补齐、流式输出适配与 DeepSeek 兼容生成编排，AI 路由收敛为依赖注入、HTTP 响应包装和异常映射；新增 fake 应用服务路由委托测试，验证 `tests/test_backend_security_and_connection_policy.py` 为 `48 passed`，完整 `tests` 为 `71 passed`，局部 `ruff check` 通过。
- 2026-05-22：完成 Phase 2 第六项整改：新增统一 SSE 编码 helper，AI 聊天流和 DeepSeek 兼容流均输出 `event: content|thinking|error|done` 与 JSON `data`，移除裸文本和 data-only 混用；错误事件保持统一结构并脱敏。验证 SSE 契约测试通过，`tests/test_backend_security_and_connection_policy.py` 为 `51 passed`，完整 `tests` 为 `74 passed`，局部 `ruff check` 通过。
- 2026-05-23：修复 development 启动链路：`run.py` 在本地开发环境缺少内部鉴权配置时生成仅当前进程有效的临时 Token，`dev.ps1` 与 `dev.sh` 为后端 `INTERNAL_API_TOKEN` 和前端 `VITE_INTERNAL_API_TOKEN` 注入同一个开发 Token，不放松 production 配置校验；完成 Phase 2 最后一项整改，将 legacy `NetworkService` 移入 `app.legacy`，运行时依赖层不再暴露旧连接服务初始化入口，`/network` 写接口继续返回 410。验证 `tests/test_run_startup_config.py tests/test_backend_security_and_connection_policy.py` 为 `53 passed`，`run.py --help` 可正常加载，局部 `ruff check` 与 `verify-launch-scripts.ps1` 通过。
- 2026-05-23：完成 Phase 3 第一项整改：`backend/app/models/ai.py`、`backend/app/models/terminal.py` 迁移为 Pydantic v2 `field_validator` 与 `ConfigDict` 写法，并同步清理旧 network 模型 `class Config`；新增隔离子进程测试把 Pydantic v1 弃用警告提升为错误。验证 `tests/test_pydantic_v2_models.py tests/test_backend_security_and_connection_policy.py tests/test_terminal_connection_regressions.py` 为 `62 passed`，模型局部 `ruff check` 通过，Pydantic v1 弃用警告消失。
- 2026-05-23：完成 Phase 3 第二项整改：将 `backend/pyproject.toml` 的 `requires-python` 收紧为 `>=3.9,<3.13`，并通过 `uv lock` 同步 `backend/uv.lock`，在替换 `telnetlib` 前显式排除 Python 3.13 及以上运行环境；新增包元数据回归测试校验 pyproject 与锁文件 Python 版本边界一致。验证 `tests/test_backend_package_metadata.py` 为 `2 passed`，`uv pip check` 通过，局部 `ruff check` 通过。
- 2026-05-23：完成 Phase 3 第三项整改：明确 `backend/pyproject.toml + backend/uv.lock` 为后端依赖权威来源，`backend/requirements.txt` 仅保留为生成产物并添加禁止手工编辑说明；新增 Python 包元数据测试和 PowerShell runtime dependency 校验，要求 requirements 运行依赖与 `[project].dependencies` 完全同步。验证 `tests/test_backend_package_metadata.py` 为 `3 passed`，`verify-backend-runtime-dependencies.ps1` 通过，局部 `ruff check` 通过。
- 2026-05-23：完成 Phase 3 第四项整改：移除后端 pytest 默认 `--cov`、`--cov-report` 和 `htmlcov` 生成参数，保留 `[tool.coverage.*]` 配置和显式覆盖率命令，普通测试默认不再生成覆盖率产物；新增配置回归测试防止默认 coverage 参数回流。验证 `tests/test_pytest_cache_config.py` 为 `2 passed`，从 `backend` 目录直接运行同一测试也为 `2 passed`，局部 `ruff check` 通过。
- 2026-05-23：完成 Phase 3 第五、第六项整改：新增 `scripts/backend-check.ps1` 与 `scripts/backend-check.sh`，串联 `uv pip check`、后端依赖声明校验、当前已治理后端范围的定向 `ruff check`、后端定向 pytest 和启动脚本契约校验；新增 AST 架构边界测试，禁止 `services/*` 导入 FastAPI、`models/*` 导入 logger、`core/*` 依赖 API 层，并移除 `backend/app/models/ai.py` 对日志实现的直接依赖。验证 Windows PowerShell 版与 Git Bash 版 `backend-check` 均通过，默认后端检查为 `71 passed`，`tests/test_architecture_boundaries.py` 为 `3 passed`，`verify-launch-scripts.ps1` 通过。
- 2026-05-23：完成 Phase 3 第七项整改：为 `run.py` 增加 `ENV_FILE` 覆盖能力，默认仍加载 `backend/.env`；新增真实启动链路测试，用临时 env 文件和假 `uvicorn` 模块在子进程中验证 `.env` 加载、参数解析和 `uvicorn.run` 的 `app`、`host`、`port`、`reload`、`log_level` 参数传递，不占用真实端口。验证 `tests/test_run_startup_config.py` 为 `2 passed`，Windows PowerShell 与 Git Bash 版 `backend-check` 均通过，默认后端检查为 `72 passed`。
- 2026-05-23：完成 Phase 4 第一项整改：新增 `backend/app/core/network/telnet/client.py`，用最小 socket-based Telnet 客户端替代 Python 3.13 已移除的标准库实现，覆盖 `open`、`expect`、`read_until`、`read_very_eager`、`write`、`close` 和基础 IAC 协商处理；基础 Telnet 与华为 Telnet 连接不再导入 `telnetlib`，原有登录和分页判断测试继续通过。验证 `tests/test_telnet_login_policy.py tests/test_terminal_connection_regressions.py tests/test_backend_security_and_connection_policy.py` 为 `65 passed`，Windows PowerShell 与 Git Bash 版 `backend-check` 均通过，默认后端检查为 `76 passed`，未再出现 `telnetlib` 弃用警告；Python 上限本轮暂不放宽，等待单独的 3.13 运行矩阵验证。
- 2026-05-23：完成 Phase 4 第二项整改：新增 `backend/app/core/rate_limit.py`，定义 `RateLimiterBackend` 协议、内存滑动窗口后端、路径级 `RateLimitRule` 和 `RateLimitMiddleware`，默认对 `/ai` 与 `/terminal` 接口按客户端维度限流，并支持通过 `app.state.rate_limiter` 替换为 Redis 或网关适配器；429 响应包含 `Retry-After`、`X-RateLimit-Limit`、`X-RateLimit-Remaining`、`X-RateLimit-Reset`，通过请求也返回剩余额度头。验证限流定向测试为 `2 passed`，`tests/test_backend_security_and_connection_policy.py tests/test_terminal_connection_regressions.py tests/test_telnet_login_policy.py` 为 `67 passed`，Windows PowerShell 与 Git Bash 版 `backend-check` 均通过，默认后端检查为 `78 passed`。
- 2026-05-23：完成 Phase 4 剩余四项整改：新增协议级 fake SSH/Telnet/AI 测试，覆盖分页、断连和流式错误；新增统一 API 错误响应工具和全局异常处理，validation、鉴权、业务异常、上游异常与限流错误统一输出 `{ "error": { "code": "...", "message": "...", "request_id": "...", "details": [] } }`；新增 `X-Request-ID` 透传/生成中间件和日志上下文注入；将 `/health` 改为轻量存活检查，并新增 `/health/ready` 检查本地配置和应用资源状态；同步 Windows PowerShell 与 Git Bash 版 `backend-check` 默认目标，纳入本轮新增测试和工具模块。验证新增定向测试 `tests/test_protocol_fake_services.py tests/test_api_error_contract.py tests/test_request_id_tracing.py tests/test_health_readiness.py` 为 `15 passed`；关联回归 `tests/test_backend_security_and_connection_policy.py tests/test_terminal_connection_regressions.py tests/test_telnet_login_policy.py` 为 `67 passed`；合并关联验证为 `82 passed`；本轮触达文件 `ruff check` 通过；Windows PowerShell 与 Git Bash 版 `scripts/backend-check` 均通过，默认后端检查为 `93 passed`。
