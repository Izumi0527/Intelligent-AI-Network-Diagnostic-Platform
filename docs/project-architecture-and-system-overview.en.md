# AI-Powered Network Diagnostics Platform — Architecture and System Overview

> Updated: 2026-05-31
> Current version: 0.2.1
> Scope: the current repository code, configuration, scripts, and tests. This document describes the system architecture; it does not replace the quick-start flow in the root [`README.en.md`](../README.en.md).

[Chinese version](./project-architecture-and-system-overview.md)

## 1. Product Positioning

This project is a decoupled frontend/backend platform for AI-assisted network troubleshooting. It targets NetOps, network incident diagnostics, and security operations workflows by combining a network device terminal, AI analysis, web search enrichment, and multi-provider streaming chat in one browser-based workspace.

Core objectives:

- let users connect to SSH / Telnet network devices from the browser;
- run troubleshooting commands and inspect terminal output in the same UI;
- send logs, configuration snippets, or incident symptoms to an AI assistant for analysis;
- use a **Senior Network & Security Architect** persona so answers cover network design, protocols, performance, troubleshooting steps, security risk, and operational constraints.

Current capabilities:

- SSH / Telnet terminal sessions;
- a general-purpose `NetworkService` path backed by Netmiko;
- SSE-based AI streaming chat;
- OpenAI / Anthropic Claude / DeepSeek provider integrations;
- Brave Search enrichment for web-backed context;
- a DeepSeek-powered network log analyzer;
- an Industrial HUD frontend with light and dark themes;
- backend internal authentication, terminal access policy, and log/error redaction;
- cross-platform scripts for development, production preview, build, lint, and backend quality gates.

## 2. High-Level Architecture

```text
Browser
  |
  | Vue 3 + Pinia + TypeScript
  | fetch / axios requests to /api/*
  v
Vite development server
  |
  | proxy: /api -> http://localhost:8000/api/v1
  v
FastAPI backend
  |
  |-- API routing layer
  |     |-- /ai
  |     |-- /terminal
  |     |-- /network
  |     `-- /health
  |
  |-- AIApplicationService
  |     |-- injects Brave Search context
  |     |-- injects the Senior Network & Security Architect persona
  |     `-- AIServiceManager
  |           |-- OpenAIProvider
  |           |-- ClaudeProvider
  |           `-- DeepseekProvider
  |
  |-- DeepSeek network log analyzer
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

During development, the browser always calls `/api`; Vite rewrites those requests to backend paths under `/api/v1`. Production deployments must provide an equivalent gateway or reverse-proxy rule, or the frontend base URL and backend API prefix must be changed together.

## 3. Technology Stack

### 3.1 Frontend

- Vue 3.5
- TypeScript 5.8 in strict mode
- Pinia 2.3
- Vite 6
- Tailwind CSS v4 + `@tailwindcss/postcss`
- marked + DOMPurify
- Axios for regular HTTP requests
- fetch + `ReadableStream` for AI SSE streaming
- ESLint 9 flat config
- vue-tsc

### 3.2 Backend

- Python `>=3.9,<3.13`
- FastAPI 0.115
- Uvicorn 0.34
- Pydantic 2.11 + pydantic-settings 2.9
- Netmiko 4.5
- Paramiko 3.5
- telnetlib, with Python version compatibility to monitor over time
- aiohttp / httpx / requests
- python-jose / passlib / bcrypt
- pytest / pytest-asyncio / pytest-cov
- Ruff / Black / MyPy
- uv

## 4. Top-Level Directory Responsibilities

```text
Project3/
  backend/        FastAPI backend, AI providers, network access, configuration, runtime entrypoint
  frontend/       Vue frontend app, components, stores, types, and API clients
  docs/           Long-lived documentation, screenshots, and implementation plans
  discuss/        Discussions, verification reports, and temporary drafts
  scripts/        Cross-platform run, build, lint, test, and maintenance scripts
  tests/          Root-level test suite
  logs/           Runtime logs, excluded from version control by .gitignore
```

Documentation ownership:

- root `README.md`: Chinese project entry point, quick start, key capabilities, and API summary;
- root `README.en.md`: English project entry point and quick start;
- `docs/project-architecture-and-system-overview.md`: Chinese architecture, module boundaries, data flows, and risk notes;
- `docs/project-architecture-and-system-overview.en.md`: English architecture, module boundaries, data flows, and risk notes;
- `docs/plans/`: design plans and implementation records;
- `discuss/`: temporary discussions and verification reports.

Frontend-facing documentation is intentionally centralized in the root README files and this architecture document pair to avoid duplicated entry points drifting out of sync.

## 5. Backend Architecture

### 5.1 Startup Flow

Entrypoint: `backend/run.py`

Main sequence:

1. resolve the backend directory;
2. load `backend/.env`;
3. import `settings`;
4. initialize logging;
5. parse `--host`, `--port`, and `--reload`;
6. start `app.main:app` with Uvicorn.

Normal project startup should go through root-level wrapper scripts instead of calling low-level commands directly:

- `scripts/dev.ps1` / `scripts/dev.sh`
- `scripts/prod.ps1` / `scripts/prod.sh`

The development scripts start the backend first, wait for `/api/v1/health` to pass, and then start the frontend.

### 5.2 FastAPI Application Entrypoint

Entrypoint: `backend/app/main.py`

Responsibilities:

- create the FastAPI application;
- configure documentation routes;
- configure CORS;
- register request logging middleware;
- mount routes under `/api/v1`;
- register startup and shutdown lifecycle hooks;
- create the idle terminal-session cleanup task.

### 5.3 Configuration System

Configuration class: `backend/app/config/settings.py`

Configuration sources:

- environment variables;
- `backend/.env`;
- `backend/.env.example`.

Main configuration groups:

- base runtime: `APP_ENV`, `DEBUG`, `API_PREFIX`, `API_V1_STR`, `HOST`, `PORT`;
- security: `SECRET_KEY`, `API_AUTH_ENABLED`, `INTERNAL_API_TOKEN`, JWT settings;
- AI: `AI_ENABLED`, OpenAI / Anthropic / DeepSeek API keys, base URLs, and model lists;
- Brave Search: search API key and feature switch;
- terminal policy: allowed hosts, CIDRs, SSH/Telnet ports, command length, and high-risk command regexes;
- logging: `LOG_LEVEL`, log format, and file output.

### 5.4 API Routing

Unified router: `backend/app/api/api_v1/api.py`

Mounted modules:

- `/ai`
- `/terminal`
- `/network`
- `/health`

Main endpoints:

| Module | Endpoints |
|--------|-----------|
| Health | `GET /api/v1/health`, `GET /api/v1/health/ready` |
| AI | `GET /ai/models`, `GET /ai/models/{model_id}/status`, `POST /ai/chat/stream`, `POST /ai/debug/request-format`, `GET /ai/deepseek/status`, `POST /ai/deepseek/analyze-network-log` |
| Terminal | `POST /terminal/connect`, `POST /terminal/cancel-connect`, `POST /terminal/execute`, `POST /terminal/disconnect`, `GET /terminal/sessions`, `GET /terminal/sessions/{session_id}`, `POST /terminal/cleanup` |
| Network | `POST /network/connect`, `POST /network/command`, `POST /network/disconnect`, `GET /network/connections`, `GET /network/connections/{connection_id}` |

All API routes are served under the `/api/v1` prefix.

## 6. AI Subsystem

### 6.1 AIApplicationService

File: `backend/app/services/ai/application_service.py`

Responsibilities:

- orchestrate AI chat outside the route layer;
- centralize model validation, request logging, SSE encoding, and client-safe error messages;
- call Brave Search when `enable_search=true`;
- inject search results as a system message;
- always inject the **Senior Network & Security Architect** persona;
- call `AIServiceManager.chat_stream()` to receive provider events;
- normalize provider output into SSE events: `search_results`, `thinking`, `content`, `error`, and `done`.

Message order:

```text
[persona(system), search_context(system)?, ...user/assistant history]
```

The stable role definition is placed before temporary search context so the assistant keeps a consistent operational voice.

### 6.2 Persona Prompts

File: `backend/app/services/ai/prompts.py`

Constants:

- `NETWORK_SECURITY_ARCHITECT_PERSONA`: the main chat-assistant persona;
- `NETWORK_LOG_ANALYST_SYSTEM`: the DeepSeek log analyzer system prompt;
- `_ARCHITECT_IDENTITY`: shared role identity text.

The persona represents a Senior Network & Security Architect: it combines the troubleshooting discipline of an experienced network engineer with the defense-in-depth mindset of a security architect. Network architecture, protocols, incident diagnosis, and performance remain the primary focus; risk analysis and hardening guidance are first-class supporting dimensions.

### 6.3 AIServiceManager and Providers

File: `backend/app/services/ai/manager.py`

Responsibilities:

- initialize providers based on available API keys;
- aggregate available models;
- check model connection status;
- route requests by model ID prefix:
  - `gpt-` -> `OpenAIProvider`;
  - `claude-` -> `ClaudeProvider`;
  - `deepseek-` -> `DeepseekProvider`;
- expose one `chat_stream()` interface.

Provider files:

- `backend/app/services/ai/providers/openai_provider.py`
- `backend/app/services/ai/providers/claude_provider.py`
- `backend/app/services/ai/providers/deepseek_provider.py`

Providers only forward the already-orchestrated `request.messages` to upstream models and translate upstream streaming responses into internal `StreamEvent` objects.

### 6.4 Brave Search Enrichment

The Brave Search client lives in `backend/app/services/search/brave_search.py`.

When `ChatRequest.enable_search=true` and Brave Search is configured:

1. the backend uses the last user message as the query;
2. Brave Search is called;
3. a `SearchSource[]` payload is returned to the frontend;
4. a system block is injected with the real current time, result titles, URLs, and snippets;
5. the frontend receives a `search_results` SSE event and renders source cards.

If search fails or is not configured, the AI chat continues and the backend marks the search state with `search_failed=true`.

### 6.5 DeepSeek Network Log Analyzer

File: `backend/app/services/ai/deepseek/analyzer.py`

Supported analysis modes:

- `error_analysis`
- `performance_analysis`
- `security_analysis`
- automatic log-type classification;
- extraction of IP addresses, timestamps, error codes, interfaces, protocols, and related patterns;
- both non-streaming and streaming log analysis use `NETWORK_LOG_ANALYST_SYSTEM`.

## 7. Frontend Architecture

### 7.1 Startup Flow

Entrypoints:

- `frontend/src/main.ts`
- `frontend/src/App.vue`
- `frontend/src/layouts/MainLayout.vue`

Startup sequence:

1. create the Vue application;
2. register Pinia;
3. load `main.css`;
4. render `MainLayout`;
5. load the terminal panel and AI assistant panel.

Default development server: `http://localhost:5180`.

### 7.2 Layout and Theme

Main layout: `frontend/src/layouts/MainLayout.vue`

Layout regions:

- top bar: NETOPS brand, subtitle, clock, backend status, command palette, and theme toggle;
- left panel: network terminal;
- right panel: AI assistant;
- responsive behavior: two-column desktop layout, with tab/collapsed behavior on mobile.

Theme state: `frontend/src/stores/app.ts`

- light mode is the default;
- user selection is persisted to `localStorage.theme`;
- dark mode is activated with `document.documentElement.classList.add('dark')`.

### 7.3 State Management

Pinia stores:

- `stores/app.ts`: backend connectivity and theme state;
- `stores/terminal.ts`: terminal connection, sessions, commands, output, and history;
- `stores/ai-assistant/`: AI assistant state, models, streaming responses, search toggle, messages, and errors.

The AI assistant selects `deepseek-v4-flash` by default.

### 7.4 API Clients

AI client: `frontend/src/utils/aiService.ts`

- Axios handles model list and status checks;
- fetch handles true streaming via `POST /api/ai/chat/stream`;
- an SSE state machine parses `event:` and `data:` lines;
- backend events are normalized into frontend JSON-line events: `thinking`, `content`, `error`, and `search_results`.

Terminal client: `frontend/src/utils/terminalService.ts`

- uses Axios;
- connects, executes commands, disconnects, and queries sessions;
- uses longer connection timeouts to account for slow first-time network device logins.

### 7.5 Component Structure

Primary components:

- `components/terminal/NetworkTerminal.vue`: terminal shell component;
- `components/terminal/components/*`: connection form, terminal output, command input, and status bar;
- `components/ai-assistant/AIAssistant.vue`: AI assistant shell component;
- `components/ai-assistant/components/*`: header, message list, input box, model selector, search/streaming controls, and related UI;
- `components/common/ServerStatusIndicator.vue`: backend status indicator;
- `components/ui/*`: HUD and visual enhancement components.

## 8. Network Device Connectivity

The backend has two separate network-device interaction paths.

### 8.1 Terminal Path

This path powers the interactive terminal experience in the frontend.

```text
Frontend Terminal UI
  -> terminalService
  -> /api/v1/terminal/*
  -> TerminalService
  -> TerminalManager
  -> SSHManager / TelnetManager
  -> network device
```

Characteristics:

- persistent sessions;
- command history;
- output cleanup;
- session timeout and idle cleanup;
- optimized for the user-facing terminal workflow in the page.

### 8.2 Network Path

This path provides a general connection and command-execution API.

```text
External/internal caller /api/v1/network/*
  -> NetworkService
  -> Netmiko ConnectHandler
  -> network device
```

Characteristics:

- backed by Netmiko;
- maintains a connection dictionary;
- wraps blocking connection and command execution with `asyncio.to_thread()`;
- better suited for structured API calls.

These two paths use different connection IDs, state models, and underlying libraries. Their IDs and session state must not be mixed.

## 9. Data Models

### 9.1 AI Models

File: `backend/app/models/ai.py`

Core models:

- `AIModel`
- `Message`
- `ChatRequest`
- `SearchSource`
- `ModelsResponse`
- `ModelConnectionStatus`
- `StreamEvent`

Important `ChatRequest` fields:

- `model`
- `messages`
- `max_tokens`
- `temperature`
- `top_p`
- `stream`
- `enable_search`

Constraints:

- maximum 8000 characters per message;
- maximum 32000 characters across all messages;
- maximum 50 messages;
- maximum `max_tokens` value: 8192.

### 9.2 Terminal / Network Models

- `backend/app/models/terminal.py`: terminal credentials, command requests, responses, and session metadata;
- `backend/app/models/network.py`: connection requests, connection responses, command requests, connection lists, and related payloads.

## 10. Logging and Security

### 10.1 Logging

Utility: `backend/app/utils/logger.py`

Capabilities:

- console logs;
- file logs;
- access logs;
- error logs;
- automatic log-directory creation;
- sensitive-field redaction;
- client-safe error messages.

Log output directory: `logs/`. It is excluded from version control through `.gitignore`.

### 10.2 Security Boundaries

Security-related modules:

- `backend/app/utils/security.py`
- `backend/app/utils/terminal_policy.py`
- `backend/app/services/ai/base.py`
- `backend/app/core/rate_limit.py`

Main mechanisms:

- internal API token;
- JWT utilities;
- terminal target host / CIDR / port restrictions;
- command length limits;
- high-risk command regex blocking;
- upstream AI error redaction;
- log redaction;
- device passwords are not hard-coded or committed to the repository.

Note: in-process wrapping of device passwords mainly reduces accidental plaintext exposure. It should not be treated as strong encryption or as a replacement for a secret manager.

## 11. Setup, Runtime, and Scripts

This project expects Run / Debug / Test / Build workflows to go through root-level `scripts/` wrappers. This prevents behavior drift caused by calling low-level `npm`, `uv`, `python`, or similar commands differently across environments.

### 11.1 Requirements

- Python 3.9–3.12;
- Node.js 20+;
- uv;
- npm;
- Windows PowerShell 7+ on Windows, or Bash / Git Bash.

### 11.2 Environment Variables

Backend:

```powershell
Copy-Item backend/.env.example backend/.env
```

Frontend:

```powershell
Copy-Item frontend/.env.example frontend/.env.local
```

Common backend settings:

| Variable | Description |
|----------|-------------|
| `INTERNAL_API_TOKEN` | Bearer token for internal APIs; frontend `VITE_INTERNAL_API_TOKEN` must match it |
| `API_AUTH_ENABLED` | Enables internal API authentication; should be enabled in production |
| `DEEPSEEK_API_KEY` / `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | Configure the providers you want to enable |
| `BRAVE_SEARCH_ENABLED` / `BRAVE_SEARCH_API_KEY` | Brave Search web-enrichment switch and key |
| `TERMINAL_ALLOWED_HOSTS` / `TERMINAL_ALLOWED_CIDRS` | Restrict which network devices may be reached |
| `TERMINAL_ALLOWED_SSH_PORTS` / `TERMINAL_ALLOWED_TELNET_PORTS` | Restrict SSH / Telnet ports |
| `TERMINAL_COMMAND_MAX_LENGTH` | Maximum terminal command length |
| `TERMINAL_BLOCKED_COMMAND_PATTERNS` | Regex patterns for high-risk command blocking |
| `LOG_LEVEL` | Logging level |

Frontend settings currently consumed by the app:

| Variable | Description |
|----------|-------------|
| `VITE_INTERNAL_API_TOKEN` | Internal API access token; must match backend `INTERNAL_API_TOKEN` |

### 11.3 Runtime Scripts

Script directory: `scripts/`

| Script | Purpose |
|--------|---------|
| `dev.ps1` / `dev.sh` | Development mode: backend hot reload + frontend Vite |
| `prod.ps1` / `prod.sh` | Production-style preview: backend production mode + frontend preview |
| `build.ps1` / `build.sh` | Frontend production build and dist statistics |
| `lint.ps1` / `lint.sh` | Frontend vue-tsc + ESLint |
| `backend-check.ps1` / `backend-check.sh` | Backend dependencies, Ruff, pytest, and script contract gates |
| `clean-python-cache.ps1` / `clean-python-cache.sh` | Remove Python cache files |
| `p3_axe_audit.py` / `p6_axe_audit.py` | Playwright + axe verification scripts |

Windows PowerShell:

```powershell
.\scripts\dev.ps1
.\scripts\dev.ps1 -BackendPort 8080 -FrontendPort 5181
.\scripts\prod.ps1
.\scripts\build.ps1
.\scripts\lint.ps1
.\scripts\backend-check.ps1
```

Linux / macOS / Git Bash:

```bash
./scripts/dev.sh
./scripts/prod.sh
./scripts/build.sh
./scripts/lint.sh
./scripts/backend-check.sh
```

Shared script behavior:

- validate the project layout;
- check that `backend/.env` exists;
- check required commands: `uv` and `npm`; shell scripts also check `curl`;
- create the log directory automatically;
- start the backend first and start the frontend after the health check passes;
- set `PYTHONDONTWRITEBYTECODE=1` to reduce runtime cache noise.

### 11.4 Access URLs

Default ports:

- frontend: `http://localhost:5180`;
- backend health check: `http://localhost:8000/api/v1/health`;
- backend readiness check: `http://localhost:8000/api/v1/health/ready`;
- API docs: `http://localhost:8000/api/v1/docs`.

In development mode, the browser calls `/api/*`; Vite proxies those requests to backend `/api/v1/*`.

### 11.5 Logs and Cache Files

- Runtime logs are written to `logs/`, which is excluded by `.gitignore`;
- `backend/.env`, `frontend/.env.local`, `.venv`, and `node_modules` are not version-controlled;
- startup scripts set `PYTHONDONTWRITEBYTECODE=1`;
- Python cache files can be removed with `clean-python-cache.ps1` / `clean-python-cache.sh`.

## 12. Testing and Quality Gates

Root test suite: `tests/`

Current test coverage themes:

- AI SSE contract and error redaction;
- AI persona and Brave Search injection order;
- Brave Search client behavior;
- Pydantic v2 models;
- backend package metadata and runtime dependencies;
- startup script contracts;
- Python bytecode cache policy;
- terminal connection policy and Telnet login policy;
- health readiness;
- request ID tracing;
- logger behavior;
- architecture boundaries.

Main verification entry points:

```powershell
.\scripts\lint.ps1
.\scripts\build.ps1
.\scripts\backend-check.ps1
```

## 13. Core Data Flows

### 13.1 AI Streaming Chat

```text
User input
  -> ai-assistant store
  -> aiService.sendMessageStream()
  -> fetch('/api/ai/chat/stream')
  -> Vite proxy to /api/v1/ai/chat/stream
  -> AIApplicationService.chat_stream()
  -> Brave Search? + persona injection
  -> AIServiceManager.chat_stream()
  -> Provider calls upstream model
  -> backend SSE event
  -> frontend SSE state-machine parser
  -> ChatMessages renders thinking/content/search sources
```

### 13.2 Search Enrichment

```text
enable_search=true
  -> take the last user message
  -> BraveSearchClient.search(query)
  -> format search system block with the real current time
  -> insert search context into request.messages
  -> frontend receives search_results event first
  -> AI response can cite sources at the end
```

### 13.3 Terminal Connection

```text
User enters SSH/Telnet details
  -> terminalStore.connectToDevice()
  -> terminalService.connect()
  -> POST /api/terminal/connect
  -> TerminalService.connect()
  -> TerminalManager.connect()
  -> SSHManager or TelnetManager
  -> return session_id
  -> frontend enters connected state
```

### 13.4 Terminal Command Execution

```text
User enters command
  -> terminalStore.executeCommand()
  -> terminalService.execute()
  -> POST /api/terminal/execute
  -> TerminalService.execute_command()
  -> TerminalManager.execute_command()
  -> execute through SSH/Telnet session
  -> clean output
  -> append terminal output in the frontend
```

## 14. Current Operational Concerns and Evolution Paths

The following items are maintenance considerations visible from the current code structure. They are not production incident conclusions.

### 14.1 Production Proxy Rules

The frontend relies on Vite to rewrite `/api` to `/api/v1` during development. Production deployments must provide the same proxy behavior, or frontend `baseURL` and backend API prefixes must be updated together.

### 14.2 Boundary Between the Two Device-Access Paths

Both `/terminal/*` and `/network/*` can connect to devices, but they use different state models and underlying libraries. Future work should keep this boundary documented and avoid mixing connection IDs with session IDs in business logic.

### 14.3 Terminal Connection Cancellation

`/terminal/cancel-connect` is currently closer to an API-level placeholder. To cancel an in-flight low-level connection for real, the task cancellation mechanism needs to be extended further.

### 14.4 Multi-Instance Deployment

AI providers, terminal sessions, and network connections are primarily process-local today. Multi-worker or multi-instance deployments will need shared state, sticky sessions, or connection routing.

### 14.5 Telnet Dependency Evolution

The Telnet path still depends on `telnetlib`. Python upgrades should include an early review of replacement libraries or compatibility layers.

### 14.6 Credential Management

Device passwords and API keys currently flow through environment variables, request payloads, and process-local state. Production deployments should prefer a secret manager, audit logging, and stronger credential lifecycle controls.

## 15. Documentation Maintenance Rules

Update this document and the root README pair when changing any of the following:

- API paths or request / response models;
- AI providers, model lists, persona prompts, or search-injection logic;
- frontend theme, layout, state management, or runtime ports;
- startup scripts and quality gates;
- terminal connection policy, security policy, or logging policy;
- test directories and verification entry points.
