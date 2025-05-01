from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union

class DeepseekMessage(BaseModel):
    """聊天消息模型"""
    role: str = Field(..., description="消息角色，可选：system, user, assistant")
    content: str = Field(..., description="消息内容")

class DeepseekGenerateRequest(BaseModel):
    """Deepseek生成文本请求模型"""
    messages: List[DeepseekMessage] = Field(..., description="消息列表")
    model: str = Field("deepseek-chat", description="使用的模型名称")
    max_tokens: Optional[int] = Field(4096, description="最大生成令牌数")
    temperature: Optional[float] = Field(0.7, description="生成文本的随机性")
    top_p: Optional[float] = Field(0.9, description="Top-p采样参数")
    stream: Optional[bool] = Field(False, description="是否使用流式响应")

class DeepseekDelta(BaseModel):
    """增量响应内容"""
    content: Optional[str] = Field(None, description="增量内容")
    role: Optional[str] = Field(None, description="角色")

class DeepseekChoice(BaseModel):
    """Deepseek生成结果的选项"""
    index: int = Field(..., description="选项索引")
    delta: Optional[DeepseekDelta] = Field(None, description="增量内容")
    message: Optional[DeepseekMessage] = Field(None, description="完整消息")
    finish_reason: Optional[str] = Field(None, description="结束原因")

class DeepseekResponse(BaseModel):
    """Deepseek API响应模型"""
    id: str = Field(..., description="请求ID")
    object: str = Field(..., description="对象类型")
    created: int = Field(..., description="创建时间戳")
    model: str = Field(..., description="使用的模型")
    choices: List[DeepseekChoice] = Field(..., description="生成结果")
    usage: Dict[str, int] = Field(..., description="令牌使用情况")

class DeepseekErrorResponse(BaseModel):
    """Deepseek API错误响应"""
    error: str = Field(..., description="错误信息")
    details: Optional[str] = Field(None, description="详细错误信息")

class DeepseekAnalyzeRequest(BaseModel):
    """网络日志分析请求"""
    log_content: str = Field(..., description="网络日志内容")
    query: str = Field(..., description="用户查询")
    model: Optional[str] = Field("deepseek-chat", description="使用的模型名称，可选: deepseek-reasoner 或 deepseek-chat")
    temperature: Optional[float] = Field(0.3, description="生成文本的随机性")

class DeepseekModelInfo(BaseModel):
    """Deepseek模型信息"""
    id: str = Field(..., description="模型ID")
    name: str = Field(..., description="模型名称")
    description: Optional[str] = Field(None, description="模型描述")
