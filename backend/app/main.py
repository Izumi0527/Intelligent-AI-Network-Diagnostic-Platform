import asyncio
import inspect
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.api.api_v1.api import api_router
from app.config.settings import settings
from app.core.rate_limit import InMemoryRateLimiter, RateLimitMiddleware, RateLimitRule
from app.services.ai.manager import AIServiceManager
from app.services.deepseek_service import DeepseekService
from app.services.terminal_service import TerminalService
from app.utils.logger import get_logger

# 使用统一的日志管理器获取logger
logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件。"""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(
            f"{request.method} {request.url.path} - {response.status_code} ({process_time:.2f}s)"
        )
        return response


async def cleanup_idle_sessions(terminal_service):
    """定期清理闲置的终端会话"""
    while True:
        try:
            result = await terminal_service.cleanup_idle_sessions()
            if result["cleaned_count"] > 0:
                logger.info(f"定期清理: {result['message']}")
        except Exception as e:
            logger.error(f"定期清理任务出错: {str(e)}")
        # 每5分钟运行一次
        await asyncio.sleep(300)


def _initialize_application_services(application: FastAPI) -> None:
    """在应用实例范围内统一创建服务，避免模块级全局单例。"""
    application.state.terminal_service = TerminalService()
    application.state.ai_service_manager = AIServiceManager()
    application.state.deepseek_service = DeepseekService()
    application.state.rate_limiter = InMemoryRateLimiter()


async def _cleanup_service(service) -> None:
    """清理具备 cleanup 方法的服务实例。"""
    cleanup = getattr(service, "cleanup", None)
    if cleanup is None:
        return

    result = cleanup()
    if inspect.isawaitable(result):
        await result


@asynccontextmanager
async def lifespan(application: FastAPI):
    """应用生命周期：统一启动和取消后台任务。"""
    _initialize_application_services(application)
    terminal_service = application.state.terminal_service
    start_terminal_tasks = getattr(terminal_service, "start_background_tasks", None)
    if start_terminal_tasks:
        start_terminal_tasks()

    application.state.cleanup_task = asyncio.create_task(
        cleanup_idle_sessions(terminal_service)
    )
    logger.info("已启动定期会话清理任务")

    try:
        yield
    finally:
        if hasattr(application.state, "cleanup_task"):
            application.state.cleanup_task.cancel()
            try:
                await application.state.cleanup_task
            except asyncio.CancelledError:
                logger.info("已取消定期会话清理任务")

        for service_name in (
            "terminal_service",
            "deepseek_service",
            "ai_service_manager",
        ):
            if hasattr(application.state, service_name):
                await _cleanup_service(getattr(application.state, service_name))


def _api_documentation_urls() -> dict[str, str | None]:
    """生产环境关闭文档和 OpenAPI 枚举入口。"""
    if (settings.APP_ENV or "").lower() == "production":
        return {
            "openapi_url": None,
            "docs_url": None,
            "redoc_url": None,
        }

    return {
        "openapi_url": f"{settings.API_V1_STR}/openapi.json",
        "docs_url": f"{settings.API_V1_STR}/docs",
        "redoc_url": f"{settings.API_V1_STR}/redoc",
    }


def create_app() -> FastAPI:
    """创建 FastAPI 应用，便于不同环境下测试启动配置。"""
    application = FastAPI(
        title=settings.PROJECT_NAME,
        lifespan=lifespan,
        **_api_documentation_urls(),
    )

    cors_origins = [origin for origin in settings.BACKEND_CORS_ORIGINS if origin != "*"]
    if cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in cors_origins],
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "Accept", "Origin"],
        )

    application.add_middleware(
        RateLimitMiddleware,
        rules=[
            RateLimitRule(
                scope="ai",
                path_prefix=f"{settings.API_V1_STR}/ai",
                limit=settings.AI_RATE_LIMIT_PER_MINUTE,
                window_seconds=60,
            ),
            RateLimitRule(
                scope="terminal",
                path_prefix=f"{settings.API_V1_STR}/terminal",
                limit=settings.TERMINAL_RATE_LIMIT_PER_MINUTE,
                window_seconds=60,
            ),
        ],
    )
    application.add_middleware(LoggingMiddleware)
    application.include_router(api_router, prefix=settings.API_V1_STR)

    @application.get("/")
    async def root():
        """根路径返回服务状态。"""
        if (settings.APP_ENV or "").lower() == "production":
            return {"message": "API 服务运行中"}
        return {"message": f"请访问 {settings.API_V1_STR}/docs 查看API文档"}

    return application


# 创建 FastAPI 应用
app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
