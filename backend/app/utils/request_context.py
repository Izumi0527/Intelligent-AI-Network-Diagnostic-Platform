"""请求级上下文工具。"""

from contextvars import ContextVar
from uuid import uuid4

_request_id_var: ContextVar[str | None] = ContextVar(
    "request_id",
    default=None,
)


def new_request_id() -> str:
    """生成新的请求追踪 ID。"""
    return str(uuid4())


def get_request_id() -> str | None:
    """读取当前上下文中的请求追踪 ID。"""
    return _request_id_var.get()


def set_request_id(request_id: str | None):
    """设置当前上下文请求追踪 ID，并返回可重置 token。"""
    return _request_id_var.set(request_id)


def reset_request_id(token) -> None:
    """恢复请求追踪 ID 上下文。"""
    _request_id_var.reset(token)
