import os
from pydantic_settings import BaseSettings
from typing import Optional, Dict, Any, List

class Settings(BaseSettings):
    """应用配置"""
    # 应用设置
    APP_ENV: str = os.getenv("APP_ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = os.getenv("APP_NAME", "AI智能网络故障分析平台")
    APP_VERSION: str = os.getenv("APP_VERSION", "0.1.0")
    
    # CORS设置
    BACKEND_CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # 安全设置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # 服务器设置
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # 会话设置
    SESSION_IDLE_TIMEOUT: int = int(os.getenv("SESSION_IDLE_TIMEOUT", "600"))
    MAX_TERMINAL_SESSIONS: int = int(os.getenv("MAX_TERMINAL_SESSIONS", "5"))
    
    # 日志设置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "standard")
    
    # AI设置
    AI_ENABLED: bool = os.getenv("AI_ENABLED", "true").lower() == "true"
    
    # API密钥 - Anthropic (Claude)
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    CLAUDE_MODEL_VERSION: str = os.getenv("CLAUDE_MODEL_VERSION", "claude-3-sonnet-20240229")
    
    # API密钥 - OpenAI (GPT)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # API密钥 - Deepseek
    DEEPSEEK_API_ENABLED: bool = os.getenv("DEEPSEEK_API_ENABLED", "true").lower() == "true"
    DEEPSEEK_API_KEY: Optional[str] = os.getenv("DEEPSEEK_API_KEY")
    DEEPSEEK_API_URL: str = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1")
    DEEPSEEK_MODEL_VERSION: str = os.getenv("DEEPSEEK_MODEL_VERSION", "deepseek-chat")
    DEEPSEEK_TIMEOUT: int = int(os.getenv("DEEPSEEK_TIMEOUT", "30"))
    DEEPSEEK_MAX_TOKENS: int = int(os.getenv("DEEPSEEK_MAX_TOKENS", "4096"))
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "allow"
    }

# 创建全局设置实例
settings = Settings() 