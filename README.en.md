# AI-Powered Network Diagnostics Platform

> An AI-assisted troubleshooting workspace for NetOps and security teams: connect to network devices, run commands, analyze logs, and stream model responses from one browser-based console.

**Language / 语言**：[简体中文](./README.md) | English

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Version](https://img.shields.io/badge/version-0.2.1-blue.svg)](#)
[![Vue](https://img.shields.io/badge/Vue-3.5-42b883.svg)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-v4-38bdf8.svg)](https://tailwindcss.com/)

## Overview

This project brings together a **network device terminal**, **AI-assisted diagnostics**, **web search enrichment**, and **multi-provider streaming chat** in a single operational workspace. The AI assistant is primed with a **Senior Network & Security Architect** persona, so responses are framed around topology, protocols, performance, troubleshooting workflow, security exposure, and operational risk.

It is designed for:

- SSH / Telnet access to network devices and command execution;
- troubleshooting switches, routers, firewalls, and adjacent infrastructure;
- AI-assisted analysis of logs, configuration snippets, and incident symptoms;
- NetOps workflows that need both network engineering and security review in the same context.

## UI Preview

### Light Mode

![Light mode](./docs/images/day.png)

### Dark Mode

![Dark mode](./docs/images/dark.png)

## Key Features

- **Network terminal**: SSH / Telnet sessions, command history, output cleanup, and basic paging handling.
- **AI assistant**: OpenAI, Anthropic Claude, and DeepSeek providers behind one SSE streaming interface.
- **Domain persona**: A Senior Network & Security Architect system prompt for network-first diagnostics with security-aware recommendations.
- **Search enrichment**: Optional Brave Search integration with source cards and time-aware context injection.
- **Log analysis**: DeepSeek-powered templates for network error, performance, and security analysis.
- **Industrial HUD UI**: Vue 3 + Tailwind CSS v4 + OKLCH design tokens, with light and dark themes.
- **Security boundaries**: Internal API token, terminal access policy, high-risk command blocking, and log redaction.
- **Cross-platform scripts**: PowerShell and Bash entry points for Windows, Linux, macOS, and Git Bash.

## Technology Stack

| Layer | Stack |
|------|-------|
| Frontend | Vue 3.5, TypeScript 5.8, Pinia, Vite 6, Tailwind CSS v4 |
| Backend | Python 3.9–3.12, FastAPI, Pydantic v2, Uvicorn |
| Network access | Netmiko, Paramiko, telnetlib |
| AI integrations | OpenAI, Anthropic Claude, DeepSeek, Brave Search |
| Quality gates | ESLint, vue-tsc, Ruff, pytest, cross-platform scripts |

## Setup and Run

### 1. Requirements

- Python 3.9–3.12
- Node.js 20+
- uv
- npm
- PowerShell 7+ on Windows, or Bash / Git Bash on Unix-like environments

### 2. Configure environment files

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env.local
```

Configure the required values for your environment:

- `backend/.env`
  - `INTERNAL_API_TOKEN`
  - `DEEPSEEK_API_KEY` / `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`
  - Optional: `BRAVE_SEARCH_ENABLED=true` and `BRAVE_SEARCH_API_KEY`
- `frontend/.env.local`
  - `VITE_INTERNAL_API_TOKEN`, which must match `INTERNAL_API_TOKEN` on the backend

### 3. Start the development environment

Windows PowerShell:

```powershell
.\scripts\dev.ps1
```

Linux / macOS / Git Bash:

```bash
./scripts/dev.sh
```

Default endpoints:

- Frontend: <http://localhost:5180>
- Backend health check: <http://localhost:8000/api/v1/health>
- API docs: <http://localhost:8000/api/v1/docs>

### Common scripts

```powershell
.\scripts\lint.ps1                # Frontend typecheck + ESLint
.\scripts\build.ps1               # Frontend production build
.\scripts\backend-check.ps1       # Backend dependencies, Ruff, pytest, and script contract checks
.\scripts\clean-python-cache.ps1  # Remove Python cache files
.\scripts\prod.ps1                # Production-style preview
```

```bash
./scripts/lint.sh
./scripts/build.sh
./scripts/backend-check.sh
./scripts/clean-python-cache.sh
./scripts/prod.sh
```

- `scripts/p3_axe_audit.py` / `scripts/p6_axe_audit.py`: Playwright + axe accessibility audit scripts.
- Runtime scripts set `PYTHONDONTWRITEBYTECODE=1` to reduce Python bytecode cache noise during development.

> For the full architecture, API map, data flows, environment variables, and maintenance notes, see [`docs/project-architecture-and-system-overview.en.md`](./docs/project-architecture-and-system-overview.en.md).

## Documentation

- [Architecture and system overview](./docs/project-architecture-and-system-overview.en.md)
- [Design plans](./docs/plans/)
- [Discussions and verification notes](./discuss/)

## Star History

If this project is useful to you, a **Star** helps support future maintenance.

[![Star History Chart](https://api.star-history.com/svg?repos=Izumi0527/Intelligent-AI-Network-Diagnostic-Platform&type=Date)](https://star-history.com/#Izumi0527/Intelligent-AI-Network-Diagnostic-Platform&Date)

## Acknowledgements

This project builds on the following open-source ecosystems:

- [Vue](https://vuejs.org/) / [Vite](https://vite.dev/) / [Pinia](https://pinia.vuejs.org/)
- [Tailwind CSS](https://tailwindcss.com/)
- [FastAPI](https://fastapi.tiangolo.com/) / [Pydantic](https://docs.pydantic.dev/) / [uv](https://github.com/astral-sh/uv)
- [Netmiko](https://github.com/ktbyers/netmiko) / [Paramiko](https://www.paramiko.org/)
- OpenAI, Anthropic Claude, DeepSeek, and Brave Search API ecosystems

Thanks to everyone who uses the project, shares feedback, opens issues, or gives it a Star.

## License

This project is released under the [MIT License](./LICENSE).
