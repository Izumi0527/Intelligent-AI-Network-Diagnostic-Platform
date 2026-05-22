"""终端服务领域异常。

服务层只抛这些异常，不直接依赖 FastAPI；HTTP 状态码由路由层映射。
"""


class TerminalServiceError(Exception):
    """终端服务领域异常基类。"""

    def __init__(self, client_message: str, status_code: int = 500):
        super().__init__(client_message)
        self.client_message = client_message
        self.status_code = status_code


class TerminalPolicyViolation(TerminalServiceError):
    """终端目标或命令违反安全策略。"""


class TerminalSessionLimitExceeded(TerminalServiceError):
    """终端会话数超过配置上限。"""

    def __init__(self, client_message: str):
        super().__init__(client_message, status_code=429)


class TerminalConnectionFailed(TerminalServiceError):
    """终端连接或断开操作失败。"""


class SessionNotFound(TerminalServiceError):
    """终端会话不存在。"""

    def __init__(self, client_message: str):
        super().__init__(client_message, status_code=404)


class TerminalValidationFailed(TerminalServiceError):
    """终端请求参数验证失败。"""

    def __init__(self, client_message: str = "请求参数验证失败"):
        super().__init__(client_message, status_code=400)


class TerminalOperationFailed(TerminalServiceError):
    """终端服务内部操作失败。"""

    def __init__(self, client_message: str = "内部服务器错误"):
        super().__init__(client_message, status_code=500)
