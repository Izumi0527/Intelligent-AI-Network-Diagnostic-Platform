import logging
import json
from typing import Dict, Any, Optional
import sys

from app.config.settings import settings

# 配置根日志记录器
def setup_logger() -> None:
    """配置应用日志"""
    log_level = getattr(logging, settings.LOG_LEVEL, logging.INFO)
    
    # 创建处理程序
    handler = logging.StreamHandler(sys.stdout)
    
    # 设置格式
    if settings.LOG_FORMAT.lower() == "json":
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    handler.setFormatter(formatter)
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 移除所有现有处理程序并添加新的
    for hdlr in root_logger.handlers:
        root_logger.removeHandler(hdlr)
    root_logger.addHandler(handler)
    
    # 静默第三方库的日志
    for logger_name in ["uvicorn", "uvicorn.access"]:
        logger = logging.getLogger(logger_name)
        logger.propagate = False

class JsonFormatter(logging.Formatter):
    """JSON格式的日志格式化器"""
    
    def format(self, record: logging.LogRecord) -> str:
        """将日志记录格式化为JSON"""
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        
        # 添加异常信息（如果有）
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # 添加额外字段
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_data.update(record.extra)
        
        return json.dumps(log_data)

def get_logger(name: str) -> logging.Logger:
    """获取命名的日志记录器"""
    return logging.getLogger(name)

# 设置应用日志
setup_logger()