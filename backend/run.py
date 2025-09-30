import os
import sys
import signal
import logging
from pathlib import Path
import argparse
import traceback
from datetime import datetime

import uvicorn
from dotenv import load_dotenv

print("运行run.py脚本...")

# 确保加载环境变量
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

try:
    from app.config.settings import settings
    print("成功导入settings")
except ImportError as e:
    print(f"导入settings失败: {str(e)}")
    traceback.print_exc()
    sys.exit(1)

# 配置日志 - 使用统一的日志管理器
try:
    from app.utils.logger import logger_manager, setup_logger

    # 防止重复配置的全局标志
    if not hasattr(logger_manager, '_configured'):
        setup_logger()  # 只在第一次调用时配置
        logger_manager._configured = True

    # 获取后端应用的日志器
    logger = logger_manager.get_logger("backend")
    logger.info("日志管理器已配置完成")
    print("已配置日志管理器")
except Exception as e:
    print(f"配置日志失败: {str(e)}")
    traceback.print_exc()
    sys.exit(1)

# 检查必要的环境变量
def check_environment():
    """检查必要的环境变量和配置"""
    required_vars = []
    
    # 如果使用AI功能，需要检查AI API密钥
    ai_enabled = os.getenv("AI_ENABLED", "true").lower() == "true"
    if ai_enabled:
        if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"):
            logger.warning("警告: 未设置任何AI服务API密钥，AI功能可能不可用")
        
    # 检查应用设置
    if not os.getenv("SECRET_KEY"):
        logger.warning("警告: 未设置SECRET_KEY，使用默认值可能存在安全风险")

# 优雅退出处理
def handle_exit(signum, frame):
    """处理退出信号"""
    logger.info("接收到退出信号，正在关闭服务...")
    # 可以在这里添加清理代码
    sys.exit(0)

# 设置信号处理
signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

def parse_args():
    parser = argparse.ArgumentParser(description="AI智能网络故障分析平台")
    
    # 服务器参数
    parser.add_argument(
        "--host", 
        type=str, 
        default=settings.HOST,
        help="监听地址 (默认: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=settings.PORT, 
        help="监听端口 (默认: 8000)"
    )
    parser.add_argument(
        "--reload", 
        action="store_true", 
        default=settings.APP_ENV == "development",
        help="启用热加载"
    )
    
    return parser.parse_args()

# 主函数
def main():
    """主函数"""
    try:
        args = parse_args()
        
        print(f"启动服务器: host={args.host}, port={args.port}")
        
        # 记录启动信息
        logger.info(f"启动 AI智能网络故障分析平台 服务")
        logger.info(f"环境: {settings.APP_ENV}")
        logger.info(f"监听地址: {args.host}:{args.port}")
        
        # 启动服务器
        try:
            print("尝试启动uvicorn...")
            uvicorn.run(
                "app.main:app",
                host=args.host,
                port=args.port,
                reload=args.reload,
                log_level=settings.LOG_LEVEL.lower(),
            )
        except Exception as e:
            print(f"启动uvicorn错误: {str(e)}")
            traceback.print_exc()
            logger.error(f"服务器启动失败: {str(e)}")
            sys.exit(1)
    except Exception as e:
        print(f"main函数错误: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    try:
        print("调用main函数...")
        main()
    except Exception as e:
        print(f"全局错误: {str(e)}")
        traceback.print_exc()
        sys.exit(1) 