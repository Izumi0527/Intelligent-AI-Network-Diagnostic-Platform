import os
from pydantic_settings import BaseSettings
from typing import Optional, Dict, Any, List

class Settings(BaseSettings):
    """应用配置"""
    # 应用设置
    APP_ENV: Optional[str] = os.getenv("APP_ENV")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    API_PREFIX: Optional[str] = os.getenv("API_PREFIX")
    API_V1_STR: Optional[str] = os.getenv("API_V1_STR")
    PROJECT_NAME: Optional[str] = os.getenv("APP_NAME")
    APP_VERSION: Optional[str] = os.getenv("APP_VERSION")
    
    # CORS设置
    BACKEND_CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else []
    
    # 安全设置
    SECRET_KEY: Optional[str] = os.getenv("SECRET_KEY")
    JWT_ALGORITHM: Optional[str] = os.getenv("JWT_ALGORITHM")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "0"))
    
    # 服务器设置
    HOST: Optional[str] = os.getenv("HOST")
    PORT: int = int(os.getenv("PORT", "0"))
    
    # 会话设置
    SESSION_IDLE_TIMEOUT: int = int(os.getenv("SESSION_IDLE_TIMEOUT", "0"))
    MAX_TERMINAL_SESSIONS: int = int(os.getenv("MAX_TERMINAL_SESSIONS", "0"))
    
    # 日志设置
    LOG_LEVEL: Optional[str] = os.getenv("LOG_LEVEL")
    LOG_FORMAT: Optional[str] = os.getenv("LOG_FORMAT")
    
    # AI设置
    AI_ENABLED: bool = os.getenv("AI_ENABLED", "false").lower() == "true"
    
    # API密钥 - Anthropic (Claude)
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    ANTHROPIC_API_BASE: Optional[str] = os.getenv("ANTHROPIC_API_BASE")
    CLAUDE_MODEL_VERSION: Optional[str] = os.getenv("CLAUDE_MODEL_VERSION")
    
    # API密钥 - OpenAI (GPT)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_API_BASE: Optional[str] = os.getenv("OPENAI_API_BASE")
    
    # API密钥 - Deepseek
    DEEPSEEK_API_ENABLED: bool = os.getenv("DEEPSEEK_API_ENABLED", "false").lower() == "true"
    DEEPSEEK_API_KEY: Optional[str] = os.getenv("DEEPSEEK_API_KEY")
    DEEPSEEK_API_URL: Optional[str] = os.getenv("DEEPSEEK_API_URL")
    DEEPSEEK_MODEL_VERSION: Optional[str] = os.getenv("DEEPSEEK_MODEL_VERSION")
    DEEPSEEK_TIMEOUT: int = int(os.getenv("DEEPSEEK_TIMEOUT", "0"))
    DEEPSEEK_MAX_TOKENS: int = int(os.getenv("DEEPSEEK_MAX_TOKENS", "0"))
    
    # 模型列表配置
    OPENAI_MODELS: Optional[str] = os.getenv("OPENAI_MODELS")
    OPENAI_MODEL_NAMES: Optional[str] = os.getenv("OPENAI_MODEL_NAMES")
    OPENAI_MODEL_DESCRIPTIONS: Optional[str] = os.getenv("OPENAI_MODEL_DESCRIPTIONS")
    OPENAI_MODEL_MAX_TOKENS: Optional[str] = os.getenv("OPENAI_MODEL_MAX_TOKENS")
    
    CLAUDE_MODELS: Optional[str] = os.getenv("CLAUDE_MODELS")
    CLAUDE_MODEL_NAMES: Optional[str] = os.getenv("CLAUDE_MODEL_NAMES")
    CLAUDE_MODEL_DESCRIPTIONS: Optional[str] = os.getenv("CLAUDE_MODEL_DESCRIPTIONS")
    CLAUDE_MODEL_MAX_TOKENS: Optional[str] = os.getenv("CLAUDE_MODEL_MAX_TOKENS")

    # Deepseek模型列表配置
    DEEPSEEK_MODELS: Optional[str] = os.getenv("DEEPSEEK_MODELS")
    DEEPSEEK_MODEL_NAMES: Optional[str] = os.getenv("DEEPSEEK_MODEL_NAMES")
    DEEPSEEK_MODEL_DESCRIPTIONS: Optional[str] = os.getenv("DEEPSEEK_MODEL_DESCRIPTIONS")
    DEEPSEEK_MODEL_MAX_TOKENS: Optional[str] = os.getenv("DEEPSEEK_MODEL_MAX_TOKENS")

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "allow"
    }

    def model_post_init(self, __context: Any) -> None:  # type: ignore[override]
        """验证必需配置项并规范化配置"""
        # 验证必需的基础配置项
        self._validate_required_config()

        # 规范化 API_PREFIX：确保以 / 开头、无结尾 /
        prefix = (self.API_PREFIX or "/api").strip()
        if not prefix.startswith("/"):
            prefix = "/" + prefix
        prefix = prefix.rstrip("/")
        self.API_PREFIX = prefix

        # 若未通过环境变量显式提供 API_V1_STR，则按前缀计算 /v1
        if os.getenv("API_V1_STR") is None:
            self.API_V1_STR = f"{self.API_PREFIX}/v1"

        # 验证必需的AI配置项
        self._validate_ai_config()

    def _validate_required_config(self) -> None:
        """验证必需的基础配置项"""
        required_configs = [
            ("APP_ENV", self.APP_ENV),
            ("API_PREFIX", self.API_PREFIX),
            ("APP_NAME", self.PROJECT_NAME),
            ("APP_VERSION", self.APP_VERSION),
            ("SECRET_KEY", self.SECRET_KEY),
            ("JWT_ALGORITHM", self.JWT_ALGORITHM),
            ("HOST", self.HOST),
            ("LOG_LEVEL", self.LOG_LEVEL),
            ("LOG_FORMAT", self.LOG_FORMAT),
        ]

        missing_configs = []
        zero_configs = []

        for config_name, config_value in required_configs:
            if not config_value:
                missing_configs.append(config_name)

        # 检查数值型配置是否为0（可能未设置）
        if self.PORT == 0:
            zero_configs.append("PORT")
        if self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES == 0:
            zero_configs.append("JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
        if self.SESSION_IDLE_TIMEOUT == 0:
            zero_configs.append("SESSION_IDLE_TIMEOUT")
        if self.MAX_TERMINAL_SESSIONS == 0:
            zero_configs.append("MAX_TERMINAL_SESSIONS")

        error_messages = []
        if missing_configs:
            error_messages.append(f"以下基础配置项在.env文件中缺失或为空: {', '.join(missing_configs)}")
        if zero_configs:
            error_messages.append(f"以下数值配置项可能未正确设置(当前为0): {', '.join(zero_configs)}")

        if error_messages:
            raise ValueError(
                f"配置验证失败:\n" + "\n".join(error_messages) +
                f"\n请检查.env文件并确保所有必需的配置项都已正确设置。"
            )

    def _validate_ai_config(self) -> None:
        """验证AI相关配置的完整性"""
        if not self.AI_ENABLED:
            return

        # 验证基础AI配置项
        basic_ai_configs = [
            ("ANTHROPIC_API_BASE", self.ANTHROPIC_API_BASE),
            ("OPENAI_API_BASE", self.OPENAI_API_BASE),
            ("DEEPSEEK_API_URL", self.DEEPSEEK_API_URL),
        ]

        # 验证Deepseek数值配置
        deepseek_numeric_configs = []
        if self.DEEPSEEK_TIMEOUT == 0:
            deepseek_numeric_configs.append("DEEPSEEK_TIMEOUT")
        if self.DEEPSEEK_MAX_TOKENS == 0:
            deepseek_numeric_configs.append("DEEPSEEK_MAX_TOKENS")

        # 验证必需的配置项
        required_configs = [
            ("CLAUDE_MODEL_VERSION", self.CLAUDE_MODEL_VERSION),
            ("DEEPSEEK_MODEL_VERSION", self.DEEPSEEK_MODEL_VERSION),
            ("OPENAI_MODELS", self.OPENAI_MODELS),
            ("OPENAI_MODEL_NAMES", self.OPENAI_MODEL_NAMES),
            ("OPENAI_MODEL_DESCRIPTIONS", self.OPENAI_MODEL_DESCRIPTIONS),
            ("OPENAI_MODEL_MAX_TOKENS", self.OPENAI_MODEL_MAX_TOKENS),
            ("CLAUDE_MODELS", self.CLAUDE_MODELS),
            ("CLAUDE_MODEL_NAMES", self.CLAUDE_MODEL_NAMES),
            ("CLAUDE_MODEL_DESCRIPTIONS", self.CLAUDE_MODEL_DESCRIPTIONS),
            ("CLAUDE_MODEL_MAX_TOKENS", self.CLAUDE_MODEL_MAX_TOKENS),
            ("DEEPSEEK_MODELS", self.DEEPSEEK_MODELS),
            ("DEEPSEEK_MODEL_NAMES", self.DEEPSEEK_MODEL_NAMES),
            ("DEEPSEEK_MODEL_DESCRIPTIONS", self.DEEPSEEK_MODEL_DESCRIPTIONS),
            ("DEEPSEEK_MODEL_MAX_TOKENS", self.DEEPSEEK_MODEL_MAX_TOKENS),
        ]

        missing_configs = []
        missing_basic_configs = []

        # 检查基础AI配置
        for config_name, config_value in basic_ai_configs:
            if not config_value:
                missing_basic_configs.append(config_name)

        # 检查模型配置
        for config_name, config_value in required_configs:
            if not config_value:
                missing_configs.append(config_name)

        error_messages = []
        if missing_basic_configs:
            error_messages.append(f"以下AI基础配置项在.env文件中缺失或为空: {', '.join(missing_basic_configs)}")
        if deepseek_numeric_configs:
            error_messages.append(f"以下Deepseek数值配置项可能未正确设置(当前为0): {', '.join(deepseek_numeric_configs)}")
        if missing_configs:
            error_messages.append(f"以下AI模型配置项在.env文件中缺失或为空: {', '.join(missing_configs)}")

        if error_messages:
            raise ValueError(
                f"AI配置验证失败:\n" + "\n".join(error_messages) +
                f"\n请检查.env文件并确保所有必需的AI配置项都已正确设置。"
            )

# 创建全局设置实例
settings = Settings() 
