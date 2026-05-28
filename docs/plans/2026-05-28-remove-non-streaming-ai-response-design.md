# 非流式 AI 响应残留清理设计文档

> **状态**：已设计 / 待执行
> **创建日期**：2026-05-28
> **作者**：架构清理任务
> **关联**：前端 AI 助手已于 commit `00fa82c feat(ai-assistant): 默认使用流式响应` 移除流式/非流式切换按钮

---

## 1. 背景与动机

前端 UI 在 commit `00fa82c` 之后已经**强制走 SSE 流式响应**，移除了"流式/非流式"切换按钮。然而**整条非流式调用链在后端、模型、测试、文档中完整保留**，形成：

| 残留类型 | 具体表现 |
|---|---|
| 死路由 | `POST /api/v1/ai/chat`、`POST /api/v1/ai/deepseek/generate` 双模式 endpoint 仍对外暴露 |
| 死调用链 | `endpoints.ai.chat → ApplicationService.chat → AIServiceManager.chat → {Deepseek,OpenAI,Claude}Provider.chat → ChatResponse / _error_chat_response` |
| 死类型 | `ChatResponse` 模型、`DeepseekGenerateRequest.stream` 字段 |
| 误导文档 | README、`docs/project-architecture-and-system-overview.md` 仍宣传"流式/非流式切换" |
| 误导测试 | `tests/test_chat_with_search.py` 用 `service.chat(...)` 测 Brave Search 注入 |

**清理目标**：
- 前端、后端、文档**只剩流式一条路径**
- 后端不再对外暴露任何"非流式" endpoint
- 测试覆盖率不下降（横切测试改打 `/chat/stream`，业务测试改测 `chat_stream`）
- **流式实现的代码、日志、注释、变量名（含上游 API 协议字段 `stream=True/False`）全部保留**

---

## 2. 调研发现（Read-only Explore 结论）

### 2.1 流式实现已完全自洽

- `manager.chat_stream` 直接调用 `provider.chat_stream`，**不经过** `chat()`
- 每个 provider 的 `chat_stream` 用 `_error_stream_event` 处理错误，**不调用** `_error_chat_response`
- `application_service.chat_stream` 完整封装错误处理与 search 注入

### 2.2 架构守护测试已经在向这个方向演进

`tests/test_backend_security_and_connection_policy.py:667` 已有断言：
```python
assert "ai_manager.chat(" not in route_source
assert "ai_manager.chat_stream(" not in route_source  # 已禁止路由直接编排
```
本次清理是**延续既定演进路径**，不是破坏性改动。

### 2.3 子类完整集合

`AIProviderBase` 只有 3 个子类（`DeepseekProvider` / `OpenAIProvider` / `ClaudeProvider`），全部 `chat()` 实现都是非流式，可安全删除抽象方法。

### 2.4 `ChatRequest.stream` 字段的真实读取点

| 位置 | 用途 | 处置 |
|---|---|---|
| `application_service.py:104 request.stream = True` | 流式入口兜底（客户端漏传时强制为 True） | **保留** |
| `application_service.py:210, 213` | `/deepseek/generate` 非流式分支判断 | **删除**（随 `/deepseek/generate` 一并删） |
| `provider._build_*_payload(request, stream=True)` | **上游 API 协议字段**，与本项目开关无关 | **保留** |

### 2.5 测试依赖矩阵

| 测试文件 | 用法 | 处置 |
|---|---|---|
| `tests/test_chat_with_search.py` | 用 `service.chat()` 测 Brave Search 注入业务（5 个测试） | **迁移到 `chat_stream` 版**：新建 `_consume_stream` helper，断言 `search_results` SSE 事件 |
| `tests/test_backend_security_and_connection_policy.py` | 用 `"/api/v1/ai/chat"` 测鉴权/限流横切关注点（多处） | **URL 全局替换为 `/chat/stream`** |
| `tests/test_api_error_contract.py` | 同上（多处） | 同上 |
| `tests/test_request_id_tracing.py` | 同上（1 处） | 同上 |

---

## 3. 清理范围（保留 vs 删除）

### 3.1 A 档：必须清理

| # | 位置 | 内容 | 操作 |
|---|---|---|---|
| A1 | `backend/app/api/api_v1/endpoints/ai.py` | `@router.post("/chat")` 路由 | 整段删 |
| A2 | `backend/app/api/api_v1/endpoints/ai.py` | `@router.post("/deepseek/generate")` 路由 | 整段删 |
| A3 | `backend/app/services/ai/application_service.py` | `chat()`、`generate_text()`、`_generate_deepseek_stream()` | 整方法删 |
| A4 | `backend/app/services/ai/manager.py` | `chat()` 非流式方法 | 整方法删 |
| A5 | `backend/app/services/ai/providers/{deepseek,openai,claude}_provider.py` | `chat()` + `_parse_*_response()` | 整方法删（先核对 `_parse_*_response` 仅被 `chat()` 调用） |
| A6 | `backend/app/services/ai/base.py` | 抽象 `chat()` + `_error_chat_response()` | 整方法删 |
| A7 | `backend/app/models/ai.py` | `class ChatResponse` 模型 | 整类删 |
| A8 | `backend/app/models/ai.py` | `class DeepseekGenerateRequest` 模型 | 整类删 |
| A9 | `README.md` 多处 | "流式/非流式切换"、"POST /api/v1/ai/chat"、"POST /api/v1/ai/deepseek/generate" | 删/改 |
| A10 | `docs/project-architecture-and-system-overview.md` | 12.2 节、L226-227、L723、L814、L27 措辞 | 删/改 |

### 3.2 B 档：必须保留

| 内容 | 位置 | 保留理由 |
|---|---|---|
| `ChatRequest.stream: bool = Field(False, ...)` | `models/ai.py:94` | 字段名虽叫 stream，但作用是**作为流式入口的兜底参数**与**向上游 API 透传**；无外部入口能切非流式，留着无害 |
| `request.stream = True` 兜底赋值 | `application_service.py:104` | 客户端漏传字段时强制走流式 |
| `_build_{claude,openai,deepseek}_payload(stream=True)` 形参 | 各 provider | **上游 OpenAI/DeepSeek/Anthropic API 协议字段** |
| 前端 `aiService.ts`、`messaging.ts` 中"流式响应"注释/日志 | 前端 | 描述当前实现，准确无误导 |
| 前端 `store.sendMessage` 包装 + retry 路径 | `messaging.ts:30, 558` | 是流式入口的便利包装；retry 复用此入口；保留 |
| `docs/backend-optimization-remediation-plan.md:87` 历史规划条目 | docs | 已标 `[x]` 完成，是历史记录 |
| 所有 `tests/` 中"流式 SSE 契约"相关测试 | tests/ | 是流式实现的回归保护 |
| `scripts/` 下所有脚本 | scripts/ | 无非流式调用 |

---

## 4. 五阶段执行顺序

每阶段独立 commit，独立可回滚。

### 阶段 1：测试迁移（前置必做）

> 不先迁移测试，后续阶段 2-4 会断 CI。

**1.1 业务测试（`tests/test_chat_with_search.py`）**

新增 helper：
```python
async def _consume_stream(result: AIStreamingResult) -> dict[str, Any]:
    """收集 SSE 事件流，返回 {sources, search_failed, content}。"""
    events = {"sources": [], "search_failed": False, "content": ""}
    async for line in result.chunks:
        if line.startswith("event: search_results"):
            # 解析下一行 data: { sources, search_failed }
            ...
        elif line.startswith("event: content"):
            ...
    return events
```

把 5 个测试中的：
```python
response = await service.chat(request)
assert response.sources == [...]
```
改为：
```python
result = service.chat_stream(request)
events = await _consume_stream(result)
assert events["sources"] == [...]
```

**1.2 横切测试 URL 替换**

在 `tests/test_backend_security_and_connection_policy.py`、`tests/test_api_error_contract.py`、`tests/test_request_id_tracing.py` 中：
- 全局替换 `"/api/v1/ai/chat"` → `"/api/v1/ai/chat/stream"`
- 删除 `ChatResponse` 的 import
- 删除测试里构造 `ChatResponse(...)` 的 fake AI manager 返回（参考 line 86、127）—— 改为 fake `chat_stream` 异步生成器

**1.3 验证**
```powershell
.\scripts\backend-check.ps1
```
所有测试 green，包含已迁移的业务测试与横切测试。

**Commit message**：`refactor(ai): 阶段1 测试迁移到流式（删 ChatResponse 业务断言）`

---

### 阶段 2：路由清理

**文件**：`backend/app/api/api_v1/endpoints/ai.py`

操作：
- 删 `@router.post("/chat")` 整段（line 70-79）
- 删 `@router.post("/deepseek/generate")` 整段（line 113-126）
- 清理顶部 import：删 `ChatResponse`、`DeepseekGenerateRequest`、`AIStreamingResult`（如不再被其他路由使用）

**验证**：
```powershell
.\scripts\backend-check.ps1
# 期望：所有测试 pass
# 期望：curl http://127.0.0.1:8000/api/v1/ai/chat -X POST → 404
```

**Commit message**：`refactor(ai): 阶段2 移除非流式 /chat 与 /deepseek/generate endpoint`

---

### 阶段 3：调用链清理（自顶向下）

按调用关系自顶向下，每删一层立即跑测试：

1. `application_service.py`：删 `chat()`（line 75-96）+ `generate_text()`（line 198-225）+ `_generate_deepseek_stream()`（line 227-*）+ 顶部 `ChatResponse` import
2. `manager.py`：删 `chat()`（line 126-138）+ 顶部 `ChatResponse` import
3. `providers/deepseek_provider.py`：删 `chat()`（line 109-130）+ `_parse_deepseek_response()`（line 206-230）+ 顶部 `ChatResponse` import
4. `providers/openai_provider.py`：删 `chat()`（line 78-103）+ `_parse_chat_response()`（line 167-185）+ 顶部 `ChatResponse` import
5. `providers/claude_provider.py`：删 `chat()`（line 81-107）+ `_parse_claude_response()`（line 173-195）+ 顶部 `ChatResponse` import
6. `base.py`：删抽象 `chat()`（line 91-93）+ `_error_chat_response()`（line 167-190）+ 顶部 `ChatResponse` import

**验证**：
```powershell
# 全局检查残留
Get-ChildItem -Recurse backend\app -Filter *.py | Select-String -Pattern "ChatResponse|_error_chat_response|ai_manager\.chat\(|provider\.chat\("
# 期望：仅 models/ai.py 自身的 ChatResponse 定义（阶段 4 才删）

.\scripts\backend-check.ps1
```

**Commit message**：`refactor(ai): 阶段3 移除 chat() 调用链（application_service/manager/provider/base）`

---

### 阶段 4：类型与字段清理

**文件**：`backend/app/models/ai.py`

操作：
- 删 `class ChatResponse(BaseModel)` 整类（line 177-*）
- 删 `class DeepseekGenerateRequest(BaseModel)` 整类（line 232-260）
- **保留** `ChatRequest.stream` 字段 default=False 与 description 不动（理由见 §3.2）

**验证**：
```powershell
Get-ChildItem -Recurse backend\app -Filter *.py | Select-String -Pattern "ChatResponse|DeepseekGenerateRequest|payload\.stream"
# 期望：零结果

.\scripts\backend-check.ps1
```

**Chrome MCP 端到端验证**：
1. 启动 `.\scripts\dev.ps1`
2. 用 Chrome MCP 打开页面
3. 发一次完整对话
4. 期望：SSE 流式 thinking + content 正常显示，前端无任何破坏

**Commit message**：`refactor(ai): 阶段4 移除 ChatResponse 与 DeepseekGenerateRequest 模型`

---

### 阶段 5：文档同步

**5.1 README.md**

| 行 | 旧 | 新 |
|---|---|---|
| L3 | "提供流式响应界面，实现实时网络设备连接和命令执行" | **保留**（已准确） |
| L211 | `### 流式响应与交互体验` | **保留** |
| L213 | `- **流式模式切换**：支持流式/非流式模式灵活切换` | **删除整行** |
| L636 | `- POST /api/v1/ai/chat: 非流式AI对话接口` | **删除整行** |
| L646 | "支持流式响应，多种模型切换" | "使用 SSE 流式响应，多种模型切换" |
| L674 | "支持多模型选择和流式响应" | "支持多模型选择，使用 SSE 流式响应" |

**新增 BREAKING CHANGE 提示**（位置：`## API 接口` 章节标题下方）：

```markdown
> ⚠️ **BREAKING CHANGE（2026-05-28）**：
> `POST /api/v1/ai/chat` 与 `POST /api/v1/ai/deepseek/generate` 非流式 / 双模式接口已于本版本移除。
> AI 对话请统一使用 `POST /api/v1/ai/chat/stream`（SSE 流式响应）。
```

**5.2 docs/project-architecture-and-system-overview.md**

| 行 | 旧 | 新 |
|---|---|---|
| L27 | "支持模型列表加载、模型连通性检查、普通响应和流式响应。" | "支持模型列表加载、模型连通性检查、流式响应。" |
| L226-227 | `- POST /api/v1/ai/chat: 非流式 AI 对话。` | **删除整行** |
| L723 | `- 流式响应开关。` | **删除整行** |
| L814 | `- 切换流式响应。` | **删除整行** |
| L857-872 | `### 12.2 AI 非流式对话` 整节 | **整段删除**，调整后续章节编号 |
| L390 | "支持流式响应" | **保留**（描述事实） |

**5.3 验证**：
```powershell
# 检查残留（应零结果）
Select-String -Path README.md, docs\*.md -Pattern "非流式|流式/非流式" -Exclude "backend-optimization-remediation-plan.md"
Select-String -Path README.md, docs\*.md -Pattern "/api/v1/ai/chat\b" -NotMatch "/chat/stream"
```

**Commit message**：`docs(ai): 阶段5 同步流式专属文档（含 BREAKING CHANGE 提示）`

---

## 5. 关键文件清单

| 阶段 | 文件 | 操作 |
|---|---|---|
| 1 | `tests/test_chat_with_search.py` | 改业务测试为流式版 + 新增 `_consume_stream` helper |
| 1 | `tests/test_backend_security_and_connection_policy.py` | URL 全局替换 + 删 ChatResponse import + 改 fake AI manager |
| 1 | `tests/test_api_error_contract.py` | URL 全局替换 |
| 1 | `tests/test_request_id_tracing.py` | URL 全局替换 |
| 2 | `backend/app/api/api_v1/endpoints/ai.py` | 删 /chat + /deepseek/generate 路由 + 清理 import |
| 3 | `backend/app/services/ai/application_service.py` | 删 chat / generate_text / _generate_deepseek_stream |
| 3 | `backend/app/services/ai/manager.py` | 删 chat() |
| 3 | `backend/app/services/ai/providers/deepseek_provider.py` | 删 chat() + _parse_deepseek_response |
| 3 | `backend/app/services/ai/providers/openai_provider.py` | 删 chat() + _parse_chat_response |
| 3 | `backend/app/services/ai/providers/claude_provider.py` | 删 chat() + _parse_claude_response |
| 3 | `backend/app/services/ai/base.py` | 删抽象 chat + _error_chat_response |
| 4 | `backend/app/models/ai.py` | 删 ChatResponse 类 + DeepseekGenerateRequest 类 |
| 5 | `README.md` | 删/改 5 处 + 加 BREAKING CHANGE 提示 |
| 5 | `docs/project-architecture-and-system-overview.md` | 删/改 5 处 + 整段 12.2 |

**预估总变更量**：约 360 行死代码与误导文档被清除；前端代码 0 行改动。

---

## 6. 验证矩阵

| 阶段 | 验证手段 | 期望结果 |
|---|---|---|
| 阶段 1 | `.\scripts\backend-check.ps1` | 全部测试 green |
| 阶段 2 | `curl http://127.0.0.1:8000/api/v1/ai/chat -X POST` | 404；`/chat/stream` 仍 200 |
| 阶段 3 | `Select-String -Recurse backend\app -Pattern "ChatResponse\|_error_chat_response\|ai_manager\.chat\("` | 仅 `models/ai.py` 自身定义剩余 |
| 阶段 4 | Chrome MCP：发一次完整对话 | SSE 流式 thinking + content 正常 |
| 阶段 5 | grep README.md/docs/ `非流式` `流式/非流式` `/api/v1/ai/chat` | 零结果（历史规划标 [x] 行除外） |
| 全局 | `git diff --stat` | 仅修改本清单文件；前端代码 0 行 |

---

## 7. 风险与回滚

| 风险 | 缓解 | 回滚 |
|---|---|---|
| 阶段 1 测试 helper 与现有 fake AI manager 不兼容 | 阶段 1 单独 commit | `git revert <阶段1 commit>` |
| 阶段 2 后外部脚本/Postman 仍打 `/chat` | 阶段 5 BREAKING CHANGE 提示用户迁移 | 阶段 2 单独 commit 可回 |
| 阶段 3 漏 import 导致服务启动失败 | 每删一层立即 `python -c "import app.main"` + backend-check | 单层 commit 可单独回 |
| 阶段 4 字段 `ChatRequest.stream` 被未识别处使用 | grep 全局确认零结果后再决定是否删（本方案选择保留） | 字段保留风险更低 |
| 文档表达失误 | 人工逐行审阅 | git revert 文档 commit |

每阶段独立 commit，回滚成本最低。

---

## 8. 不修改的内容（明确边界）

- 任何前端代码（`AIAssistant.vue`、`messaging.ts`、`aiService.ts`、`connection.ts`、`ModelSelector.vue` 等）
- 任何流式实现的代码、日志、注释
- `provider._build_*_payload(stream=...)` 的 `stream` 形参 —— 上游 API 协议字段
- `application_service.chat_stream` 内 `request.stream = True` 兜底
- `ChatRequest.stream` 字段定义（仅保留，不动）
- `docs/backend-optimization-remediation-plan.md:87` 已完成的历史规划条目
- `scripts/` 下任何脚本

---

## 9. 后续追踪（执行后补充）

> 执行完毕后在此区域补充：
> - [ ] 阶段 1 commit SHA：
> - [ ] 阶段 2 commit SHA：
> - [ ] 阶段 3 commit SHA：
> - [ ] 阶段 4 commit SHA：
> - [ ] 阶段 5 commit SHA：
> - [ ] 真实环境验证记录：
> - [ ] 实测删除行数（vs 预估 360 行）：
