import asyncio
import logging
import time
from typing import Dict, Any, Optional, Tuple
import uuid
import re

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
                
            # 创建交互式会话通道（而不是每次命令都创建新通道）
            shell_channel = await asyncio.to_thread(client.invoke_shell)
            
            # 等待初始提示
            await asyncio.sleep(1)
            initial_output = await asyncio.to_thread(shell_channel.recv, 4096)
            logger.debug(f"SSH初始输出: {initial_output.decode('utf-8', 'replace')}")
            
            # 获取更详细的设备信息
            try:
                # 尝试发送简单命令来获取更多设备信息
                await asyncio.to_thread(shell_channel.send, "display version\n")
                await asyncio.sleep(2)
                version_output = await asyncio.to_thread(shell_channel.recv, 4096)
                device_info_match = re.search(r'(Software|Version|System).*?(\d+\.\d+\.\d+)', 
                                              version_output.decode('utf-8', 'replace'))
                if device_info_match:
                    device_info = device_info_match.group(0)
            except Exception as e:
                logger.debug(f"获取详细设备信息失败: {str(e)}")
            
            # 加密存储密码
            encrypted_password = encrypt_device_password(password)
            
            # 记录连接
            self.clients[session_id] = {
                "client": client,
                "shell": shell_channel,
                "host": host,
                "port": port,
                "username": username,
                "password": encrypted_password,
                "device_info": device_info,
                "last_command": "",
                "created_at": asyncio.get_event_loop().time(),
                "last_active": time.time()
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
        
        session_data = self.clients[session_id]
        shell = session_data.get("shell")
        
        if not shell or not shell.active:
            # 如果会话已经失效，尝试重新连接
            try:
                logger.warning(f"SSH会话已失效，尝试重新连接: {session_data['host']}:{session_data['port']}")
                password = decrypt_device_password(session_data["password"])
                success, msg, new_session_id = await self.connect(
                    session_data["host"], 
                    session_data["port"], 
                    session_data["username"], 
                    password,
                    timeout=10
                )
                
                if success and new_session_id:
                    # 更新会话信息
                    if session_id in self.clients:
                        del self.clients[session_id]
                    return await self.execute_command(new_session_id, command)
                else:
                    return False, f"会话已失效且无法重新连接: {msg}"
            except Exception as e:
                logger.error(f"会话恢复失败: {str(e)}")
                return False, f"会话已失效且恢复失败: {str(e)}"
        
        try:
            # 记录最后一条命令和活动时间
            session_data["last_command"] = command
            session_data["last_active"] = time.time()
            
            # 发送命令
            await asyncio.to_thread(shell.send, command + "\n")
            
            # 等待命令执行完成（需要根据设备响应速度调整）
            await asyncio.sleep(2)
            
            # 读取输出
            output = ""
            await asyncio.sleep(0.5)  # 给设备一点时间来产生输出
            
            # 检查是否有可用数据
            while await asyncio.to_thread(lambda: shell.recv_ready()):
                chunk = await asyncio.to_thread(shell.recv, 4096)
                if not chunk:
                    break
                output += chunk.decode("utf-8", errors="replace")
                await asyncio.sleep(0.1)  # 短暂等待更多数据
            
            # 处理输出 - 移除命令回显和终端提示符
            processed_output = self._process_command_output(command, output)
            
            # 规范化输出格式
            normalized_output = self._normalize_output(processed_output)
            
            return True, normalized_output
            
        except Exception as e:
            error_msg = f"执行SSH命令时出错: {str(e)}"
            logger.error(error_msg)
            # 标记会话可能已失效
            if "session" in str(e).lower() and "active" in str(e).lower():
                if shell:
                    shell.active = False
            return False, error_msg
    
    def _process_command_output(self, command: str, output: str) -> str:
        """处理命令输出，移除回显和提示符"""
        if not output:
            return ""
            
        # 按行分割输出
        lines = output.split("\n")
        processed_lines = []
        
        # 移除第一行（通常是命令回显）
        command_found = False
        for i, line in enumerate(lines):
            # 跳过空行
            if not line.strip():
                continue
                
            # 如果找到命令回显行，跳过它
            if not command_found and command.strip() in line:
                command_found = True
                continue
                
            # 跳过可能的提示符行
            if re.match(r'^[\w\-\.]+[>#\$]\s*$', line.strip()):
                continue
                
            processed_lines.append(line)
        
        return "\n".join(processed_lines)
    
    def _normalize_output(self, text: str) -> str:
        """规范化命令输出，处理格式问题"""
        if not text:
            return ""
            
        lines = text.split("\n")
        processed_lines = []
        
        for line in lines:
            # 处理过多的前导空格（通常表示右对齐）
            if line.strip():
                # 统计前导空格数量
                leading_spaces = len(line) - len(line.lstrip())
                # 如果有过多前导空格（可能是右对齐文本）
                if leading_spaces > 8:
                    # 保留最多4个空格作为缩进
                    indent = " " * min(4, leading_spaces // 2) 
                    line = indent + line.strip()
                
                processed_lines.append(line)
            else:
                # 保留空行以维持段落分隔
                processed_lines.append("")
                
        return "\n".join(processed_lines)
    
    async def disconnect(self, session_id: str) -> Tuple[bool, str]:
        """
        关闭SSH连接
        
        Returns:
            Tuple[bool, str]: (成功标志, 消息)
        """
        if session_id not in self.clients:
            return False, "错误: SSH会话不存在或已过期"
        
        try:
            session_data = self.clients[session_id]
            client = session_data.get("client")
            shell = session_data.get("shell")
            host = session_data.get("host", "unknown")
            
            # 尝试优雅退出
            if shell and shell.active:
                try:
                    await asyncio.to_thread(shell.send, "exit\n")
                    await asyncio.sleep(0.5)
                except:
                    pass
            
            # 关闭会话和连接
            if shell:
                try:
                    await asyncio.to_thread(shell.close)
                except:
                    pass
                    
            if client:
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
    
    async def check_session_active(self, session_id: str) -> bool:
        """检查会话是否仍然活跃"""
        if session_id not in self.clients:
            return False
            
        session_data = self.clients[session_id]
        shell = session_data.get("shell")
        
        if not shell:
            return False
            
        # 检查通道是否仍然打开
        try:
            is_active = shell.active and not shell.closed
            if not is_active:
                return False
                
            # 可选：发送保活信息
            await asyncio.to_thread(shell.send, "\n")
            await asyncio.sleep(0.1)
            
            # 清除任何响应
            if await asyncio.to_thread(lambda: shell.recv_ready()):
                await asyncio.to_thread(shell.recv, 1024)
                
            return True
        except Exception as e:
            logger.warning(f"检查会话活跃状态时出错: {str(e)}")
            return False
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息（敏感信息已移除）"""
        if session_id not in self.clients:
            return None
            
        info = self.clients[session_id].copy()
        
        # 移除敏感信息
        for key in ["client", "shell", "password"]:
            if key in info:
                del info[key]
            
        return info
        
    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """获取所有会话信息（敏感信息已移除）"""
        sessions = {}
        
        for session_id, info in self.clients.items():
            session_info = info.copy()
            
            # 移除敏感信息
            for key in ["client", "shell", "password"]:
                if key in session_info:
                    del session_info[key]
                
            sessions[session_id] = session_info
            
        return sessions
        
    async def cleanup_idle_sessions(self, idle_timeout: int = 600) -> int:
        """清理闲置的会话，返回清理的会话数"""
        current_time = time.time()
        sessions_to_cleanup = []
        
        for session_id, session_data in self.clients.items():
            last_active = session_data.get("last_active", 0)
            if (current_time - last_active) > idle_timeout:
                sessions_to_cleanup.append(session_id)
                
        cleanup_count = 0
        for session_id in sessions_to_cleanup:
            success, _ = await self.disconnect(session_id)
            if success:
                cleanup_count += 1
                
        return cleanup_count 