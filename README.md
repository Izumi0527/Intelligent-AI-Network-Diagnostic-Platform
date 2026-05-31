# AI 智能网络故障分析平台

> 面向网络运维与网络安全场景的一体化 AI 故障诊断工作台：连接设备、执行命令、分析日志、流式问答。

**语言 / Language**：简体中文 | [English](./README.en.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Version](https://img.shields.io/badge/version-0.2.1-blue.svg)](#)
[![Vue](https://img.shields.io/badge/Vue-3.5-42b883.svg)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-v4-38bdf8.svg)](https://tailwindcss.com/)

## 项目简介

本项目将 **网络设备终端**、**AI 辅助诊断**、**联网搜索** 与 **多模型流式对话** 集成在同一工作台中。AI 助手默认注入「高级网络安全架构师（Senior Network & Security Architect）」角色，从网络架构、协议、性能、排障与安全风险多个角度辅助分析。

适合用于：

- 网络设备 SSH / Telnet 连接与命令执行；
- 交换机、路由器、防火墙等设备故障排查；
- 网络日志、配置片段和故障现象的 AI 分析；
- 网络与安全双视角的运维辅助。

## 界面预览

### 浅色模式

![浅色模式](./docs/images/day.png)

### 深色模式

![深色模式](./docs/images/dark.png)

## 核心特性

- **网络终端**：SSH / Telnet 会话、命令历史、输出清洗、基础分页处理。
- **AI 助手**：OpenAI / Anthropic Claude / DeepSeek 多模型接入，统一 SSE 流式响应。
- **专业 Persona**：网络与安全并重的高级网络安全架构师角色提示词。
- **联网搜索增强**：可选 Brave Search，支持来源卡片和时间锚点。
- **日志分析**：DeepSeek 网络日志错误 / 性能 / 安全分析模板。
- **工业 HUD UI**：Vue 3 + Tailwind CSS v4 + OKLCH token，支持浅色 / 深色主题。
- **安全边界**：内部 API Token、终端连接策略、高风险命令拦截、日志脱敏。
- **跨平台脚本**：Windows PowerShell 与 Linux / macOS / Git Bash 双入口。

## 技术栈速览

| 层 | 技术 |
|----|------|
| 前端 | Vue 3.5、TypeScript 5.8、Pinia、Vite 6、Tailwind CSS v4 |
| 后端 | Python 3.9–3.12、FastAPI、Pydantic v2、Uvicorn |
| 网络连接 | Netmiko、Paramiko、telnetlib |
| AI 接入 | OpenAI、Anthropic Claude、DeepSeek、Brave Search |
| 质量保障 | ESLint、vue-tsc、Ruff、pytest、跨平台 scripts |

## 安装与启动

### 1. 环境要求

- Python 3.9–3.12
- Node.js 20+
- uv
- npm
- PowerShell 7+（Windows 推荐）或 Bash / Git Bash

### 2. 配置环境变量

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env.local
```

至少需要按实际情况配置：

- `backend/.env`
  - `INTERNAL_API_TOKEN`
  - `DEEPSEEK_API_KEY` / `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`
  - 可选：`BRAVE_SEARCH_ENABLED=true` 与 `BRAVE_SEARCH_API_KEY`
- `frontend/.env.local`
  - `VITE_INTERNAL_API_TOKEN`：需与后端 `INTERNAL_API_TOKEN` 一致

### 3. 启动项目

Windows PowerShell：

```powershell
.\scripts\dev.ps1
```

Linux / macOS / Git Bash：

```bash
./scripts/dev.sh
```

默认访问：

- 前端：<http://localhost:5180>
- 后端健康检查：<http://localhost:8000/api/v1/health>
- API 文档：<http://localhost:8000/api/v1/docs>

### 常用脚本

```powershell
.\scripts\lint.ps1                # 前端 typecheck + ESLint
.\scripts\build.ps1               # 前端生产构建
.\scripts\backend-check.ps1       # 后端依赖、ruff、pytest、脚本契约
.\scripts\clean-python-cache.ps1  # 清理 Python 缓存
.\scripts\prod.ps1                # 生产预览
```

```bash
./scripts/lint.sh
./scripts/build.sh
./scripts/backend-check.sh
./scripts/clean-python-cache.sh
./scripts/prod.sh
```

- `scripts/p3_axe_audit.py` / `scripts/p6_axe_audit.py`：Playwright + axe 可访问性验证脚本。
- 启动脚本会设置 `PYTHONDONTWRITEBYTECODE=1`，减少运行时 Python 字节码缓存污染。

> 更完整的架构、API、数据流、环境变量和维护说明见：[`docs/project-architecture-and-system-overview.md`](./docs/project-architecture-and-system-overview.md)。

## 项目文档

- [架构与系统信息总览](./docs/project-architecture-and-system-overview.md)
- [设计计划目录](./docs/plans/)
- [讨论与验证记录目录](./discuss/)

## Star 趋势

如果这个项目对你有帮助，欢迎点一个 **Star** 支持后续维护。

[![Star History Chart](https://api.star-history.com/svg?repos=Izumi0527/Intelligent-AI-Network-Diagnostic-Platform&type=Date)](https://star-history.com/#Izumi0527/Intelligent-AI-Network-Diagnostic-Platform&Date)

## 致谢

感谢以下开源项目与生态对本项目的支持：

- [Vue](https://vuejs.org/) / [Vite](https://vite.dev/) / [Pinia](https://pinia.vuejs.org/)
- [Tailwind CSS](https://tailwindcss.com/)
- [FastAPI](https://fastapi.tiangolo.com/) / [Pydantic](https://docs.pydantic.dev/) / [uv](https://github.com/astral-sh/uv)
- [Netmiko](https://github.com/ktbyers/netmiko) / [Paramiko](https://www.paramiko.org/)
- OpenAI、Anthropic Claude、DeepSeek 与 Brave Search 相关 API 生态

也感谢每一位使用、反馈、提交 issue 或给予 Star 的朋友。

## 许可证

本项目基于 [MIT License](./LICENSE) 开源。
