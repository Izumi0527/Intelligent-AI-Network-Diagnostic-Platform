from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from sse_starlette.sse import EventSourceResponse
from fastapi.responses import StreamingResponse, JSONResponse
from typing import List, Dict, Any, Optional
from pydantic import ValidationError
from datetime import datetime
import json
import time
import asyncio

from app.models.ai import (
    ChatRequest, ChatResponse, ModelsResponse,
    ModelConnectionStatus, StreamEvent, Message
)
from app.services.ai.manager import AIServiceManager
from app.services.deepseek_service import DeepseekService
from app.api.deps import get_ai_service_manager, get_deepseek_service
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

@router.get("/models", response_model=ModelsResponse)
async def get_models(
    ai_manager: AIServiceManager = Depends(get_ai_service_manager)
):
    """获取可用的AI模型列表"""
    return await ai_manager.get_models_response()

@router.get("/models/{model_id}/status", response_model=ModelConnectionStatus)
async def check_model_status(
    model_id: str,
    ai_manager: AIServiceManager = Depends(get_ai_service_manager)
):
    """检查模型连接状态"""
    is_connected, message = await ai_manager.check_model_status(model_id)
    return ModelConnectionStatus(
        connected=is_connected,
        message=message,
        last_check=datetime.now().isoformat()
    )

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    ai_manager: AIServiceManager = Depends(get_ai_service_manager)
):
    """AI聊天API（非流式）"""
    try:
        if not request.model:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="必须指定模型"
            )
        
        # 记录请求信息，帮助排查问题
        logger.info(f"接收聊天请求: 模型={request.model}, 消息数量={len(request.messages)}")
        
        # 记录详细的消息内容用于调试
        message_summary = []
        for i, msg in enumerate(request.messages):
            # 限制内容长度防止日志过大
            content_preview = msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
            message_summary.append(f"[{i}] {msg.role}: {content_preview}")
        
        logger.debug(f"消息详情: {'; '.join(message_summary)}")
        
        # 格式化请求消息，确保时间戳正确
        for msg in request.messages:
            if not msg.timestamp:
                msg.timestamp = None  # 让模型自动设置默认值
        
        # 获取聊天响应
        response = await ai_manager.chat(request)
        
        # 确保content字段存在，方便前端访问
        if not hasattr(response, 'content') or not response.content:
            response.content = response.message.content
            
        return response
    except ValidationError as e:
        # 记录详细验证错误
        logger.error(f"请求参数验证错误: {str(e)}")
        
        # 提取并记录原始请求数据，帮助排查问题
        try:
            if hasattr(request, "__dict__"):
                req_dict = {k: str(v)[:100] for k, v in request.__dict__.items()}
                logger.error(f"原始请求数据: {req_dict}")
        except Exception as ex:
            logger.error(f"无法记录原始请求数据: {str(ex)}")
        
        # 尝试提取更具体的错误信息
        error_detail = str(e)
        loc = ["body", "request"]
        
        # 如果错误包含字段位置信息，提取出来
        if hasattr(e, "errors") and isinstance(e.errors(), list):
            errors = e.errors()
            if errors and "loc" in errors[0]:
                loc = errors[0]["loc"]
                error_detail = errors[0].get("msg", str(e))
        
        # 返回更友好的错误信息
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": [
                    {
                        "loc": loc,
                        "msg": f"请求参数验证失败: {error_detail}",
                        "type": "value_error"
                    }
                ]
            }
        )
    except Exception as e:
        logger.error(f"处理聊天请求时出错: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"服务器错误: {str(e)}"
        )

def encode_event(event: dict) -> str:
    """将事件编码为SSE格式字符串"""
    if isinstance(event, str):
        # 如果已经是字符串（可能是SSE格式）
        return event
    
    # 如果是字典，转换为SSE格式
    if "event" in event:
        output = [f"event: {event['event']}"]
    else:
        output = ["event: message"]
    
    if "data" in event:
        data = event["data"]
        json_data = json.dumps(data)
        output.append(f"data: {json_data}")
    
    return "\n".join(output) + "\n\n"

@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    req: Request,
    ai_manager: AIServiceManager = Depends(get_ai_service_manager)
):
    """AI聊天API（流式响应） - 修复版本"""
    try:
        if not request.model:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="必须指定模型"
            )
        
        # 记录请求信息
        logger.info(f"接收流式聊天请求: 模型={request.model}, 消息数量={len(request.messages)}")
        
        # 生成会话ID用于跟踪此次对话
        session_id = f"stream_{int(time.time() * 1000)}"
        logger.info(f"开始新的流式会话: {session_id}")
        
        # 确保请求是流式的
        request.stream = True
        
        # 简化流式处理：正确处理异步生成器
        async def generate_text_stream():
            try:
                # 使用异步生成器，调用正确的chat_stream方法
                async for event in ai_manager.chat_stream(request):
                    if event.type == "content":
                        # 提取内容数据
                        content = event.data.get("content", "")
                        if content:
                            yield content
                    elif event.type == "thinking":
                        # 处理思考内容 - 发送 SSE 格式的思考事件
                        thinking = event.data.get("thinking", "")
                        if thinking:
                            import json
                            # 发送JSON格式的思考事件给前端
                            thinking_event = json.dumps({
                                "type": "thinking",
                                "data": {"thinking": thinking}
                            }, ensure_ascii=False)
                            yield f"data: {thinking_event}\n\n"
                    elif event.type == "error":
                        error_msg = event.data.get("error", "未知错误")
                        logger.error(f"流式生成内容时出错: {error_msg}")
                        yield f"错误: {error_msg}"
                        break
                    elif event.type == "done":
                        # 流式响应结束
                        logger.info(f"流式会话 {session_id} 已完成")
                        break

            except Exception as e:
                logger.error(f"流式生成内容时出错: {e}")
                yield f"错误: {str(e)}"
        
        # 返回文本流响应
        return StreamingResponse(
            generate_text_stream(),
            media_type="text/event-stream",
        )
                
    except Exception as e:
        logger.error(f"处理流式聊天请求时出错: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"服务器错误: {str(e)}"
        )

# 添加一个辅助接口，用于调试消息格式
@router.post("/debug/request-format")
async def debug_request_format(
    raw_request: Dict[str, Any] = Body(...),
):
    """调试API - 回显请求格式，帮助排查格式问题"""
    try:
        # 尝试验证请求格式
        messages = []
        for msg_data in raw_request.get("messages", []):
            try:
                # 尝试创建消息对象
                msg = Message(**msg_data)
                messages.append(msg.dict())
            except ValidationError as e:
                messages.append({
                    "original": msg_data,
                    "errors": str(e)
                })
        
        # 返回请求解析结果
        return {
            "original_request": raw_request,
            "parsed_messages": messages,
            "is_valid": len([m for m in messages if "errors" in m]) == 0
        }
    except Exception as e:
        return {
            "error": f"解析请求时出错: {str(e)}",
            "original_request": raw_request
        }

@router.get("/deepseek/status")
async def check_deepseek_connection(
    ai_manager: AIServiceManager = Depends(get_ai_service_manager)
):
    """检查Deepseek API连接状态"""
    # 通过AI管理器检查Deepseek模型状态
    deepseek_models = [model for model in ai_manager.get_available_models()
                      if model.value.startswith('deepseek-')]

    if not deepseek_models:
        return {
            "connected": False,
            "message": "未找到Deepseek模型",
            "models": []
        }

    # 检查第一个Deepseek模型的连接状态
    model_id = deepseek_models[0].value
    is_connected, message = await ai_manager.check_model_status(model_id)

    return {
        "connected": is_connected,
        "message": message,
        "models": [model.value for model in deepseek_models]
    }

@router.post("/deepseek/generate")
async def generate_text(
    messages: List[Dict[str, str]] = Body(..., description="消息列表，格式为[{\"role\": \"user\", \"content\": \"内容\"}]", embed=True),
    max_tokens: int = Body(2048, description="最大生成令牌数"),
    temperature: float = Body(0.7, description="生成文本的随机性"),
    stream: bool = Body(False, description="是否使用流式响应"),
    model: str = Body("deepseek-chat", description="使用的模型名称，可选: deepseek-reasoner 或 deepseek-chat"),
    ai_manager: AIServiceManager = Depends(get_ai_service_manager)
):
    """使用AI Manager调用Deepseek生成文本"""
    try:
        # 将字典消息转换为Message对象
        message_objects = [
            Message(role=msg.get("role", "user"), content=msg.get("content", ""))
            for msg in messages
        ]

        # 创建ChatRequest
        request = ChatRequest(
            model=model,
            messages=message_objects,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=stream
        )

        if stream:
            # 使用流式响应
            async def generate_stream():
                try:
                    async for event in ai_manager.chat_stream(request):
                        if event.type == "content":
                            content = event.data.get("content", "")
                            if content:
                                yield f"data: {json.dumps({'content': content})}\n\n"
                        elif event.type == "done":
                            yield f"data: {json.dumps({'done': True})}\n\n"
                            break
                        elif event.type == "error":
                            error_msg = event.data.get("error", "未知错误")
                            yield f"data: {json.dumps({'error': error_msg})}\n\n"
                            break
                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"

            return StreamingResponse(generate_stream(), media_type="text/event-stream")
        else:
            # 非流式响应
            response = await ai_manager.chat(request)
            return {
                "content": response.message.content,
                "model": response.model,
                "usage": response.usage,
                "id": getattr(response, 'id', None)
            }

    except Exception as e:
        logger.error(f"Deepseek文本生成失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文本生成失败: {str(e)}"
        )

@router.post("/deepseek/analyze-network-log")
async def analyze_network_log(
    log_content: str = Body(..., description="网络日志内容", embed=True),
    query: str = Body(..., description="用户查询", embed=True),
    model: str = Body("deepseek-chat", description="使用的模型名称，可选: deepseek-reasoner 或 deepseek-chat"),
    deepseek_service: DeepseekService = Depends(get_deepseek_service)
):
    """使用Deepseek分析网络日志"""
    return StreamingResponse(
        deepseek_service.analyze_network_log(log_content, query, model),
        media_type="text/event-stream"
    ) 