"""
Telnet连接管理器 - 兼容性适配器
保持原有接口兼容性，内部使用重构后的模块
"""

from app.core.network.telnet import telnet_manager as new_telnet_manager
from app.utils.logger import get_logger

logger = get_logger(__name__)

# 为了保持向后兼容性，导出TelnetManager类
class TelnetManager:
    """Telnet管理器兼容性包装"""
    
    def __init__(self):
        self.manager = new_telnet_manager
        logger.info("使用重构后的Telnet管理器")
    
    async def connect(self, host: str, port: int = 23, username: str = "", password: str = "", 
                     device_type: str = "unknown", timeout: int = 30):
        """建立连接 - 兼容原接口"""
        return await self.manager.connect(host, port, username, password, device_type, timeout)
    
    async def execute_command(self, session_id: str, command: str):
        """执行命令 - 兼容原接口"""
        return await self.manager.execute_command(session_id, command)
    
    async def disconnect(self, session_id: str):
        """断开连接 - 兼容原接口"""
        return await self.manager.disconnect(session_id)
    
    def get_session_info(self, session_id: str):
        """获取会话信息 - 兼容原接口"""
        return self.manager.get_session_info(session_id)
    
    def get_all_sessions(self):
        """获取所有会话 - 兼容原接口"""
        return self.manager.get_all_sessions()
    
    async def cleanup_idle_sessions(self, timeout: int = 7200):
        """清理空闲会话 - 兼容原接口"""
        return await self.manager.cleanup_idle_sessions(timeout)


# 提供原有的全局实例以保持兼容性
telnet_manager = new_telnet_manager