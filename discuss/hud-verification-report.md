# Industrial HUD 大改造 — 前端验证报告

> 验证日期：2026-05-31
> 验证范围：H0–H7 工作区改造（未提交）的动态层验证（编译 / 渲染 / a11y / 双模式目测）
> 验证方式：纯验证 + 浏览器双模式目测，未修改任何源码 / git
> 环境：Windows，前端 5180 / 后端 8000，dev 经 `scripts/dev.ps1` 启动，后端健康检查通过
> 截图目录：`discuss/hud-shots/`；axe 报告：`discuss/redesign-p6/p6-axe-report.json`

---

## 一、代码层（lint / typecheck / build）

### 1. TypeScript 类型检查（vue-tsc --noEmit）—— ❌ 1 个 ERROR（阻塞）

```
src/components/ai-assistant/components/MessageBubble.vue(15,6): error TS2379:
Argument of type '{ thinking: ThinkingContent; isStreaming: boolean; defaultExpanded: boolean | undefined; }'
is not assignable to parameter ... with 'exactOptionalPropertyTypes: true'.
  Types of property 'defaultExpanded' are incompatible.
    Type 'boolean | undefined' is not assignable to type 'boolean'.
```

- **严重度：阻塞（blocking）**
- **位置**：`frontend/src/components/ai-assistant/components/MessageBubble.vue:19`
  绑定 `:default-expanded="isLastAssistant"`。
- **根因**：`MessageBubble` 的 `isLastAssistant` 是可选 prop（`isLastAssistant?: boolean`，`MessageBubble.vue:84`），其类型为 `boolean | undefined`。`tsconfig.json:20` 开启了 `exactOptionalPropertyTypes: true`，因此把 `boolean | undefined` 显式传给 `ThinkingBlock` 的 `defaultExpanded?: boolean`（`ThinkingBlock.vue:80`）被拒绝——显式绑定要求值精确为 `boolean`。
- **触发阶段**：H5（MessageBubble 引入 ThinkingBlock 的 `default-expanded` 绑定）。
- **建议修复方向**（任选其一，均为 1 行）：
  1. `MessageBubble.vue:19` 改为 `:default-expanded="isLastAssistant ?? false"`；或
  2. 把 `withDefaults` 已给了默认值 `isLastAssistant: false`（`MessageBubble.vue:90`），改用 `:default-expanded="props.isLastAssistant"` 仍是 `boolean | undefined`——根因在 prop 可选性，仍需 `?? false`；或
  3. 将 `isLastAssistant` 改为必选 prop（去掉 `?`），父组件已传值时最干净。

### 2. ESLint —— ✅ 全绿

`npm run lint`（eslint . --ext .vue,.js,.cjs,.mjs,.ts,.tsx,.cts,.mts）独立运行，**0 error / 0 warning**，退出码 0。
（注：`lint.ps1` 先跑 typecheck，因 typecheck 失败而中止，ESLint 不会被脚本执行到；本报告单独跑了 ESLint 确认其全绿。）

### 3. 生产构建（vue-tsc && vite build）—— ❌ 失败（被 typecheck 阻塞）

- `package.json:8` 的 build 脚本是 `"vue-tsc && vite build"`，`&&` 短路：vue-tsc 失败后 **vite build 根本不会执行**，**dist 未产出**，无法统计体积。
- 失败信息与上面 typecheck 完全一致（同一处 TS2379）。
- **结论**：修复第 1 条 typecheck 错误后，build 才能跑通。这是唯一的构建阻塞点。

> 备注：dev server（Vite/esbuild）不做类型检查，因此尽管 typecheck/build 失败，开发环境仍能正常渲染——下面的浏览器目测均在 dev server 上完成且界面正常。

---

## 二、视觉问题（按 H 阶段 + Dark/Light 分类）

> 总体观感：HUD 改造完成度高，双模式翻转干净，工业 HUD 语言（深空琥珀辉光 / 暖纸暗琥珀印刷 + 1px 双层网格 + 四角 L 角标 + scanline + 等宽坐标数据）落地到位。以下按阶段列出确认项与少量问题。

### H0 品牌名 + meta —— ✅ 通过
- 顶栏品牌「NETOPS」+ 副标题「AI 网络故障智能分析平台」（`light-topbar.png` / `dark-topbar.png`）。
- 命令面板「关于本平台」副标题「NetOps · AI 网络故障智能分析平台」（`dark-command-palette.png`）。
- 全仓 grep `驾驶舱` / `PacketSignal` **零结果**，确认旧名与旧组件引用已清除。

### H1 tokens.css 双模式 —— ✅ 通过
- 实测 `getComputedStyle`：Dark `--background = oklch(0.09 0.012 230)`（深空黑）、`--primary = oklch(0.82 0.16 80)`（琥珀主灯）；Light `--background = oklch(0.96…)`（暖纸）。token 翻转正确。
- 圆角 `--radius: 0.25rem`（HUD 锐利感）已生效。

### H2 主网格背景（NetworkTopologyBackground）—— ✅ 通过
- DOM 实测：全局唯一一个 `.hud-bg`（挂在 `netops-shell`）。双层网格 96px 粗 + 16px 细可见且克制（`dark-ai-empty.png` 网格清晰但不喧宾）。
- **四角 L 角标全部存在**：实测 4 个 corner，琥珀色 `oklch(0.6 0.1 80 / 0.45)`，20×20px，分别位于视口四角（10px 内缩）。
- scanline 实测在动（`hud-scan` 动画，4s，opacity 1，高度 = 视口 42%）。

### H3 HUD 装饰组件（HudFrame / ScanlineSweep）—— ✅ 通过
- `HudFrame.vue`：四角 L 角标 + 可选 label + `active/bordered/corners` props 完整；`:focus-within` 点亮（焦点框有职责，非纯装饰）。AI 面板 label「AI ASSISTANT」、终端面板 label「TERMINAL」均正确渲染。
- `ScanlineSweep.vue`：三态（idle/scanning/done）+ 琥珀光束辉光 + reduced-motion 处理齐全。

### H4 顶栏 + 主区 —— ✅ 通过（除下方 a11y drag-handle 项）
- mission-clock 实时跳动：跨多张截图观察到 01:10:51 → 01:11:23 → 01:22:23 连续走时，**真实时间**，mono 字体 + bracket 框。
- ⌘K 按钮、brand L 角标 logo、主题切换（月/日图标）均正常。

### H5 AI 助手面板 —— ✅ 通过
- EmptyState（`dark-ai-empty.png` / `light-ai-panel.png`）：`[ AI ]` mono 琥珀 bracket 标签 + 「AI 助手就绪」+ 4 张诊断预设卡（mono 序号 01–04 琥珀），**无 emoji**，网格底可见。完成度很高。
- ThinkingBlock 已用 ScanlineSweep 替换（代码确认，`ThinkingBlock.vue:19,24`）。
- 模型选择器、联网搜索开关、清空对话按钮齐全。

### H6 终端面板 —— ✅ 通过
- 终端永远暗底（`light-viewport.png` 中浅色模式下终端仍为深色块，符合设计），琥珀 hairline，「连接」/「发送」按钮琥珀，`$` 暖白 prompt，状态文案正常。

### H7 命令面板 + BottomTabBar + ServerStatus —— ✅ 通过
- 命令面板（`dark-command-palette.png`）：深空底 + **active item 琥珀左 bracket 高亮** + 分组（对话/主题/导航/设置）+ 快捷键徽标 + 底部 ↑↓/↵/Esc 提示。
- BottomTabBar（移动端）：active tab 琥珀 + 顶部 1px 琥珀指示线（`mobile-375-*.png`）。
- ServerStatusIndicator：绿色脉冲状态灯 +「服务器已连接」。

### 视觉问题清单
| # | 严重度 | 位置 | 现象 | 截图 | 建议 |
|---|--------|------|------|------|------|
| V1 | 次要 | AI 面板 header（768 断点） | 768px 进入双面板模式后 AI 面板偏窄，header 工具条拥挤：「联网搜索」label 竖排折行（联/网/搜/索），模型名截断为「De…」 | `mobile-768.png` | 768 断点可考虑保持单面板（移动布局），或 AI header 在窄宽下隐藏「联网搜索」文字仅留图标/开关 |
| V2 | 次要 | AI pane / prompt-card（768 断点） | 实测 `netops-pane--ai` 与部分 `prompt-card` 的 right 边缘超出视口 3–6px（772–775 vs 769），被裁剪、无页面级横向滚动条 | `mobile-768.png` | 收紧 768 断点下 AI pane 的右内边距 / card 宽度计算 |

> Light 暖纸底偏接近 off-white（非强烈纸张感），属设计取向判断，未列为缺陷。

---

## 三、a11y / 对比度

### axe-core 多视口审计（`scripts/p6_axe_audit.py`，4 视口）

| 视口 | violations | 说明 |
|------|-----------|------|
| mobile-375-light | 1 | color-contrast |
| mobile-375-dark | 0 | — |
| tablet-768-light | 0 | — |
| desktop-1280-dark | 1 | button-name |

合计 **2 个 violation**，脚本退出码 1（未满足 0 violation + 全图标 aria-hidden 的严格门槛）。

#### A1 — `button-name`（critical），desktop dark
- **位置**：`frontend/src/components/layout/DragHandle.vue`（`.drag-handle`）。
- **现象**：`<button role="separator">` 仅含一个空 `<span class="drag-handle__bar"/>`，**无可辨识名称**（无 aria-label / 无文本）。axe 判定 critical「Buttons must have discernible text」。仅在桌面宽度（出现拖拽分割条时）触发。
- **建议**：给该 button 补 `aria-label="调整面板宽度"`（1 行）。

#### A2 — `color-contrast`（serious），light only
- **位置**：`.model-selector__status-text`（「已连接」徽标文字，`ModelSelector.vue`）。
- **现象**：Light 模式下 `--success` 文字落在 `color-mix(success 14%, …)` 浅底芯片上，实测对比度 **4.42:1**（< AA 4.5）。Dark 模式实测 7.51:1 通过。
- **建议**：Light 模式将徽标文字色压暗（如 `color-mix(in oklch, var(--success), black 18%)`）或加深芯片底色。

#### A3 — 图标 aria-hidden 回归（项目自有门槛，非 axe violation）
- **现象**：`iconHiddenCount = 6/10`——10 个 SVG 中仅 6 个带 `aria-hidden="true"`，**4 个缺失**。这破坏了上一轮 P6「全图标 aria-hidden」的不变量（`icon_a11y_maintained = false`）。
- **具体未隐藏的 SVG**（均位于带 aria-label 的按钮内，故 axe 未报 violation，仅项目门槛失败）：
  - 顶栏 ⌘K 按钮内图标 `.netops-header__cmdk-icon`（按钮 aria-label「打开命令面板」）。
  - BottomTabBar 三个 tab 图标 `.bottom-tab-bar__icon`（终端 / AI 助手 / 设置）。
- **严重度：次要**（按钮本身有可访问名，不构成功能性障碍，但违反项目既定标准）。
- **建议**：给上述装饰性 SVG 补 `aria-hidden="true"`（H4 MainLayout header cmdk 图标 + H7 BottomTabBar tab 图标）。

### 手动对比度核对（canvas 像素栅格化计算，含半透明合成）

**Dark 模式**（阈值 AA 4.5:1 正文 / 3:1 大字与 UI）：

| 配对 | 比值 | 结论 |
|------|------|------|
| foreground / bg | 17.30 | ✅ |
| muted-foreground / bg | 7.19 | ✅ |
| primary(琥珀) / bg | 11.68 | ✅ |
| primary-foreground / primary（按钮白底字）| 11.33 | ✅ |
| success / bg（success 作文字）| 8.90 | ✅ |
| success / 徽标芯片（已连接）| 7.51 | ✅ |
| warning / bg | 10.82 | ✅ |
| **warning-foreground / warning（终端取消按钮）** | **10.31** | ✅ 见下 |
| **success-foreground / success** | **2.25** | ⚠ 失败，但**无任何消费者**，见下 |
| destructive / bg | 5.77 | ✅ |

**控制器预警的 `.dark` 未重定义 `--warning-foreground` / `--success-foreground` 核对结论：**
- `.dark` 块确实未重定义这两个 foreground token（`tokens.css:148–213`），它们继承 `:root` 的 light 值（warning-fg = `oklch(0.15…)` 近黑、success-fg = `oklch(0.99…)` 近白）。**确认属实。**
- **但实际影响基本为 0**：
  - `--warning-foreground` 全仓**唯一消费者**是 `TerminalConnectionForm.vue:158-159` 的 `.terminal-config-button--cancel`（连接中取消按钮）：Dark 下是「近黑字 + 亮琥珀底」= 暗字配亮底，对比度 **10.31:1，远超 AA**。不是问题。
  - `--success-foreground` 全仓**零消费者**（grep 确认无任何组件用作 success 填充上的文字）。其 2.25:1 是**休眠/潜在 bug**，当前界面不可见、无障碍工具也扫不到。
- **建议（防御性，非阻塞）**：仍建议在 `.dark` 补 `--warning-foreground` / `--success-foreground` 两行（与 light 一致或按 dark 反相），消除未来若新增「success/warning 实心填充 + 前景文字」组件时的隐患。

**Light 模式**（真正的边界对比度都集中在这里，与控制器预期相反）：

| 配对 | 比值 | 结论 |
|------|------|------|
| foreground / bg | 15.43 | ✅ |
| primary(暗琥珀) / bg | 5.51 | ✅ |
| primary-foreground / primary（按钮）| 6.02 | ✅ |
| success / bg | 5.01 | ✅ |
| success-foreground / success | 5.46 | ✅（light 有正确值）|
| **warning / bg** | **4.25** | ⚠ 略低于 4.5（正文）|
| warning / card | 4.59 | ✅（刚过）|
| **warning-foreground / warning（终端取消按钮）** | **4.12** | ⚠ 低于 4.5 |
| **success / 徽标芯片（已连接）** | **4.42** | ⚠ = axe A2，略低于 4.5 |
| destructive / bg | 5.41 | ✅ |

- Light 模式 amber/green-on-paper 有三处 4.1–4.5 的**轻微 AA 不达标**（warning 作文字、终端取消按钮文字、已连接徽标）。均属次要，建议在 light 下把 `--warning` / `--success` 用作小字时压暗一档。

---

## 四、移动端（375 / 768）

### 375×812 —— ✅ 通过（布局优秀）
- 顶栏**正确隐藏** 副标题 + divider + clock（≤640px），仅留 NETOPS logo / 服务器状态 / ⌘K / 主题切换（`mobile-375-light.png`）。
- 单面板 + BottomTabBar（终端 / AI 助手 / 设置）三 tab 切换正常，active tab 琥珀 + 顶 1px 琥珀线。
- AI tab：`[ AI ]` 空状态 + 4 张全宽预设卡，无溢出（`mobile-375-light.png`）。
- 终端 tab：连接表单 2 列响应式网格，无溢出，琥珀「连接」按钮（`mobile-375-terminal.png`）。
- 设置 tab：深色模式/命令面板/重连后端三行 + 桌面端快捷键提示（`mobile-375-settings.png`）。
- 设置抽屉可用。气泡/卡片无溢出。

### 768×1024 —— ⚠ 次要密度问题
- 768 > 640，顶栏恢复完整（含 clock，正确）。
- 768 进入**双面板桌面模式**，两侧偏窄：见上 V1（AI header「联网搜索」竖排折行、模型名截断）、V2（AI pane / card 右缘超出 3–6px 被裁剪）。
- **无文档级横向滚动条**（实测 scrollWidth = clientWidth = 769）。
- 截图：`mobile-768.png`。

---

## 五、reduced-motion

> 受限说明：chrome-devtools MCP 的 `emulate` 不暴露 `prefers-reduced-motion` 媒体模拟（且会话中 `emulate`/`press_key` 间歇被平台分类器拦截）。故以**权威静态核验**替代单点目测——结论更强（全局 `*` 覆盖 + 逐组件块双保险）。

- **全局兜底**（`base.css:42-50`，位于 `@layer base`）：`@media (prefers-reduced-motion: reduce)` 对 `*, *::before, *::after` 强制 `animation-duration: 0.001ms !important; animation-iteration-count: 1 !important; transition-duration: 0.001ms !important`。**这一条即可中和全站所有动画**（scanline / amber-pulse / digit-flicker / beam / dot pulse / cursor blink）。
- **逐组件加强块**（共 11 处）：
  - `NetworkTopologyBackground.vue:90` scanline → `animation:none; opacity:0`
  - `ScanlineSweep.vue:85` beam → `animation:none`
  - `ServerStatusIndicator.vue:51` dot → `animation:none`
  - `TerminalOutput.vue:63` cursor → `animation:none`
  - `TerminalStatusBar.vue:72` dot → `animation:none !important`
  - 另有 ChatInput / ChatMessages / ConfirmDialog / EmptyState / ScrollToBottomButton / ThinkingBlock 的过渡禁用块。
- **结论**：✅ prefers-reduced-motion 正确且全面处理；scanline / pulse / digit-flicker 在 reduce 下全停。

---

## 六、结论

**HUD 改造可以「按 H 阶段提交」，但有一个代码层硬阻塞必须先修。**

### 必须先修（阻塞提交/构建）
- **B1（阻塞）**：`MessageBubble.vue:19` 的 TS2379 typecheck 错误 → 导致 `vue-tsc` 与 `vite build` 全部失败、dist 不产出。修复（`?? false` 一行）后 build 才能通过。该问题归属 H5，提交 H5 前必须修。

### 建议随阶段修复（不阻塞，但 axe 标红 / 破坏既有标准）
- **A1（critical，建议修）**：`DragHandle.vue` 拖拽分割条缺 `aria-label` → axe button-name critical。归属 H4。
- **A3（次要）**：4 个装饰 SVG（⌘K 图标 + 3 个 BottomTabBar tab 图标）缺 `aria-hidden="true"`，破坏 P6「全图标 aria-hidden」不变量。归属 H4/H7。
- **A2 / Light 对比度（次要）**：Light 模式 `--success`/`--warning` 作小字的三处 4.1–4.5 轻微 AA 不达标（含「已连接」徽标）。归属 H8 收尾。

### 可选防御性
- `.dark` 补 `--warning-foreground` / `--success-foreground`（当前一个对比度 OK、一个无消费者，仅为未来防隐患）。归属 H1/H8。

### 视觉细节（次要，可后续打磨）
- 768 断点双面板密度（V1/V2）。

**一句话**：双模式 HUD 视觉与运动/降级层面完成度很高、无阻塞级视觉问题；唯一阻塞是 1 个 typecheck 错误（连带 build 失败），修掉后即可按 H 阶段分批提交，其余为次要 a11y/对比度打磨项。
