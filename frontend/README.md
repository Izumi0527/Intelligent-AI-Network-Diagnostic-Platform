# AI智能网络故障分析平台 - 前端

基于 **Vue 3.5 + TypeScript 5.8 + Vite 6 + Tailwind v4** 的网络故障分析平台前端。
提供差异化的"工程师终端审美"与"AI 对话 conversational 审美"双区域体验。

> 完整的项目背景、API 契约、启停脚本细节见仓库根 [README.md](../README.md)。
> 本文只聚焦前端层面的目录、组件、状态、构建与开发约定。

## 项目结构

```
frontend/
├── public/                          # 静态资源
├── src/
│   ├── assets/
│   │   ├── main.css                 # 入口（≤ 20 行），仅 @import 子模块
│   │   └── styles/                  # P1 拆分的样式子模块
│   │       ├── tokens.css           # OKLCH 色 / 间距 / 动效 / 字体 / Z 轴 token
│   │       ├── base.css             # reset / focus-visible / reduced-motion
│   │       ├── surfaces.css         # glass-effect / shadow-glow / btn-glow
│   │       ├── terminal.css         # 终端命名空间样式
│   │       └── ai.css               # AI 对话命名空间样式
│   ├── components/
│   │   ├── ai-assistant/
│   │   │   ├── AIAssistant.vue      # 壳（~115 行），仅装配
│   │   │   └── components/          # 5 个子组件
│   │   │       ├── ChatHeader.vue
│   │   │       ├── ChatInput.vue
│   │   │       ├── ChatMessages.vue
│   │   │       ├── ModelSelector.vue
│   │   │       └── StreamToggle.vue
│   │   ├── terminal/
│   │   │   ├── NetworkTerminal.vue  # 壳（~35 行），仅装配
│   │   │   ├── components/          # 4 个子组件
│   │   │   │   ├── TerminalConnectionForm.vue
│   │   │   │   ├── TerminalOutput.vue
│   │   │   │   ├── TerminalCommandInput.vue
│   │   │   │   └── TerminalStatusBar.vue
│   │   │   └── composables/         # 2 个本地 composable
│   │   │       ├── useTerminalLineStyle.ts
│   │   │       └── useCommandHistory.ts
│   │   ├── common/
│   │   │   ├── ServerStatusIndicator.vue
│   │   │   └── icons/               # SunIcon / MoonIcon / Send / Clear / Connect / Disconnect
│   │   └── ui/
│   │       ├── CardSpotlight.vue
│   │       ├── FloatingParticlesBackground.vue
│   │       └── ShimmerButton.vue
│   ├── composables/                 # 跨组件的全局 composable
│   │   ├── useAiKeyboard.ts         # Ctrl/Cmd+K 清空对话
│   │   ├── useAutoResizeTextarea.ts
│   │   └── useChatScroll.ts
│   ├── layouts/MainLayout.vue
│   ├── stores/
│   │   ├── app.ts                   # 应用级状态（主题 / 后端健康）
│   │   ├── terminal.ts              # 终端会话
│   │   └── ai-assistant/            # AI 助手 store 模块（拆分目录）
│   ├── types/
│   │   ├── index.ts
│   │   └── chat.ts                  # ChatMessage / ChatSettings 等单一类型源头
│   ├── utils/
│   │   ├── aiService.ts
│   │   ├── terminalService.ts
│   │   ├── localStorageUtils.ts
│   │   ├── helpers.ts
│   │   └── logger.ts                # 分级日志器（debug/info/warn/error + traceId）
│   ├── App.vue
│   └── main.ts                      # 只 import './assets/main.css'
├── .env.example                     # 环境变量样例
├── eslint.config.js                 # ESLint 9 flat config
├── postcss.config.js                # 仅 @tailwindcss/postcss
├── package.json
├── tsconfig.json
└── vite.config.ts                   # alias / proxy / build manualChunks + sourcemap
```

## 启动（推荐走根目录脚本）

```powershell
# Windows
..\scripts\dev.ps1           # 后端 + 前端联动启动
..\scripts\build.ps1         # 生产构建 + dist 体积统计
..\scripts\lint.ps1          # typecheck + lint
..\scripts\lint.ps1 -Fix     # typecheck + lint --fix
```

```bash
# macOS / Linux / Git Bash
../scripts/dev.sh
../scripts/build.sh
../scripts/lint.sh
../scripts/lint.sh --fix
```

底层 `npm run dev / build / typecheck / lint / lint:fix` 仍可用，但日常请走 `scripts/`
统一入口，方便对齐全局规则 Layer 4.1。

## 状态管理

使用 Pinia 拆分：
- `stores/app.ts` — 应用全局状态（主题切换、后端健康）
- `stores/terminal.ts` — 终端会话状态
- `stores/ai-assistant/` — AI 助手 store 模块（拆分为 actions / getters / types 等子文件）

类型源头统一在 `src/types/chat.ts`，跨组件共享的 `ChatMessage` / `ChatSettings` 等不允许在
组件内重复定义。

## 环境变量

复制 `.env.example` 为 `.env.local`（被 `.gitignore` 排除），按需填值。当前代码仅消费：

- `VITE_INTERNAL_API_TOKEN`（必填）— 与后端 `INTERNAL_API_TOKEN` 一致，前端通过
  `X-Internal-Api-Token` 自证身份。消费点：`src/utils/terminalService.ts` /
  `src/utils/aiService.ts`。

`.env.example` 还以注释占位列出了 `VITE_API_BASE_URL` / `VITE_DEFAULT_THEME` /
`VITE_DEFAULT_AI_MODEL`，作为未来扩展约定示例 —— 添加任何 `VITE_*` 时必须在 `src/`
内有真实消费点，避免幽灵配置。

## 技术栈

- **框架**：Vue 3.5 + TypeScript 5.8（strict）
- **构建**：Vite 6（manualChunks: vue / markdown / vendor）+ esbuild + sourcemap
- **状态**：Pinia 2.3
- **样式**：Tailwind CSS v4 + `@tailwindcss/postcss`（v4 内置 autoprefixer，不再单独依赖）
- **Markdown 安全**：marked + DOMPurify（在 `ChatMessages.vue` 内净化）
- **HTTP**：axios
- **工具集**：@vueuse/core（含 useIntervalFn 等）、clsx + tailwind-merge
- **代码规范**：ESLint 9 flat config + vue-tsc 2

## 开发约定

- 任何超过 ~150 行的组件视为拆分候选；超过 300 行必须拆
- 不引入 CommonJS、不引入 i18n / vue-router / shadcn-vue（plan 已明确不在范围）
- AI 助手对话区使用 `text-foreground/80` / `text-muted-foreground` 等 token 化语义类，
  禁止 `text-gray-*` 等 light-only 硬编码
- 微交互过渡使用 `transition-[<具体属性>] duration-[var(--dur-base|slow)]
  ease-[var(--ease-out)]`，禁止 `transition-all`
- 装饰性 SVG 应在父按钮（已有 `aria-label`/`title`）内出现；如须强可达性，给父
  按钮加 `aria-label`，依赖按钮的可达名称承载语义
