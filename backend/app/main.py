import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import time

from app.api.api_v1.api import api_router
from app.config.settings import settings
from app.services.terminal_service import TerminalService
from app.utils.logger import get_logger

# 使用统一的日志管理器获取logger
logger = get_logger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# 添加CORS中间件
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# 日志中间件
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(
            f"{request.method} {request.url.path} - {response.status_code} ({process_time:.2f}s)"
        )
        return response

app.add_middleware(LoggingMiddleware)

# 添加路由
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    """根路径重定向到API文档"""
    return {"message": f"请访问 {settings.API_V1_STR}/docs 查看API文档"}

# 创建后台任务
async def cleanup_idle_sessions():
    """定期清理闲置的终端会话"""
    terminal_service = TerminalService()
    while True:
        try:
            result = await terminal_service.cleanup_idle_sessions()
            if result["cleaned_count"] > 0:
                logger.info(f"定期清理: {result['message']}")
        except Exception as e:
            logger.error(f"定期清理任务出错: {str(e)}")
        # 每5分钟运行一次
        await asyncio.sleep(300)

@app.on_event("startup")
async def start_background_tasks():
    """启动后台任务"""
    app.state.cleanup_task = asyncio.create_task(cleanup_idle_sessions())
    logger.info("已启动定期会话清理任务")

@app.on_event("shutdown")
async def shutdown_background_tasks():
    """关闭后台任务"""
    if hasattr(app.state, "cleanup_task"):
        app.state.cleanup_task.cancel()
        try:
            await app.state.cleanup_task
        except asyncio.CancelledError:
            logger.info("已取消定期会话清理任务")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app", 
        host=settings.HOST, 
        port=settings.PORT,
        reload=True
    ) 