from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

AI_MAX_MESSAGES = 50
AI_MAX_MESSAGE_CONTENT_LENGTH = 8000
AI_MAX_TOTAL_MESSAGE_CONTENT_LENGTH = 32000
AI_MAX_TOKENS = 8192


class AIModel(BaseModel):
    """AI模型信息"""

    value: str = Field(..., description="模型ID")
    label: str = Field(..., description="模型显示名称")
    description: Optional[str] = Field(None, description="模型描述")
    features: list[str] = Field(default_factory=list, description="模型支持的功能")
    max_tokens: int = Field(..., description="最大token数")

class Message(BaseModel):
    """聊天消息"""

    model_config = ConfigDict(extra="ignore")

    role: Literal["user", "assistant"] = Field(..., description="消息角色")
    content: str = Field(
        ...,
        description="消息内容",
        max_length=AI_MAX_MESSAGE_CONTENT_LENGTH,
    )
    timestamp: Optional[datetime] = Field(
        default_factory=datetime.now,
        description="消息时间戳",
    )

    # 添加验证器，确保content不为空
    @field_validator("content")
    @classmethod
    def content_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("消息内容不能为空")
        return value.strip()


# 扩展消息类型，用于处理前端可能发送的简化消息格式
class SimpleMessage(BaseModel):
    """简化的消息格式，用于与前端交互"""

    model_config = ConfigDict(extra="ignore")

    role: str
    content: str


class ChatRequest(BaseModel):
    """聊天请求模型"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "model": "deepseek-v4-pro",
                "messages": [
                    {
                        "role": "user",
                        "content": "如何解决交换机端口状态显示up但无法正常通信的问题？",
                    }
                ],
                "stream": True,
            }
        }
    )

    model: str = Field(..., description="模型名称", min_length=1, max_length=100)
    messages: list[Message] = Field(
        ...,
        description="消息历史",
        min_length=1,
        max_length=AI_MAX_MESSAGES,
    )
    max_tokens: Optional[int] = Field(
        None,
        description="最大生成token数",
        ge=1,
        le=AI_MAX_TOKENS,
    )
    temperature: Optional[float] = Field(
        None,
        description="生成温度",
        ge=0,
        le=2,
    )
    top_p: Optional[float] = Field(None, description="top p值", ge=0, le=1)
    stream: bool = Field(False, description="是否使用流式响应")

    @field_validator("messages", mode="before")
    @classmethod
    def messages_not_empty(cls, value: Any) -> Any:
        """确保消息列表不为空且所有消息内容有效"""
        # 基本验证：列表非空
        if not value:
            raise ValueError("消息列表不能为空")

        valid_messages = []
        conversion_errors = []

        # 尝试转换和验证每条消息
        for i, message in enumerate(value):
            try:
                # 如果是字典（例如来自JSON的未验证数据），尝试转换为Message
                if isinstance(message, dict):
                    message = dict(message)
                    # 确保基本字段存在
                    if not message.get("role"):
                        message["role"] = "user"

                    if not message.get("content"):
                        if "content" in message and message["content"] == "":
                            continue
                        elif "content" not in message:
                            continue

                    # 验证内容不全为空白字符
                    if (
                        isinstance(message.get("content"), str)
                        and message["content"].strip() == ""
                    ):
                        continue

                    try:
                        # 尝试转换为Message对象
                        valid_msg = Message(**message)
                        valid_messages.append(valid_msg)
                    except Exception as e:
                        conversion_errors.append((i, str(e)))
                        continue
                else:
                    # 已经是Message对象，验证内容非空
                    if not message.content or (
                        isinstance(message.content, str)
                        and message.content.strip() == ""
                    ):
                        continue
                    valid_messages.append(message)
            except Exception as e:
                conversion_errors.append((i, str(e)))
                continue

        # 如果没有有效消息，抛出错误
        if not valid_messages:
            error_detail = "所有消息均无效"
            if conversion_errors:
                error_detail += f"，转换错误: {conversion_errors}"
            raise ValueError(error_detail)

        total_content_length = sum(len(message.content) for message in valid_messages)
        if total_content_length > AI_MAX_TOTAL_MESSAGE_CONTENT_LENGTH:
            raise ValueError("消息总长度超出限制")

        return valid_messages


class ChatResponse(BaseModel):
    """聊天响应"""

    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "example": {
                "message": {
                    "role": "assistant",
                    "content": "我是DeepSeek-V4-Pro大语言模型。",
                },
                "model": "deepseek-v4-pro",
                "content": "我是DeepSeek-V4-Pro大语言模型。",
                "finish_reason": "stop",
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 12,
                    "total_tokens": 22,
                },
            }
        },
    )

    id: Optional[str] = Field(None, description="响应或请求追踪ID")
    message: Message
    model: str = Field(..., description="使用的AI模型")
    finish_reason: Optional[str] = Field(None, description="结束原因")
    usage: dict[str, Any] = Field(default_factory=dict, description="使用情况统计")
    content: Optional[str] = Field(None, description="响应内容，方便前端直接获取")


class ModelConnectionStatus(BaseModel):
    """模型连接状态"""

    connected: bool = Field(..., description="是否连接成功")
    message: str = Field(..., description="状态消息")
    last_check: str = Field(..., description="最后检查时间")

class ModelsResponse(BaseModel):
    """可用模型列表响应"""

    models: list[AIModel] = Field(..., description="可用的模型列表")
    status: dict[str, ModelConnectionStatus] = Field(
        default_factory=dict,
        description="各提供商连接状态",
    )


class DeepseekGenerateRequest(BaseModel):
    """Deepseek 兼容生成请求"""

    messages: list[Message] = Field(
        ...,
        description="消息列表",
        min_length=1,
        max_length=AI_MAX_MESSAGES,
    )
    max_tokens: int = Field(2048, description="最大生成令牌数", ge=1, le=AI_MAX_TOKENS)
    temperature: float = Field(0.7, description="生成文本的随机性", ge=0, le=2)
    stream: bool = Field(False, description="是否使用流式响应")
    model: str = Field(
        "deepseek-v4-pro",
        description="使用的模型名称",
        min_length=1,
        max_length=100,
    )
    top_p: Optional[float] = Field(None, description="top p值", ge=0, le=1)

    @field_validator("messages")
    @classmethod
    def message_total_length_within_limit(cls, value: list[Message]) -> list[Message]:
        total_content_length = sum(len(message.content) for message in value)
        if total_content_length > AI_MAX_TOTAL_MESSAGE_CONTENT_LENGTH:
            raise ValueError("消息总长度超出限制")
        return value


class StreamEvent(BaseModel):
    """流式响应事件"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "content",
                "data": {
                    "content": "交换机端口状态显示up但无法正常通信",
                },
            }
        }
    )

    type: Literal[
        "content",
        "error",
        "done",
        "finish",
        "thinking",
        "message_start",
        "content_block_start",
        "content_block_delta",
        "content_block_stop",
        "message_delta",
        "message_stop",
    ]
    data: dict[str, Any]
