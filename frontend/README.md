# AI智能网络故障分析平台 - 前端

本项目是一个基于Vue 3和TypeScript的AI智能网络故障分析平台前端应用。结合现代UI设计和功能性，提供一个用于网络设备连接和AI辅助故障分析的界面。

## 功能特点

- **网络终端**：支持SSH/Telnet连接到网络设备
- **AI助手**：集成Claude 3.7等AI模型，提供智能化故障分析
- **现代UI**：响应式设计，支持明暗主题切换
- **流式响应**：AI回答支持实时流式显示
- **会话管理**：支持保存和清除对话历史
- **状态监控**：实时显示与后端服务器和AI模型的连接状态

## 项目结构

```
frontend/
├── public/              # 静态资源
├── src/                 # 源代码
│   ├── assets/          # 资源文件(CSS, 图片等)
│   ├── components/      # 组件
│   │   ├── ai-assistant/   # AI助手相关组件
│   │   ├── common/         # 通用组件
│   │   └── terminal/       # 终端相关组件
│   ├── layouts/         # 布局组件
│   ├── stores/          # Pinia状态管理
│   ├── App.vue          # 根组件
│   └── main.ts          # 入口文件
├── .gitignore          # Git忽略文件
├── index.html          # HTML模板
├── package.json        # 项目配置
├── tsconfig.json       # TypeScript配置
└── README.md           # 文档
```

## 主要组件

- **AIAssistant.vue**: AI助手界面，提供与AI模型交互的功能
- **NetworkTerminal.vue**: 网络终端界面，提供SSH/Telnet远程连接功能
- **MainLayout.vue**: 主布局组件，管理整体页面结构

## 状态管理

使用Pinia进行状态管理，主要包含以下store:
- **app.ts**: 应用级状态，如主题切换、服务器连接等
- **aiAssistant.ts**: AI助手相关状态
- **terminal.ts**: 终端相关状态

## 启动项目

```bash
# 安装依赖
npm install

# 开发模式启动
npm run dev

# 构建生产版本
npm run build
```

## 依赖项

- Vue 3
- TypeScript
- Vite
- Pinia
- Tailwind CSS

## 技术栈

- **前端框架**：Vue 3 + TypeScript
- **UI组件库**：Inspira UI
- **状态管理**：Pinia
- **样式方案**：TailwindCSS
- **HTTP客户端**：Axios
- **代码规范**：ESLint + Prettier

## 开发环境设置

### 先决条件
- Node.js (v18+)
- npm 或 yarn

### 安装依赖
```bash
npm install
# 或
yarn install
```

### 开发服务器
```bash
npm run dev
# 或
yarn dev
```

### 构建生产版本
```bash
npm run build
# 或
yarn build
```

## 配置

平台支持通过环境变量进行配置：

- `VITE_API_BASE_URL`：后端API基础URL
- `VITE_DEFAULT_THEME`：默认主题（light或dark）
- `VITE_DEFAULT_AI_MODEL`：默认AI模型

## API集成

平台通过后端API与网络设备和AI模型进行通信，主要API端点包括：

- 终端管理：`/api/terminal/*`
- AI助手：`/api/ai/*`
- 系统状态：`/api/status`

## 许可证

[MIT](LICENSE)
