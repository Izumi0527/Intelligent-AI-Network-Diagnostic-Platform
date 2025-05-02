# Intelligent-AI-Network-Diagnostic-Platform

This project is an intelligent platform combining AI and network management, designed to connect network devices and provide AI-assisted fault analysis. The system supports multiple large language models (Claude, GPT, Deepseek, etc.) for intelligent analysis, offers streaming response interfaces, and enables real-time network device connections and command execution.

## Project Structure

The project consists of frontend and backend components:
project/
├── frontend/ # Vue 3 + TypeScript frontend application
│ ├── src/ # Source code directory
│ │ ├── components/ # Components
│ │ │ ├── ai-assistant/ # AI assistant components
│ │ │ ├── terminal/ # Terminal components
│ │ │ └── common/ # Common components (including icons)
│ │ ├── assets/ # Static assets
│ │ ├── composables/ # Composable functions
│ │ ├── layouts/ # Layout components
│ │ ├── stores/ # Pinia state management
│ │ ├── utils/ # Utility functions
│ │ ├── types/ # TypeScript type definitions
│ │ ├── views/ # Page view components
│ │ ├── App.vue # Main application component
│ │ └── main.ts # Application entry
│ ├── public/ # Public static assets
│ ├── lib/ # Third-party libraries
│ ├── vite.config.ts # Vite configuration
│ ├── tailwind.config.js # Tailwind configuration
│ ├── package.json # Frontend dependencies
│ └── index.html # HTML entry
└── backend/ # FastAPI backend application
├── app/ # Main application directory
│ ├── api/ # API routes
│ │ └── api_v1/ # V1 API
│ │ └── endpoints/ # API endpoints
│ │ ├── ai.py # AI assistant interfaces
│ │ ├── health.py # Health check interface
│ │ ├── network.py # Network device connection interface
│ │ └── terminal.py # Terminal session management interface
│ ├── services/ # Business services
│ ├── models/ # Data models
│ ├── core/ # Core functionalities
│ ├── utils/ # Utility functions
│ ├── config/ # Configuration
│ ├── main.py # Application entry point
│ └── config.py # Main configuration
├── run.py # Startup script
└── requirements.txt # Backend dependencies

## Key Features

- **Network Connectivity**: Supports SSH and Telnet protocols for connecting to network devices
- **Command Execution**: Execute remote network commands and retrieve results
- **AI Analysis**: Supports multiple LLMs for intelligent fault analysis
  - Claude (Anthropic)
  - GPT (OpenAI)
  - Deepseek
- **Streaming Responses**: Real-time streaming display of AI responses
- **Multiple Themes**: Responsive design with light/dark theme support
- **Terminal Sessions**: Multi-terminal session management with timeout control
- **Security**: JWT authentication system for secure access

## Technology Stack

### Frontend

- **Framework**: Vue 3.3+ + TypeScript 5.2+
- **UI**: Inspira UI + TailwindCSS 3.3+
- **State Management**: Pinia 2.1+
- **Build Tool**: Vite 5.0+
- **HTTP Client**: Axios 1.6+
- **Utilities**:
  - VueUse 10.7+
  - clsx 2.0+
  - tailwind-merge 2.0+
  - class-variance-authority 0.7+
  - tailwindcss-animate 1.0+

### Backend

- **Framework**: FastAPI 0.104+ + Pydantic 2.4+
- **Server**: Uvicorn 0.23+
- **Network Tools**:
  - Paramiko 3.3+ (SSH connections)
  - Netmiko 4.2+ (Network device connections)
- **AI Integration**:
  - Anthropic API (Claude)
  - OpenAI API (GPT)
  - Deepseek API
- **Async Processing**:
  - aiohttp 3.8+
  - sse-starlette 1.6+ (Server-Sent Events)
- **HTTP Clients**:
  - aiohttp 3.8+
  - httpx 0.24+
  - requests 2.31+
- **Security**:
  - python-jose 3.3+ (JWT)
  - passlib 1.7+ (Password)
  - bcrypt 4.0+
- **Environment**: python-dotenv 1.0+

## Quick Start

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows
.\venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure .env file
cp .env.example .env
# Edit .env file to set API keys and other configurations

# Start server
python run.py

cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Build production version
npm run build

Environment Variables
Key backend environment variables:

APP_ENV: Application environment (development/production)

AI_ENABLED: Enable AI features

ANTHROPIC_API_KEY: Claude API key

CLAUDE_MODEL_VERSION: Claude model version

OPENAI_API_KEY: OpenAI API key

DEEPSEEK_API_KEY: Deepseek API key

SECRET_KEY: Application secret key

JWT_ACCESS_TOKEN_EXPIRE_MINUTES: JWT token expiration time

MAX_TERMINAL_SESSIONS: Maximum terminal sessions

SESSION_IDLE_TIMEOUT: Session idle timeout (seconds)

HOST: Binding host (default: 0.0.0.0)

PORT: Binding port (default: 8000)

LOG_LEVEL: Logging level

Access Points
Frontend: http://localhost:5173

Backend API: http://localhost:8000

API Documentation: http://localhost:8000/api/v1/docs

API Endpoints
Main API endpoints:

/api/v1/health: Health check

/api/v1/network: Network device connections

/api/v1/terminal: Terminal session management

/api/v1/ai: AI assistant interface

Development Notes
Backend Development
Built with FastAPI framework following RESTful API design principles. Key files:

app/main.py: Main application entry with FastAPI instance and middleware

app/api/api_v1/endpoints/: API endpoint handlers

run.py: Server startup script handling CLI arguments and environment

Frontend Development
Developed using Vue 3 Composition API and TypeScript. Features:

Pinia state management

Responsive layout supporting multiple devices

Component-based architecture for maintainability

License
MIT
