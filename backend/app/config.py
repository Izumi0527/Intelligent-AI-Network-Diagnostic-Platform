from typing import List, Union
import os
from pydantic import AnyHttpUrl, validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

class Settings(BaseSettings):
    # 应用设置
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_PREFIX: str = "/api"
    APP_NAME: str = "AI智能网络故障分析平台"
    APP_VERSION: str = "0.1.0"
    
    # 服务器设置
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:5174"]
    
    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # 安全设置
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 数据库配置
    DATABASE_URL: str
    
    # AI模型配置
    ANTHROPIC_API_KEY: str
    CLAUDE_MODEL_VERSION: str = "claude-3.7-sonnet-20240229"
    
    # 会话配置
    SESSION_IDLE_TIMEOUT: int = 600  # 10分钟超时
    MAX_TERMINAL_SESSIONS: int = 5  # 最大同时活跃会话数
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    class Config:
        case_sensitive = True
        env_file = ".env"

# 创建全局可访问的设置实例
settings = Settings() 