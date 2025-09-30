"""
Telnet连接管理器
统一管理所有Telnet连接和会话
"""

import asyncio
import time
from typing import Dict, Any, Optional, Tuple, List
import uuid

from app.core.network.base import DeviceType, ConnectionStatus
from app.core.network.telnet.connection import TelnetConnection
from app.core.network.telnet.devices.huawei import HuaweiTelnetConnection
from app.utils.logger import get_logger
from app.utils.security import encrypt_device_password, decrypt_device_password

logger = get_logger(__name__)


class TelnetManager:
    """Telnet连接管理器"""
    
    def __init__(self):
        """初始化Telnet管理器"""
        self.sessions: Dict[str, TelnetConnection] = {}
        self.device_factories = {
            DeviceType.HUAWEI: HuaweiTelnetConnection,
            DeviceType.UNKNOWN: TelnetConnection,
        }
        self._cleanup_task = None
    
    def _create_connection(self, device_type: str, host: str, port: int, username: str, password: str) -> TelnetConnection:
        """根据设备类型创建相应的连接"""
        try:
            device_enum = DeviceType(device_type.lower())
        except ValueError:
            device_enum = DeviceType.UNKNOWN
        
        factory_class = self.device_factories.get(device_enum, TelnetConnection)
        return factory_class(host, port, username, password)
    
    async def connect(self, host: str, port: int, username: str, password: str,
                     device_type: str = "unknown", timeout: int = 30) -> Tuple[bool, str, Optional[str]]:
        """建立新连接"""
        try:
            logger.info(f"尝试连接到设备 {host}:{port} (类型: {device_type})")
            
            # 创建连接对象
            connection = self._create_connection(device_type, host, port, username, password)
            
            # 建立连接
            success, message = await connection.connect(timeout)
            
            if success:
                # 存储会话
                self.sessions[connection.session_id] = connection
                logger.info(f"会话 {connection.session_id} 创建成功")
                
                # 启动清理任务（如果未启动）
                if not self._cleanup_task:
                    self._start_cleanup_task()
                
                return True, f"连接成功，会话ID: {connection.session_id}", connection.session_id
            else:
                logger.error(f"连接失败: {message}")
                return False, message, None
                
        except Exception as e:
            error_msg = f"连接异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    async def execute_command(self, session_id: str, command: str) -> Tuple[bool, str]:
        """在指定会话中执行命令"""
        try:
            if session_id not in self.sessions:
                return False, "会话不存在"
            
            connection = self.sessions[session_id]
            
            if not connection.is_alive():
                # 连接已断开，清理会话
                await self._cleanup_session(session_id)
                return False, "连接已断开"
            
            logger.debug(f"在会话 {session_id} 中执行命令: {command}")
            return await connection.execute_command(command)
            
        except Exception as e:
            error_msg = f"命令执行异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    async def disconnect(self, session_id: str) -> Tuple[bool, str]:
        """断开指定会话"""
        try:
            if session_id not in self.sessions:
                return False, "会话不存在"
            
            connection = self.sessions[session_id]
            success, message = await connection.disconnect()
            
            # 从会话字典中移除
            del self.sessions[session_id]
            
            logger.info(f"会话 {session_id} 已断开")
            return success, message
            
        except Exception as e:
            error_msg = f"断开连接异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息"""
        if session_id not in self.sessions:
            return None
        
        connection = self.sessions[session_id]
        info = connection.get_info()
        info['is_alive'] = connection.is_alive()
        return info
    
    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """获取所有会话信息"""
        result = {}
        for session_id, connection in self.sessions.items():
            info = connection.get_info()
            info['is_alive'] = connection.is_alive()
            result[session_id] = info
        return result
    
    async def cleanup_idle_sessions(self, idle_timeout: int = 7200) -> Dict[str, Any]:
        """清理空闲会话"""
        current_time = time.time()
        cleanup_count = 0
        cleaned_sessions = []
        
        # 找出需要清理的会话
        sessions_to_cleanup = []
        for session_id, connection in self.sessions.items():
            if (connection.last_activity_time and 
                current_time - connection.last_activity_time > idle_timeout) or \
               not connection.is_alive():
                sessions_to_cleanup.append(session_id)
        
        # 清理会话
        for session_id in sessions_to_cleanup:
            try:
                await self._cleanup_session(session_id)
                cleanup_count += 1
                cleaned_sessions.append(session_id)
            except Exception as e:
                logger.error(f"清理会话 {session_id} 失败: {str(e)}")
        
        if cleanup_count > 0:
            logger.info(f"清理了 {cleanup_count} 个空闲或断开的会话")
        
        return {
            "cleaned_count": cleanup_count,
            "cleaned_sessions": cleaned_sessions,
            "message": f"清理了 {cleanup_count} 个会话",
            "remaining_sessions": len(self.sessions)
        }
    
    async def _cleanup_session(self, session_id: str):
        """清理单个会话"""
        if session_id in self.sessions:
            connection = self.sessions[session_id]
            try:
                await connection.disconnect()
            except:
                pass
            del self.sessions[session_id]
    
    def _start_cleanup_task(self):
        """启动定期清理任务"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            logger.debug("已启动定期会话清理任务")
    
    async def _periodic_cleanup(self):
        """定期清理任务"""
        try:
            while True:
                await asyncio.sleep(300)  # 每5分钟检查一次
                if self.sessions:
                    await self.cleanup_idle_sessions()
                else:
                    # 没有活跃会话时停止清理任务
                    break
        except asyncio.CancelledError:
            logger.debug("定期清理任务已取消")
        except Exception as e:
            logger.error(f"定期清理任务异常: {str(e)}")
    
    async def shutdown(self):
        """关闭管理器，清理所有资源"""
        logger.info("正在关闭Telnet管理器...")
        
        # 取消清理任务
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # 断开所有会话
        sessions_to_close = list(self.sessions.keys())
        for session_id in sessions_to_close:
            try:
                await self._cleanup_session(session_id)
            except Exception as e:
                logger.error(f"关闭会话 {session_id} 失败: {str(e)}")
        
        logger.info("Telnet管理器已关闭")
    
    def __len__(self):
        """返回活跃会话数量"""
        return len(self.sessions)


# 全局Telnet管理器实例
telnet_manager = TelnetManager()