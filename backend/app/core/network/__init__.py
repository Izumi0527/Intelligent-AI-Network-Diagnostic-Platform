"""
网络连接核心模块
"""

from .base import NetworkConnection, DeviceType, ConnectionStatus
from .telnet import telnet_manager, TelnetManager

__all__ = [
    'NetworkConnection',
    'DeviceType', 
    'ConnectionStatus',
    'telnet_manager',
    'TelnetManager'
]