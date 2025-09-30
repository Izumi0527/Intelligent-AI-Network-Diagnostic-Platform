"""
Deepseek专用模块
提供Deepseek API访问和网络日志分析功能
"""

from .client import DeepseekClient, get_deepseek_client
from .analyzer import NetworkLogAnalyzer

# 使用懒加载函数代替直接实例化
deepseek_client = get_deepseek_client()

__all__ = [
    'DeepseekClient',
    'deepseek_client',
    'get_deepseek_client',
    'NetworkLogAnalyzer'
]