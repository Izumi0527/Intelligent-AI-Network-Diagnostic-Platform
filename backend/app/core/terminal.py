import asyncio
import logging
from typing import Dict, Any, Optional, Tuple, List
import time

from app.utils.logger import get_logger
from app.core.ssh import SSHManager
from app.core.telnet import TelnetManager
from app.models.terminal import (
    SessionInfo, ConnectionType, ConnectionResponse,
    CommandResponse
)

logger = get_logger(__name__)

class TerminalManager:
    """终端管理器，整合SSH和Telnet功能"""
    
    def __init__(self):
        """初始化终端管理器"""
        self.ssh_manager = SSHManager()
        self.telnet_manager = TelnetManager()
        self.sessions: Dict[str, SessionInfo] = {}
        self.lock = asyncio.Lock()
        
        # 启动会话检查任务（如果是在异步环境中初始化的）
        try:
            loop = asyncio.get_event_loop()
            if not loop.is_closed():
                self.session_check_task = loop.create_task(self._session_check_routine())
        except Exception as e:
            logger.warning(f"无法启动会话检查任务: {str(e)}")
    
    async def _session_check_routine(self):
        """定期检查会话状态并执行保活操作"""
        try:
            while True:
                try:
                    await self._check_and_keep_alive_sessions()
                except Exception as e:
                    logger.error(f"会话检查例程出错: {str(e)}")
                    
                # 每60秒检查一次
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            logger.info("会话检查任务已取消")
    
    async def _check_and_keep_alive_sessions(self):
        """检查所有会话状态并执行保活操作"""
        current_time = time.time()
        ssh_session_ids = []
        
        # 找出需要检查的SSH会话
        for session_id, session in self.sessions.items():
            if session.connection_type == "ssh":
                # 如果会话在过去2分钟内有活动，我们不需要检查它
                if (current_time - session.last_activity) < 120:
                    continue
                ssh_session_ids.append(session_id)
        
        # 对每个SSH会话执行检查
        for session_id in ssh_session_ids:
            if session_id in self.sessions:  # 确保会话仍然存在
                try:
                    # 检查会话状态
                    is_active = await self.ssh_manager.check_session_active(session_id)
                    
                    if not is_active:
                        logger.warning(f"SSH会话 {session_id} 已失效，将在下次使用时尝试恢复")
                except Exception as e:
                    logger.error(f"检查SSH会话 {session_id} 状态时出错: {str(e)}")
        
    async def connect(
        self, connection_type: ConnectionType, 
        device_address: str, port: int, 
        username: str, password: str
    ) -> ConnectionResponse:
        """创建新的终端连接"""
        try:
            if connection_type == "ssh":
                success, message, session_id = await self.ssh_manager.connect(
                    device_address, port, username, password
                )
            elif connection_type == "telnet":
                success, message, session_id = await self.telnet_manager.connect(
                    device_address, port, username, password
                )
            else:
                return ConnectionResponse(
                    success=False,
                    message=f"不支持的连接类型: {connection_type}",
                    session_id=None
                )
                
            if not success or not session_id:
                return ConnectionResponse(
                    success=False,
                    message=message,
                    session_id=None
                )
            
            # 获取设备信息
            device_info = ""
            if connection_type == "ssh" and session_id:
                session_info = self.ssh_manager.get_session_info(session_id)
                if session_info and "device_info" in session_info:
                    device_info = session_info["device_info"]
            elif connection_type == "telnet" and session_id:
                session_info = self.telnet_manager.get_session_info(session_id)
                if session_info and "device_info" in session_info:
                    device_info = session_info["device_info"]
            
            # 创建会话信息
            async with self.lock:
                self.sessions[session_id] = SessionInfo(
                    session_id=session_id,
                    connection_type=connection_type,
                    device_address=device_address,
                    port=port,
                    username=username,
                    is_active=True,
                    last_activity=time.time()  # 确保设置初始活动时间
                )
            
            return ConnectionResponse(
                success=True,
                session_id=session_id,
                message=message,
                device_info=device_info
            )
            
        except Exception as e:
            logger.error(f"创建终端连接时出错: {str(e)}")
            return ConnectionResponse(
                success=False,
                message=f"创建连接时出错: {str(e)}",
                session_id=None
            )
    
    async def execute_command(self, session_id: str, command: str) -> CommandResponse:
        """在终端会话中执行命令"""
        if session_id not in self.sessions:
            return CommandResponse(
                session_id=session_id,
                output="错误: 会话不存在或已过期",
                is_error=True
            )
        
        session = self.sessions[session_id]
        
        try:
            # 更新会话最后活动时间
            session.last_activity = time.time()
            
            if session.connection_type == "ssh":
                success, output = await self.ssh_manager.execute_command(session_id, command)
            elif session.connection_type == "telnet":
                success, output = await self.telnet_manager.execute_command(session_id, command)
            else:
                return CommandResponse(
                    session_id=session_id,
                    output=f"错误: 不支持的连接类型 {session.connection_type}",
                    is_error=True
                )
            
            if not success:
                # 如果是会话失效或连接中断错误，设置会话为非活跃
                if "会话" in output and ("失效" in output or "不存在" in output or "已过期" in output):
                    session.is_active = False
                    
                return CommandResponse(
                    session_id=session_id,
                    output=output,
                    is_error=True
                )
            
            # 命令执行成功，更新会话活跃状态
            session.is_active = True
            return CommandResponse(
                session_id=session_id,
                output=output,
                is_error=False
            )
            
        except Exception as e:
            logger.error(f"执行命令时出错: {str(e)}")
            # 可能是会话或连接问题，标记为非活跃
            session.is_active = False
            
            return CommandResponse(
                session_id=session_id,
                output=f"执行命令时出错: {str(e)}",
                is_error=True
            )
    
    async def disconnect(self, session_id: str) -> Tuple[bool, str]:
        """断开终端连接"""
        if session_id not in self.sessions:
            return False, "错误: 会话不存在或已过期"
        
        session = self.sessions[session_id]
        
        try:
            if session.connection_type == "ssh":
                success, message = await self.ssh_manager.disconnect(session_id)
            elif session.connection_type == "telnet":
                success, message = await self.telnet_manager.disconnect(session_id)
            else:
                return False, f"错误: 不支持的连接类型 {session.connection_type}"
            
            # 无论成功与否，都移除会话
            async with self.lock:
                if session_id in self.sessions:
                    del self.sessions[session_id]
            
            return success, message
            
        except Exception as e:
            logger.error(f"断开连接时出错: {str(e)}")
            
            # 尝试强制移除会话
            async with self.lock:
                if session_id in self.sessions:
                    del self.sessions[session_id]
                    
            return False, f"断开连接时出错: {str(e)}"
    
    async def get_all_sessions(self) -> List[SessionInfo]:
        """获取所有活跃会话"""
        return list(self.sessions.values())
    
    async def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """获取指定会话信息"""
        return self.sessions.get(session_id)
    
    async def cleanup_idle_sessions(self, idle_timeout: int = 600) -> int:
        """清理闲置的会话"""
        current_time = time.time()
        sessions_to_cleanup = []
        
        # 找出闲置的会话
        for session_id, session in self.sessions.items():
            if (current_time - session.last_activity) > idle_timeout:
                sessions_to_cleanup.append(session_id)
        
        # 断开这些会话
        cleaned_count = 0
        for session_id in sessions_to_cleanup:
            success, _ = await self.disconnect(session_id)
            if success:
                cleaned_count += 1
        
        # 同时让SSH和Telnet管理器进行它们自己的清理
        try:
            ssh_cleaned = await self.ssh_manager.cleanup_idle_sessions(idle_timeout)
            cleaned_count += ssh_cleaned
        except Exception as e:
            logger.error(f"SSH会话清理出错: {str(e)}")
            
        return cleaned_count 