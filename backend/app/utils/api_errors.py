"""统一 API 错误响应工具。"""

from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.requests import Request

from app.utils.request_context import get_request_id, new_request_id, set_request_id

ERROR_CODE_BY_STATUS = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    410: "gone",
    422: "validation_error",
    429: "rate_limit_exceeded",
    500: "internal_error",
    502: "upstream_error",
    503: "service_unavailable",
}

DEFAULT_MESSAGE_BY_STATUS = {
    400: "请求参数错误",
    401: "未授权",
    403: "禁止访问",
    404: "资源不存在",
    410: "资源已废弃",
    422: "请求参数验证失败",
    429: "请求过于频繁，请稍后重试",
    500: "内部服务器错误",
    502: "上游服务暂时不可用",
    503: "服务暂时不可用",
}


def ensure_request_id(request: Request | None = None) -> str:
    """从请求或上下文读取 request_id；缺失时生成并写回上下文。"""
    if request is not None and hasattr(request.state, "request_id"):
        request_id = request.state.request_id
        if request_id:
            return request_id

    request_id = None
    if request is not None:
        request_id = request.headers.get("X-Request-ID")
    request_id = request_id or get_request_id() or new_request_id()

    if request is not None:
        request.state.request_id = request_id
    set_request_id(request_id)
    return request_id


def error_code_for_status(status_code: int) -> str:
    """按 HTTP 状态码给出稳定错误码。"""
    return ERROR_CODE_BY_STATUS.get(status_code, "http_error")


def api_error_response(
    *,
    status_code: int,
    message: str | None = None,
    code: str | None = None,
    details: list[Any] | None = None,
    request: Request | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """构造统一 API 错误响应。"""
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(
            {
                "error": {
                    "code": code or error_code_for_status(status_code),
                    "message": message
                    or DEFAULT_MESSAGE_BY_STATUS.get(status_code, "请求失败"),
                    "request_id": ensure_request_id(request),
                    "details": details or [],
                }
            }
        ),
        headers=headers,
    )


def normalize_http_detail(
    detail: Any,
    status_code: int,
) -> tuple[str, str, list[Any]]:
    """把 HTTPException.detail 规范化为 code、message、details。"""
    if isinstance(detail, dict):
        code = str(detail.get("code") or error_code_for_status(status_code))
        message = str(
            detail.get("message")
            or detail.get("error")
            or DEFAULT_MESSAGE_BY_STATUS.get(status_code, "请求失败")
        )
        details = detail.get("details", [])
        if details is None:
            details = []
        if not isinstance(details, list):
            details = [details]

        extra = {
            key: value
            for key, value in detail.items()
            if key not in {"code", "message", "error", "details"}
        }
        if extra:
            details = [*details, extra]
        return code, message, details

    if isinstance(detail, list):
        return (
            error_code_for_status(status_code),
            DEFAULT_MESSAGE_BY_STATUS.get(status_code, "请求失败"),
            detail,
        )

    message = str(detail or DEFAULT_MESSAGE_BY_STATUS.get(status_code, "请求失败"))
    return error_code_for_status(status_code), message, []
