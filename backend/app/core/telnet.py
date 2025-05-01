import asyncio
import logging
import telnetlib
from typing import Dict, Any, Optional, Tuple
import uuid
import re
import time

from app.utils.logger import get_logger
from app.utils.security import encrypt_device_password, decrypt_device_password

logger = get_logger(__name__)

class TelnetManager:
    """Telnet连接管理器"""
    
    def __init__(self):
        """初始化Telnet管理器"""
        self.clients: Dict[str, Dict[str, Any]] = {}
        
    async def connect(
        self, host: str, port: int, username: str, password: str, timeout: int = 10
    ) -> Tuple[bool, str, Optional[str]]:
        """
        建立Telnet连接
        
        Returns:
            Tuple[bool, str, Optional[str]]: (成功标志, 消息, 会话ID或None)
        """
        session_id = f"telnet-{uuid.uuid4().hex[:8]}"
        
        try:
            # 创建Telnet客户端并连接
            client = await asyncio.to_thread(
                self._connect_telnet, host, port, username, password, timeout
            )
            
            if not client:
                return False, f"Telnet连接失败: {host}:{port}", None
            
            # 加密存储密码
            encrypted_password = encrypt_device_password(password)
            
            # 尝试获取设备信息
            device_info = ""
            try:
                device_info = await self._get_device_info(client)
            except Exception as e:
                logger.warning(f"无法获取设备信息: {str(e)}")
                device_info = "Unknown device"
            
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
            
            logger.info(f"Telnet连接成功: {host}:{port} 用户: {username}")
            return True, f"Telnet连接成功: {host}", session_id
            
        except ConnectionRefusedError:
            error_msg = f"Telnet连接被拒绝: {host}:{port}"
            logger.error(error_msg)
            return False, error_msg, None
            
        except TimeoutError:
            error_msg = f"Telnet连接超时: {host}:{port}"
            logger.error(error_msg)
            return False, error_msg, None
            
        except Exception as e:
            error_msg = f"建立Telnet连接时发生未知错误: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    def _connect_telnet(self, host, port, username, password, timeout):
        """建立Telnet连接（同步方法）"""
        try:
            # 初始连接
            client = telnetlib.Telnet(host, port, timeout)
            
            # 等待用户名提示符，可能需要调整提示符的匹配方式以适应不同设备
            client.read_until(b"login: ", timeout)
            client.write(username.encode('ascii') + b"\n")
            
            # 等待密码提示符
            client.read_until(b"Password: ", timeout)
            client.write(password.encode('ascii') + b"\n")
            
            # 等待登录完成（命令提示符）
            # 这里可能需要根据不同设备类型调整匹配的命令提示符
            response = client.read_until(b"#", timeout)
            
            # 检查登录是否成功
            if b"Login incorrect" in response or b"Authentication failed" in response:
                client.close()
                raise Exception("认证失败")
            
            return client
        except Exception as e:
            logger.error(f"Telnet连接过程中出错: {str(e)}")
            return None
    
    async def _get_device_info(self, client) -> str:
        """获取设备信息（通过发送常见命令）"""
        try:
            # 尝试不同的命令来获取设备信息
            commands = ["show version", "version", "display version", "system-view"]
            
            for cmd in commands:
                client.write(cmd.encode('ascii') + b"\n")
                time.sleep(1)
                response = client.read_very_eager().decode('ascii', errors='replace')
                
                # 检查是否有有用的设备信息
                version_match = re.search(r'(Software|Version|System).*?(\d+\.\d+\.\d+)', response)
                if version_match:
                    return version_match.group(0)
                
                model_match = re.search(r'(Model|Platform|Hardware).*?(\w+-\w+|\w+\d+)', response)
                if model_match:
                    return model_match.group(0)
                
                # 如果有任何输出，就返回前几行
                if response.strip():
                    return response.strip().split('\n')[0]
            
            return "Unknown"
        except Exception as e:
            logger.error(f"获取设备信息失败: {str(e)}")
            return "Unknown device"
    
    async def execute_command(self, session_id: str, command: str) -> Tuple[bool, str]:
        """
        在Telnet连接上执行命令
        
        Returns:
            Tuple[bool, str]: (成功标志, 输出或错误消息)
        """
        if session_id not in self.clients:
            return False, "错误: Telnet会话不存在或已过期"
        
        try:
            client = self.clients[session_id]["client"]
            
            # 记录最后一条命令
            self.clients[session_id]["last_command"] = command
            
            # 使用线程执行阻塞的Telnet命令
            output = await asyncio.to_thread(
                self._execute_telnet_command, client, command
            )
            
            return True, output
            
        except Exception as e:
            error_msg = f"执行Telnet命令时出错: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _execute_telnet_command(self, client, command) -> str:
        """执行Telnet命令（同步方法）"""
        try:
            # 清空缓冲区
            client.read_very_eager()
            
            # 发送命令
            client.write(command.encode('ascii') + b"\n")
            
            # 等待命令执行完成（这需要调整以适应不同设备）
            time.sleep(1)
            
            # 读取响应
            response = client.read_very_eager().decode('ascii', errors='replace')
            
            # 处理响应
            lines = response.split('\n')
            if len(lines) > 1:
                # 移除第一行（回显的命令）
                processed_response = '\n'.join(lines[1:])
            else:
                processed_response = response
                
            return processed_response
            
        except Exception as e:
            raise Exception(f"执行Telnet命令失败: {str(e)}")
    
    async def disconnect(self, session_id: str) -> Tuple[bool, str]:
        """
        关闭Telnet连接
        
        Returns:
            Tuple[bool, str]: (成功标志, 消息)
        """
        if session_id not in self.clients:
            return False, "错误: Telnet会话不存在或已过期"
        
        try:
            client = self.clients[session_id]["client"]
            host = self.clients[session_id]["host"]
            
            # 尝试先发送退出命令
            try:
                client.write(b"exit\n")
                time.sleep(0.5)
            except:
                pass
            
            # 关闭连接
            await asyncio.to_thread(client.close)
            
            # 移除会话
            del self.clients[session_id]
            
            logger.info(f"已关闭Telnet连接: {host}")
            return True, f"已成功断开Telnet连接: {host}"
            
        except Exception as e:
            error_msg = f"关闭Telnet连接时出错: {str(e)}"
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