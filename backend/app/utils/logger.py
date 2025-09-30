import logging
import logging.handlers
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import sys
import os

from app.config.settings import settings


class LoggerManager:
    """日志管理器 - 统一管理所有日志配置"""
    
    def __init__(self, log_base_dir: str = "../logs"):
        self.log_base_dir = Path(log_base_dir)
        self.loggers: Dict[str, logging.Logger] = {}
        
        # 确保日志目录存在
        self._create_log_directories()
    
    def _create_log_directories(self):
        """创建日志目录结构"""
        directories = ["app", "access", "error", "backend", "frontend"]
        for directory in directories:
            (self.log_base_dir / directory).mkdir(parents=True, exist_ok=True)
    
    def get_logger(
        self,
        name: str,
        level: str = None,
        log_to_file: bool = True,
        log_to_console: bool = True,
        max_bytes: int = 10485760,  # 10MB
        backup_count: int = 10
    ) -> logging.Logger:
        """
        获取配置好的日志器

        Args:
            name: 日志器名称
            level: 日志级别
            log_to_file: 是否输出到文件
            log_to_console: 是否输出到控制台
            max_bytes: 单个日志文件最大字节数
            backup_count: 保留的历史文件数量
        """
        if level is None:
            level = settings.LOG_LEVEL

        if name in self.loggers:
            return self.loggers[name]

        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level.upper()))

        # 防止重复添加handler
        if logger.handlers:
            logger.handlers.clear()

        # 防止日志传播到父logger，避免重复输出
        logger.propagate = False

        # 日志格式
        if settings.LOG_FORMAT.lower() == "json":
            formatter = JsonFormatter()
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )

        # 文件日志处理器
        if log_to_file:
            log_file = self._get_log_file_path(name)
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(getattr(logging, level.upper()))
            logger.addHandler(file_handler)

        # 控制台日志处理器
        if log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            console_handler.setLevel(getattr(logging, level.upper()))
            logger.addHandler(console_handler)

        # 错误日志单独处理器（ERROR级别及以上写入error目录）
        if level.upper() in ["DEBUG", "INFO", "WARNING"]:
            error_log_file = self.log_base_dir / "error" / f"error-{datetime.now().strftime('%Y-%m-%d')}.log"
            error_handler = logging.handlers.RotatingFileHandler(
                error_log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            error_handler.setFormatter(formatter)
            error_handler.setLevel(logging.ERROR)
            logger.addHandler(error_handler)

        self.loggers[name] = logger
        return logger
    
    def _get_log_file_path(self, logger_name: str) -> Path:
        """根据日志器名称确定日志文件路径"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        if "backend" in logger_name.lower():
            return self.log_base_dir / "backend" / f"backend-{today}.log"
        elif "frontend" in logger_name.lower():
            return self.log_base_dir / "frontend" / f"frontend-{today}.log"
        elif "access" in logger_name.lower():
            return self.log_base_dir / "access" / f"access-{today}.log"
        elif "error" in logger_name.lower():
            return self.log_base_dir / "error" / f"error-{today}.log"
        else:
            return self.log_base_dir / "app" / f"{logger_name}-{today}.log"
    
    def configure_uvicorn_logging(self, log_level: str = None):
        """配置Uvicorn的日志输出到文件"""
        if log_level is None:
            log_level = settings.LOG_LEVEL
            
        # 配置访问日志
        access_logger = self.get_logger(
            "uvicorn.access", 
            log_level, 
            log_to_console=False
        )
        
        # 配置错误日志
        error_logger = self.get_logger("uvicorn.error", log_level)
        
        # 应用到uvicorn
        uvicorn_access = logging.getLogger("uvicorn.access")
        uvicorn_error = logging.getLogger("uvicorn.error")
        
        uvicorn_access.handlers = access_logger.handlers
        uvicorn_error.handlers = error_logger.handlers
        
        uvicorn_access.propagate = False
        uvicorn_error.propagate = False
    
    def get_file_logger_only(self, name: str, level: str = None) -> logging.Logger:
        """获取仅输出到文件的日志器（用于后台任务）"""
        if level is None:
            level = settings.LOG_LEVEL
        return self.get_logger(name, level, log_to_file=True, log_to_console=False)
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """清理过期的日志文件"""
        import time
        
        cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
        cleaned_count = 0
        
        for log_dir in ["app", "access", "error", "backend", "frontend"]:
            log_path = self.log_base_dir / log_dir
            if log_path.exists():
                for log_file in log_path.glob("*.log*"):
                    try:
                        if log_file.stat().st_mtime < cutoff_time:
                            log_file.unlink()
                            cleaned_count += 1
                    except OSError:
                        pass  # 文件可能正在使用
        
        if cleaned_count > 0:
            print(f"已清理 {cleaned_count} 个过期日志文件")


class JsonFormatter(logging.Formatter):
    """JSON格式的日志格式化器"""
    
    def format(self, record: logging.LogRecord) -> str:
        """将日志记录格式化为JSON"""
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # 添加异常信息（如果有）
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # 添加额外字段
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_data.update(record.extra)
        
        return json.dumps(log_data, ensure_ascii=False)


# 全局日志管理器实例
logger_manager = LoggerManager()

def setup_logger() -> None:
    """配置应用日志 - 兼容原有接口"""
    # 配置主应用日志器
    app_logger = logger_manager.get_logger("backend")

    # 配置uvicorn日志
    logger_manager.configure_uvicorn_logging()

    # 设置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))

    # 清理默认处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 添加新的处理器
    for handler in app_logger.handlers:
        root_logger.addHandler(handler)

def get_logger(name: str, level: str = None) -> logging.Logger:
    """获取命名的日志记录器 - 兼容原有接口"""
    if level is None:
        level = settings.LOG_LEVEL

    return logger_manager.get_logger(name, level)

# 注意：不再在模块级别自动调用setup_logger()
# 这防止了模块导入时的重复日志配置
# setup_logger()应该仅在需要时由run.py调用