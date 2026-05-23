from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from app.config.settings import settings

router = APIRouter()


class HealthResponse(BaseModel):
    """健康检查响应"""

    status: str
    details: dict[str, Any]


READY_REQUIRED_SETTINGS = {
    "APP_ENV": "APP_ENV",
    "API_PREFIX": "API_PREFIX",
    "API_V1_STR": "API_V1_STR",
    "APP_NAME": "PROJECT_NAME",
    "APP_VERSION": "APP_VERSION",
    "HOST": "HOST",
    "PORT": "PORT",
    "LOG_LEVEL": "LOG_LEVEL",
    "LOG_FORMAT": "LOG_FORMAT",
}

READY_REQUIRED_SERVICES = (
    "terminal_service",
    "ai_service_manager",
    "rate_limiter",
)


@router.get("", response_model=HealthResponse)
async def health_check():
    """轻量 API 存活检查，不触发外部依赖调用。"""
    return HealthResponse(
        status="healthy",
        details={
            "ai_service": "not_checked",
            "network_service": "deprecated",
            "connection_count": 0,
            "model_count": "not_checked",
            "version": settings.APP_VERSION,
        },
    )


@router.get("/ready", response_model=HealthResponse)
async def readiness_check(request: Request):
    """就绪检查：只检查本地配置和应用内资源状态。"""
    missing_config = [
        env_name
        for env_name, attr_name in READY_REQUIRED_SETTINGS.items()
        if not getattr(settings, attr_name, None)
    ]
    service_status = {
        service_name: "available"
        if hasattr(request.app.state, service_name)
        else "missing"
        for service_name in READY_REQUIRED_SERVICES
    }
    missing_services = [
        service_name
        for service_name, service_state in service_status.items()
        if service_state != "available"
    ]

    details: dict[str, Any] = {
        "configuration": "ok" if not missing_config else "missing",
        "services": service_status,
        "version": settings.APP_VERSION,
    }

    if missing_config or missing_services:
        error_details = []
        if missing_config:
            error_details.append({"missing_config": missing_config})
        if missing_services:
            error_details.append({"missing_services": missing_services})

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "readiness_failed",
                "message": "服务未就绪",
                "details": error_details,
            },
        )

    return HealthResponse(status="ready", details=details)
