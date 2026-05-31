# AI 助手「高级网络安全架构师」角色提示词设计

> 日期：2026-05-31
> 状态：已确认，待实现
> 关联模块：`backend/app/services/ai/`

## 1. 背景与目标

本项目是「AI 智能网络故障分析平台」，AI 助手支持 Claude / GPT / Deepseek 多模型流式对话。
在改造前，**主聊天链路没有任何固定的角色 system prompt**——前端 `formatMessages()` 只透传
`{role, content}`，后端 `application_service` 仅在 `enable_search=true` 时注入搜索结果。
唯一的角色设定硬编码在独立的 `deepseek/analyzer.py`（"你是一名资深的网络工程师…"），
且仅服务于日志分析器，与主聊天助手是两条独立链路。

**目标**：为 AI 助手注入统一的「高级网络安全架构师」角色，**网络与安全双视角并重、以网络为主体**，
覆盖主聊天助手与日志分析器两条链路，口径一致。

## 2. 需求决策（已与用户确认）

| 维度 | 决策 |
|------|------|
| 作用范围 | 主聊天助手 **+** 日志分析器，两条链路口径统一 |
| 文案来源 | 由助手起草，用户确认 |
| 实现形式 | 抽成常量 + 统一注入；**不**引入环境变量开关（YAGNI） |
| 角度侧重 | 网络为主体、安全为并列增强维度，两者并重 |

## 3. 架构分析：注入点选择

消息流转链路：

```
前端 formatMessages() ──{role,content}──▶ POST /api/ai/chat/stream
  └▶ application_service.chat_stream() → generate_text_stream()
        ├─ _maybe_inject_search()   仅 enable_search 时 insert(0, 搜索 system)
        └─ ai_manager.chat_stream() ──按模型前缀路由──▶ provider.chat_stream()
              └▶ _build_*_payload(): 把 request.messages 原样转发给上游
```

**结论**：三个 provider 都只是"忠实转发者"，自身不注入角色。若把 persona 写在 provider 层会
重复三遍（违反 DRY）。`application_service` 是唯一的、所有模型共享的编排层，且已有
`_maybe_inject_search()` 的 `insert(0, system)` 范式可复用——**这是主聊天链路的最佳注入点**。

日志分析器链路独立，直接在 `analyzer.py` 引用同一常量即可。

## 4. 实现方案

### 4.1 常量模块 `backend/app/services/ai/prompts.py`（新增）

- `_ARCHITECT_IDENTITY`：共享角色称谓，保证两条链路口径统一（改称谓只改一处）；
- `NETWORK_SECURITY_ARCHITECT_PERSONA`：主聊天助手完整人设；
- `NETWORK_LOG_ANALYST_SYSTEM`：日志分析器聚焦版（共享称谓 + 日志分析任务定位）。

设计取舍：能力清单刻意以"网络架构 / 故障诊断与性能 / 多厂商运维"为前三项、
"网络安全"为并列第四项——**清单顺序与篇幅占比即是给模型的注意力先验**，
用结构而非形容词确保"网络为主体、安全为增强"。

### 4.2 主聊天链路 `application_service.py`

新增 `_inject_persona(request)`，在 `generate_text_stream` 中于 `_maybe_inject_search`
**之后**调用，再 `insert(0, persona)`：

```
最终消息顺序 = [persona(system), 搜索上下文(system)?, ...用户消息]
```

**注入顺序的依据**：persona 是稳定身份，必须先于临时检索上下文；若 persona 排在搜索 block
之后，模型容易被后插入的大段搜索文本"盖过"角色设定。注入对 `enable_search` 与否都无条件执行。

### 4.3 日志分析器 `deepseek/analyzer.py`

第 102 行（`analyze_network_log`）、第 162 行（`analyze_log_stream`）两处硬编码 system
改为引用 `NETWORK_LOG_ANALYST_SYSTEM`。

## 5. 测试影响与适配

persona 无条件注入到 `messages[0]`，会改变 `test_chat_with_search.py` 中 3 处对消息结构的断言
（这是行为的预期变化，而非回归）：

| 测试 | 原断言 | 适配后 |
|------|--------|--------|
| `..._injects_system_and_returns_sources` | `messages[0]` 含搜索内容 | `messages[0]` 为 persona，搜索 block 顺延到 `messages[1]` |
| `..._does_not_call_brave` | `messages[0].role == "user"` | `messages[0]` 为 persona，`messages[1]` 为 user |
| `..._empty_results_marks_failed` | `messages[0].role == "user"` | `messages[0]` 为 persona，无搜索 block |

测试将 `import NETWORK_SECURITY_ARCHITECT_PERSONA`，显式断言"`messages[0]` 恒为 persona"，
再验证搜索 block 的相对位置；并**新增** `test_chat_stream_always_injects_persona_first`
锁定"无论是否搜索都注入 persona"的新契约。

`test_backend_security_and_connection_policy.py` 的两个流式测试用 `FakeAIManager` 忽略
`request`、只校验 SSE 结构，不受影响。

## 6. 验证标准

- [ ] `scripts/backend-check`（或 pytest）全绿，含适配后的搜索注入测试与新增 persona 测试；
- [ ] `scripts/lint` ruff 通过；
- [ ] 人工核对：persona 注入后 `messages[0]` 为角色 system，搜索场景顺序正确；
- [ ] 提交前 secret 扫描无误。

## 7. 约束边界

- `Message.content` 上限 8000 字符、全部消息合计 32000 字符；persona 约 600 字，余量充足。
- 不改前端：注入在后端完成，前端 `formatMessages()` 逻辑不动。
