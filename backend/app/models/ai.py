from typing import Dict, List, Optional, Literal, Any, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime
import logging
from app.utils.logger import get_logger

logger = get_logger(__name__)

class AIModel(BaseModel):
    """AI模型信息"""
    value: str = Field(..., description="模型ID")
    label: str = Field(..., description="模型显示名称")
    description: Optional[str] = Field(None, description="模型描述")
    features: List[str] = Field(default_factory=list, description="模型支持的功能")
    max_tokens: int = Field(..., description="最大token数")

class Message(BaseModel):
    """聊天消息"""
    role: Literal["user", "assistant"] = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now, description="消息时间戳")
    
    # 添加验证器，确保content不为空
    @validator('content')
    def content_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('消息内容不能为空')
        return v.strip()
    
    class Config:
        # 允许额外字段，提高与不同API的兼容性
        extra = "ignore"

# 扩展消息类型，用于处理前端可能发送的简化消息格式
class SimpleMessage(BaseModel):
    """简化的消息格式，用于与前端交互"""
    role: str
    content: str
    
    class Config:
        extra = "ignore"

class ChatRequest(BaseModel):
    """聊天请求模型"""
    model: str = Field(..., description="模型名称")
    messages: List[Message] = Field(..., description="消息历史")
    max_tokens: Optional[int] = Field(None, description="最大生成token数")
    temperature: Optional[float] = Field(None, description="生成温度")
    top_p: Optional[float] = Field(None, description="top p值")
    stream: bool = Field(False, description="是否使用流式响应")
    
    @validator('messages')
    def messages_not_empty(cls, v):
        """确保消息列表不为空且所有消息内容有效"""
        # 基本验证：列表非空
        if not v:
            raise ValueError('消息列表不能为空')
        
        valid_messages = []
        conversion_errors = []
        
        # 尝试转换和验证每条消息
        for i, message in enumerate(v):
            try:
                # 如果是字典（例如来自JSON的未验证数据），尝试转换为Message
                if isinstance(message, dict):
                    # 确保基本字段存在
                    if not message.get('role'):
                        logger.warning(f"消息{i}缺少role字段，默认设为'user'")
                        message['role'] = 'user'
                        
                    if not message.get('content'):
                        if 'content' in message and message['content'] == '':
                            logger.warning(f"消息{i}内容为空，将被跳过")
                            continue
                        elif 'content' not in message:
                            logger.warning(f"消息{i}缺少content字段，将被跳过")
                            continue
                            
                    # 验证内容不全为空白字符
                    if isinstance(message.get('content'), str) and message['content'].strip() == '':
                        logger.warning(f"消息{i}内容全为空白字符，将被跳过")
                        continue
                        
                    try:
                        # 尝试转换为Message对象
                        valid_msg = Message(**message)
                        valid_messages.append(valid_msg)
                    except Exception as e:
                        logger.warning(f"消息{i}转换失败: {str(e)}，将被跳过")
                        conversion_errors.append((i, str(e)))
                        continue
                else:
                    # 已经是Message对象，验证内容非空
                    if not message.content or (isinstance(message.content, str) and message.content.strip() == ''):
                        logger.warning(f"消息{i}内容为空，将被跳过")
                        continue
                    valid_messages.append(message)
            except Exception as e:
                logger.error(f"处理消息{i}时出错: {str(e)}")
                conversion_errors.append((i, str(e)))
                continue
        
        # 如果没有有效消息，抛出错误
        if not valid_messages:
            error_detail = "所有消息均无效"
            if conversion_errors:
                error_detail += f"，转换错误: {conversion_errors}"
            raise ValueError(error_detail)
            
        return valid_messages
    
    class Config:
        json_schema_extra = {
            "example": {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "user",
                        "content": "如何解决交换机端口状态显示up但无法正常通信的问题？"
                    }
                ],
                "stream": True
            }
        }

class ChatResponse(BaseModel):
    """聊天响应"""
    message: Message
    model: str = Field(..., description="使用的AI模型")
    finish_reason: Optional[str] = Field(None, description="结束原因")
    usage: Dict[str, Any] = Field(default_factory=dict, description="使用情况统计")
    content: Optional[str] = Field(None, description="响应内容，方便前端直接获取")
    
    class Config:
        # 允许额外字段
        extra = "ignore"
        
        json_schema_extra = {
            "example": {
                "message": {
                    "role": "assistant",
                    "content": "我是DeepSeek-V3-0324大语言模型。"
                },
                "model": "deepseek-chat",
                "content": "我是DeepSeek-V3-0324大语言模型。",
                "finish_reason": "stop",
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 12,
                    "total_tokens": 22
                }
            }
        }

class ModelConnectionStatus(BaseModel):
    """模型连接状态"""
    connected: bool = Field(..., description="是否连接成功")
    message: str = Field(..., description="状态消息")
    last_check: str = Field(..., description="最后检查时间")

class ModelsResponse(BaseModel):
    """可用模型列表响应"""
    models: List[AIModel] = Field(..., description="可用的模型列表")
    status: Dict[str, ModelConnectionStatus] = Field(default_factory=dict, description="各提供商连接状态")

class StreamEvent(BaseModel):
    """流式响应事件"""
    type: Literal["content", "error", "done", "finish", "thinking", "message_start", "content_block_start", "content_block_delta", "content_block_stop", "message_delta", "message_stop"]
    data: Dict[str, Any]

    class Config:
        json_schema_extra = {
            "example": {
                "type": "content",
                "data": {
                    "content": "交换机端口状态显示up但无法正常通信"
                }
            }
        } 