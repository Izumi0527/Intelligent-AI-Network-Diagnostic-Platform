"""
华为设备专用Telnet连接实现
针对华为设备的特殊处理逻辑
"""

import telnetlib
import socket
import time
import concurrent.futures
from typing import Dict, Any, Optional, Tuple

from app.core.network.telnet.connection import TelnetConnection
from app.core.network.base import DeviceType, ConnectionStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)


class HuaweiTelnetConnection(TelnetConnection):
    """华为设备专用Telnet连接"""
    
    def __init__(self, host: str, port: int, username: str, password: str):
        super().__init__(host, port, username, password)
        self.device_type = DeviceType.HUAWEI
        self.enable_password = None
        self.huawei_more_pattern = r'---- More ----'
    
    def _connect_sync(self, timeout: int) -> Tuple[bool, str]:
        """华为设备专用连接实现"""
        try:
            # 检查主机可达性
            if not self._check_host_reachable(timeout):
                return False, f"主机 {self.host}:{self.port} 不可达"
            
            # 使用华为设备专用的连接方法
            return self._huawei_direct_connect(timeout)
            
        except Exception as e:
            return False, f"华为设备连接失败: {str(e)}"
    
    def _huawei_direct_connect(self, timeout: int) -> Tuple[bool, str]:
        """华为设备直接连接方法"""
        try:
            # 创建原始socket连接
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((self.host, self.port))
            
            # 创建Telnet客户端
            self.client = telnetlib.Telnet()
            self.client.sock = sock
            
            # 华为设备特有的初始化序列
            initial_data = self.client.read_until(b"Username:", 10)
            if b"Username:" not in initial_data:
                # 尝试其他提示符
                self.client.write(b"\r\n")
                initial_data = self.client.read_until(b":", 10)
            
            if b"Username:" in initial_data or b"Login:" in initial_data:
                # 发送用户名
                self.client.write(self.username.encode('ascii') + b"\r\n")
                
                # 等待密码提示
                password_prompt = self.client.read_until(b"Password:", 10)
                if b"Password:" in password_prompt:
                    # 发送密码
                    self.client.write(self.password.encode('ascii') + b"\r\n")
                    
                    # 等待登录成功
                    welcome_response = self.client.read_until(b">", 10)
                    
                    if b">" in welcome_response or b"#" in welcome_response:
                        logger.info("华为设备登录成功")
                        
                        # 进入系统视图（如果需要）
                        self._enter_system_view()
                        
                        return True, "华为设备连接成功"
                    else:
                        return False, "登录失败，用户名或密码错误"
            
            return False, "未检测到正确的登录提示符"
            
        except socket.timeout:
            return False, "华为设备连接超时"
        except ConnectionRefusedError:
            return False, "华为设备拒绝连接"
        except Exception as e:
            return False, f"华为设备连接异常: {str(e)}"
    
    def _enter_system_view(self):
        """进入华为设备系统视图"""
        try:
            # 发送system-view命令
            self.client.write(b"system-view\r\n")
            response = self.client.read_until(b"]", 5)
            
            if b"]" in response:
                logger.debug("已进入华为设备系统视图")
            
        except Exception as e:
            logger.warning(f"进入系统视图失败: {str(e)}")
    
    def _execute_command_sync(self, command: str) -> Tuple[bool, str]:
        """华为设备专用命令执行"""
        try:
            # 清除输入缓冲区
            try:
                self.client.read_very_eager()
            except:
                pass
            
            # 发送命令
            self.client.write(command.encode('utf-8') + b"\r\n")
            
            # 华为设备响应处理
            full_response = ""
            max_iterations = 50
            iteration = 0
            
            while iteration < max_iterations:
                try:
                    # 读取响应
                    response = self.client.read_until(b"\r\n", 2)
                    if not response:
                        break
                    
                    response_str = response.decode('utf-8', errors='ignore')
                    full_response += response_str
                    
                    # 检查是否遇到分页提示
                    if "---- More ----" in response_str:
                        # 发送空格继续
                        self.client.write(b" ")
                        continue
                    
                    # 检查是否到达命令结束
                    if self._is_command_complete(response_str, command):
                        break
                    
                    iteration += 1
                    
                except socket.timeout:
                    break
            
            # 清理响应内容
            cleaned_response = self._clean_huawei_response(full_response, command)
            return True, cleaned_response
            
        except Exception as e:
            return False, f"华为命令执行失败: {str(e)}"
    
    def _is_command_complete(self, response: str, command: str) -> bool:
        """判断华为设备命令是否执行完成"""
        # 华为设备常见提示符
        huawei_prompts = [">", "]", "#"]
        
        lines = response.strip().split('\n')
        if lines:
            last_line = lines[-1].strip()
            return any(last_line.endswith(prompt) for prompt in huawei_prompts)
        
        return False
    
    def _clean_huawei_response(self, response: str, command: str) -> str:
        """清理华为设备响应"""
        if not response:
            return ""
        
        # 移除命令回显
        lines = response.split('\n')
        cleaned_lines = []
        
        skip_first_command = True
        for line in lines:
            line = line.strip()
            
            # 跳过命令回显行
            if skip_first_command and line == command.strip():
                skip_first_command = False
                continue
            
            # 跳过分页提示
            if "---- More ----" in line:
                continue
            
            # 跳过空行和提示符行
            if line and not any(line.endswith(prompt) for prompt in [">", "]", "#"]):
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    async def get_device_info(self) -> Dict[str, Any]:
        """获取华为设备详细信息"""
        try:
            # 获取设备版本信息
            success, version_info = await self.execute_command("display version")
            device_info = {"device_type": "huawei"}
            
            if success and version_info:
                # 解析版本信息
                lines = version_info.split('\n')
                for line in lines:
                    line = line.strip()
                    if "VRP" in line and "Version" in line:
                        device_info["version"] = line
                    elif "HUAWEI" in line and any(model in line for model in ["S", "CE", "AR"]):
                        device_info["model"] = line
            
            # 获取系统名称
            success, sysname = await self.execute_command("display current-configuration | include sysname")
            if success and sysname:
                lines = sysname.split('\n')
                for line in lines:
                    if "sysname" in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            device_info["hostname"] = parts[1]
                        break
            
            return device_info
            
        except Exception as e:
            logger.error(f"获取华为设备信息失败: {str(e)}")
            return {"device_type": "huawei", "error": str(e)}