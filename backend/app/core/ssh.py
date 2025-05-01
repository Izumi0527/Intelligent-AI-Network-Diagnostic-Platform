import asyncio
import logging
from typing import Dict, Any, Optional, Tuple
import uuid

import paramiko
from paramiko.ssh_exception import SSHException, AuthenticationException, NoValidConnectionsError

from app.utils.logger import get_logger
from app.utils.security import encrypt_device_password, decrypt_device_password

logger = get_logger(__name__)

class SSHManager:
    """SSH连接管理器"""
    
    def __init__(self):
        """初始化SSH管理器"""
        self.clients: Dict[str, Dict[str, Any]] = {}
        
    async def connect(
        self, host: str, port: int, username: str, password: str, timeout: int = 10
    ) -> Tuple[bool, str, Optional[str]]:
        """
        建立SSH连接
        
        Returns:
            Tuple[bool, str, Optional[str]]: (成功标志, 消息, 会话ID或None)
        """
        session_id = f"ssh-{uuid.uuid4().hex[:8]}"
        
        try:
            # 创建SSH客户端
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # 使用线程运行阻塞的SSH连接
            await asyncio.to_thread(
                client.connect,
                hostname=host,
                port=port,
                username=username,
                password=password,
                timeout=timeout,
                look_for_keys=False,
                allow_agent=False
            )
            
            # 获取设备信息
            transport = client.get_transport()
            if transport:
                device_info = f"{transport.remote_version}"
            else:
                device_info = "Unknown device"
            
            # 加密存储密码
            encrypted_password = encrypt_device_password(password)
            
            # 记录连接
            self.clients[session_id] = {
                "client": client,
                "host": host,
                "port": port,
                "username": username,
                "password": encrypted_password,
                "device_info": device_info,
                "last_command": "",
                "created_at": asyncio.get_event_loop().time()
            }
            
            logger.info(f"SSH连接成功: {host}:{port} 用户: {username}")
            return True, f"SSH连接成功: {host}", session_id
            
        except AuthenticationException:
            error_msg = f"SSH认证失败: {host} 用户: {username}"
            logger.error(error_msg)
            return False, error_msg, None
            
        except (NoValidConnectionsError, TimeoutError):
            error_msg = f"SSH连接超时: {host}:{port}"
            logger.error(error_msg)
            return False, error_msg, None
            
        except SSHException as e:
            error_msg = f"SSH连接错误: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
            
        except Exception as e:
            error_msg = f"建立SSH连接时发生未知错误: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    async def execute_command(self, session_id: str, command: str) -> Tuple[bool, str]:
        """
        在SSH连接上执行命令
        
        Returns:
            Tuple[bool, str]: (成功标志, 输出或错误消息)
        """
        if session_id not in self.clients:
            return False, "错误: SSH会话不存在或已过期"
        
        try:
            client = self.clients[session_id]["client"]
            
            # 记录最后一条命令
            self.clients[session_id]["last_command"] = command
            
            # 使用线程运行阻塞的SSH命令
            _, stdout, stderr = await asyncio.to_thread(
                client.exec_command, command, timeout=30
            )
            
            # 获取输出
            output = await asyncio.to_thread(stdout.read)
            error = await asyncio.to_thread(stderr.read)
            
            if error:
                error_text = error.decode("utf-8", errors="replace")
                logger.warning(f"SSH命令执行警告: {error_text}")
                return True, output.decode("utf-8", errors="replace") + "\n" + error_text
            
            return True, output.decode("utf-8", errors="replace")
            
        except Exception as e:
            error_msg = f"执行SSH命令时出错: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    async def disconnect(self, session_id: str) -> Tuple[bool, str]:
        """
        关闭SSH连接
        
        Returns:
            Tuple[bool, str]: (成功标志, 消息)
        """
        if session_id not in self.clients:
            return False, "错误: SSH会话不存在或已过期"
        
        try:
            client = self.clients[session_id]["client"]
            host = self.clients[session_id]["host"]
            
            # 关闭连接
            await asyncio.to_thread(client.close)
            
            # 移除会话
            del self.clients[session_id]
            
            logger.info(f"已关闭SSH连接: {host}")
            return True, f"已成功断开SSH连接: {host}"
            
        except Exception as e:
            error_msg = f"关闭SSH连接时出错: {str(e)}"
            logger.error(error_msg)
            
            # 尝试强制移除会话
            if session_id in self.clients:
                del self.clients[session_id]
                
            return False, error_msg
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息（敏感信息已移除）"""
        if session_id not in self.clients:
            return None
            
        info = self.clients[session_id].copy()
        
        # 移除敏感信息
        if "client" in info:
            del info["client"]
        if "password" in info:
            del info["password"]
            
        return info
        
    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """获取所有会话信息（敏感信息已移除）"""
        sessions = {}
        
        for session_id, info in self.clients.items():
            session_info = info.copy()
            
            # 移除敏感信息
            if "client" in session_info:
                del session_info["client"]
            if "password" in session_info:
                del session_info["password"]
                
            sessions[session_id] = session_info
            
        return sessions 