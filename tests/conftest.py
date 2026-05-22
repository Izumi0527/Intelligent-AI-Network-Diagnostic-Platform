import os


DEFAULT_TEST_ENV = {
    "APP_ENV": "test",
    "API_PREFIX": "/api",
    "APP_NAME": "AI智能网络故障分析平台",
    "APP_VERSION": "0.1.0",
    "SECRET_KEY": "test-secret-key",
    "JWT_ALGORITHM": "HS256",
    "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": "30",
    "HOST": "127.0.0.1",
    "PORT": "8000",
    "CORS_ORIGINS": "http://localhost:5173,http://localhost:5174",
    "SESSION_IDLE_TIMEOUT": "600",
    "MAX_TERMINAL_SESSIONS": "5",
    "LOG_LEVEL": "INFO",
    "LOG_FORMAT": "standard",
    "AI_ENABLED": "false",
}


for key, value in DEFAULT_TEST_ENV.items():
    os.environ.setdefault(key, value)
