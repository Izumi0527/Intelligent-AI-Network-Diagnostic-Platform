"""
Deepseek网络日志分析器
专门处理网络日志分析相关功能
"""

import json
import re
from typing import Dict, List, Any, Optional, AsyncGenerator
import httpx
from datetime import datetime

from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class NetworkLogAnalyzer:
    """Deepseek网络日志分析器"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = getattr(settings, 'DEEPSEEK_API_URL', 'https://api.deepseek.com/v1')
        self.timeout = getattr(settings, 'DEEPSEEK_TIMEOUT', 30)
        self.max_tokens = getattr(settings, 'DEEPSEEK_MAX_TOKENS', 4096)
        self.client = None
        
        # 网络日志分析专用提示模板
        self.analysis_templates = {
            "error_analysis": """
请分析以下网络设备错误日志，提供详细的问题诊断和解决方案：

日志内容：
{log_content}

请按照以下格式分析：
1. 问题识别：
2. 根本原因：
3. 影响评估：
4. 解决方案：
5. 预防措施：
""",
            "performance_analysis": """
请分析以下网络性能数据，识别潜在的性能瓶颈：

性能数据：
{log_content}

请提供：
1. 性能指标分析
2. 瓶颈识别
3. 优化建议
4. 监控建议
""",
            "security_analysis": """
请分析以下安全日志，识别潜在的安全威胁：

安全日志：
{log_content}

请提供：
1. 威胁识别
2. 风险评估
3. 应对措施
4. 安全建议
"""
        }
    
    async def initialize(self):
        """初始化HTTP客户端"""
        if not self.client:
            self.client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
    
    async def cleanup(self):
        """清理资源"""
        if self.client:
            await self.client.aclose()
            self.client = None
    
    async def analyze_network_log(self, log_content: str, analysis_type: str = "error_analysis") -> Dict[str, Any]:
        """分析网络日志"""
        try:
            await self.initialize()
            
            if analysis_type not in self.analysis_templates:
                analysis_type = "error_analysis"
            
            prompt = self.analysis_templates[analysis_type].format(log_content=log_content)
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一名资深的网络工程师，专门分析网络设备日志和诊断网络问题。"
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                "max_tokens": self.max_tokens,
                "temperature": 0.3  # 降低随机性，提高准确性
            }
            
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                choices = result.get('choices', [])
                if choices:
                    content = choices[0].get('message', {}).get('content', '')
                    return {
                        "success": True,
                        "analysis": content,
                        "analysis_type": analysis_type,
                        "timestamp": datetime.now().isoformat(),
                        "usage": result.get('usage', {})
                    }
            
            return {
                "success": False,
                "error": f"API请求失败: HTTP {response.status_code}",
                "analysis_type": analysis_type,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"网络日志分析异常: {str(e)}")
            return {
                "success": False,
                "error": f"分析异常: {str(e)}",
                "analysis_type": analysis_type,
                "timestamp": datetime.now().isoformat()
            }
    
    async def analyze_log_stream(self, log_content: str, analysis_type: str = "error_analysis") -> AsyncGenerator[Dict[str, Any], None]:
        """流式分析网络日志"""
        try:
            await self.initialize()
            
            if analysis_type not in self.analysis_templates:
                analysis_type = "error_analysis"
            
            prompt = self.analysis_templates[analysis_type].format(log_content=log_content)
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一名资深的网络工程师，专门分析网络设备日志和诊断网络问题。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": self.max_tokens,
                "temperature": 0.3,
                "stream": True
            }
            
            async with self.client.stream(
                "POST",
                f"{self.base_url}/chat/completions", 
                json=payload
            ) as response:
                
                if response.status_code != 200:
                    yield {
                        "type": "error",
                        "data": {"error": f"API请求失败: HTTP {response.status_code}"}
                    }
                    return
                
                async for line in response.aiter_lines():
                    if line.strip():
                        if line.startswith('data: '):
                            data_text = line[6:]  # 去掉 'data: ' 前缀
                            
                            if data_text.strip() == '[DONE]':
                                yield {"type": "done", "data": {}}
                                break
                            
                            try:
                                data = json.loads(data_text)
                                choices = data.get('choices', [])
                                if choices:
                                    delta = choices[0].get('delta', {})
                                    content = delta.get('content', '')
                                    if content:
                                        yield {
                                            "type": "content",
                                            "data": {"content": content}
                                        }
                            except json.JSONDecodeError:
                                continue
                                
        except Exception as e:
            logger.error(f"流式网络日志分析异常: {str(e)}")
            yield {
                "type": "error",
                "data": {"error": f"分析异常: {str(e)}"}
            }
    
    def classify_log_type(self, log_content: str) -> str:
        """自动分类日志类型"""
        log_lower = log_content.lower()
        
        # 错误关键词
        error_keywords = ['error', 'failed', 'fail', 'down', 'timeout', 'unreachable', 'denied']
        # 性能关键词
        performance_keywords = ['cpu', 'memory', 'bandwidth', 'latency', 'utilization', 'load']
        # 安全关键词
        security_keywords = ['security', 'attack', 'intrusion', 'unauthorized', 'breach', 'malicious']
        
        error_count = sum(1 for keyword in error_keywords if keyword in log_lower)
        performance_count = sum(1 for keyword in performance_keywords if keyword in log_lower)
        security_count = sum(1 for keyword in security_keywords if keyword in log_lower)
        
        # 返回匹配度最高的分类
        max_count = max(error_count, performance_count, security_count)
        
        if max_count == 0:
            return "error_analysis"  # 默认
        elif error_count == max_count:
            return "error_analysis"
        elif security_count == max_count:
            return "security_analysis"
        else:
            return "performance_analysis"
    
    def extract_log_patterns(self, log_content: str) -> Dict[str, List[str]]:
        """提取日志中的关键模式"""
        patterns = {
            "ip_addresses": re.findall(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', log_content),
            "timestamps": re.findall(r'\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}', log_content),
            "error_codes": re.findall(r'[Ee]rror[:\s]*(\d+)', log_content),
            "interfaces": re.findall(r'[Ii]nterface[:\s]*([A-Za-z0-9/-]+)', log_content),
            "protocols": re.findall(r'\b(TCP|UDP|HTTP|HTTPS|SSH|TELNET|SNMP)\b', log_content, re.IGNORECASE)
        }
        
        return patterns