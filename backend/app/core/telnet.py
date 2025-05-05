import asyncio
import logging
import telnetlib
from typing import Dict, Any, Optional, Tuple, List
import uuid
import re
import time
import socket
import threading
import concurrent.futures
import select

from app.utils.logger import get_logger
from app.utils.security import encrypt_device_password, decrypt_device_password

logger = get_logger(__name__)

# 定义Telnet控制字符
IAC = bytes([255])  # Interpret As Command
DONT = bytes([254])
DO = bytes([253])
WONT = bytes([252])
WILL = bytes([251])
SB = bytes([250])  # Subnegotiation Begin
SE = bytes([240])  # Subnegotiation End

# Telnet选项
OPT_ECHO = bytes([1])
OPT_SGA = bytes([3])  # Suppress Go Ahead
OPT_TTYPE = bytes([24])  # Terminal Type
OPT_NAWS = bytes([31])  # Window Size
OPT_TSPEED = bytes([32])  # Terminal Speed
OPT_LFLOW = bytes([33])  # Remote Flow Control
OPT_LINEMODE = bytes([34])  # Linemode
OPT_NEW_ENVIRON = bytes([39])  # New Environment Option

# 设备类型常量
DEVICE_TYPE_UNKNOWN = "unknown"
DEVICE_TYPE_HUAWEI = "huawei"
DEVICE_TYPE_CISCO = "cisco"
DEVICE_TYPE_JUNIPER = "juniper"
DEVICE_TYPE_H3C = "h3c"

class TelnetManager:
    """Telnet连接管理器"""
    
    def __init__(self):
        """初始化Telnet管理器"""
        self.clients: Dict[str, Dict[str, Any]] = {}
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        
    async def connect(
        self, host: str, port: int, username: str, password: str, timeout: int = 120
    ) -> Tuple[bool, str, Optional[str]]:
        """
        建立Telnet连接
        
        Args:
            host: 主机地址
            port: 端口号
            username: 用户名
            password: 密码
            timeout: 超时时间（秒），默认120秒
            
        Returns:
            Tuple[bool, str, Optional[str]]: (成功标志, 消息, 会话ID或None)
        """
        session_id = f"telnet-{uuid.uuid4().hex[:8]}"
        
        # 先进行快速的网络可达性检测
        if not await self._check_host_reachable(host, port, timeout=5):
            error_msg = f"Telnet目标不可达: {host}:{port}"
            logger.error(error_msg)
            return False, error_msg, None
        
        try:
            logger.info(f"正在尝试连接到Telnet设备: {host}:{port}")
            
            # 采用分阶段连接策略，先尝试快速方法
            # 阶段1: 并行尝试所有快速连接方法 (10秒内)
            try:
                fast_connect_future = asyncio.gather(
                    self._connect_huawei_direct(host, port, username, password, timeout),
                    self._connect_direct_tcp(host, port, username, password, timeout),
                    return_exceptions=True
                )
                
                fast_result = None
                device_type = DEVICE_TYPE_UNKNOWN
                
                # 等待快速连接方法
                for i, future_result in enumerate(await asyncio.wait_for(fast_connect_future, timeout=10)):
                    if not isinstance(future_result, Exception) and future_result and future_result[0]:
                        fast_result = future_result
                        # 如果第一个方法成功，说明是华为设备
                        if i == 0:
                            device_type = DEVICE_TYPE_HUAWEI
                        logger.info(f"快速连接成功，使用方法 {i+1}")
                        break
                
                if fast_result:
                    result = fast_result
                else:
                    result = None
            except (asyncio.TimeoutError, Exception):
                logger.debug("快速连接方法超时或出错")
                result = None
            
            # 如果快速方法失败，尝试其他方法
            if not result:
                # 阶段2: 并行尝试其他连接方法，设置较短超时
                try:
                    connect_future = asyncio.gather(
                        self._connect_fast_method(host, port, username, password, timeout),
                        self._connect_telnet_optimized(host, port, username, password, timeout),
                        return_exceptions=True
                    )
                    
                    # 设置较短超时，避免等待太久
                    for i, future_result in enumerate(await asyncio.wait_for(connect_future, timeout=30)):
                        if not isinstance(future_result, Exception) and future_result and future_result[0]:
                            # 找到成功的连接
                            result = future_result
                            logger.info(f"常规连接成功，使用方法 {i+1}")
                            break
                except asyncio.TimeoutError:
                    logger.warning("常规连接方法超时，尝试单独的长超时连接方法")
                    result = None
                
                # 阶段3: 如果前两阶段失败，使用单一方法尝试长连接（用于慢速设备）
                if not result:
                    try:
                        # 最后的尝试，使用较长超时
                        result = await asyncio.wait_for(
                            self._connect_telnet_optimized(host, port, username, password, timeout),
                            timeout=60
                        )
                    except asyncio.TimeoutError:
                        logger.error(f"所有连接方法均超时: {host}:{port}")
                        return False, f"Telnet连接超时: {host}:{port}", None
            
            # 如果全部失败，返回错误
            if not result or not result[0]:
                return False, f"Telnet连接失败: {host}:{port}", None
            
            success, client, device_info = result
            
            # 如果前面没有确定设备类型，现在尝试检测
            if device_type == DEVICE_TYPE_UNKNOWN:
                device_type = self._detect_device_type(device_info)
            
            # 加密存储密码
            encrypted_password = encrypt_device_password(password)
            
            # 记录连接
            self.clients[session_id] = {
                "client": client,
                "host": host,
                "port": port,
                "username": username,
                "password": encrypted_password,
                "device_info": device_info if device_info else "Unknown device",
                "device_type": device_type,
                "last_command": "",
                "created_at": asyncio.get_event_loop().time(),
                "last_active": time.time()
            }
            
            logger.info(f"Telnet连接成功: {host}:{port} 用户: {username}, 设备类型: {device_type}")
            return True, f"Telnet连接成功: {host}", session_id
            
        except asyncio.TimeoutError:
            error_msg = f"Telnet连接总超时: {host}:{port} (超过{timeout}秒)"
            logger.error(error_msg)
            return False, error_msg, None
            
        except ConnectionRefusedError:
            error_msg = f"Telnet连接被拒绝: {host}:{port}"
            logger.error(error_msg)
            return False, error_msg, None
            
        except Exception as e:
            error_msg = f"建立Telnet连接时发生未知错误: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    def _detect_device_type(self, device_info: str) -> str:
        """根据设备信息识别设备类型"""
        device_info_lower = device_info.lower()
        
        # 华为设备特征
        if any(kw in device_info_lower for kw in ["huawei", "华为", "vrp", "vrpv", "s5700", "s7700", "ne", "ce"]):
            return DEVICE_TYPE_HUAWEI
            
        # 思科设备特征
        elif any(kw in device_info_lower for kw in ["cisco", "ios"]):
            return DEVICE_TYPE_CISCO
            
        # 瞻博网络设备特征
        elif any(kw in device_info_lower for kw in ["juniper", "junos"]):
            return DEVICE_TYPE_JUNIPER
            
        # H3C设备特征
        elif any(kw in device_info_lower for kw in ["h3c", "comware"]):
            return DEVICE_TYPE_H3C
            
        # 未识别设备
        return DEVICE_TYPE_UNKNOWN

    async def _connect_huawei_direct(self, host, port, username, password, timeout):
        """华为设备专用快速连接方法"""
        try:
            # 定义要在线程中运行的函数
            def huawei_connect():
                try:
                    # 创建socket并设置更短的超时时间
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(10)  # 华为设备较短的超时
                    
                    # 连接到服务器
                    sock.connect((host, port))
                    sock.setblocking(False)
                    
                    # 预计的华为设备提示符和特征
                    login_patterns = [b"login:", b"Username:", b"username:", b"user:"]
                    password_patterns = [b"Password:", b"password:"]
                    success_patterns = [b">", b"]", b"#"]
                    huawei_prompts = [b"<", b"[", b"{"]  # 华为特有的提示符
                    
                    # 创建telnetlib对象
                    client = telnetlib.Telnet()
                    client.sock = sock
                    
                    # 1. 快速发送回车激活登录提示
                    sock.send(b"\r\n")
                    
                    # 立即发送用户名尝试绕过登录提示
                    time.sleep(0.3)  # 等待华为设备处理
                    sock.send((username + "\r\n").encode('ascii'))
                    
                    # 快速操作: 立即等待密码提示
                    start_time = time.time()
                    buffer = b""
                    password_found = False
                    
                    # 短时间内快速检查密码提示
                    while time.time() - start_time < 3:
                        try:
                            ready_to_read, _, _ = select.select([sock], [], [], 0.3)
                            if ready_to_read:
                                chunk = sock.recv(1024)
                                if not chunk:
                                    break
                                buffer += chunk
                                
                                # 如果发现密码提示，立即处理
                                if any(pattern in buffer for pattern in password_patterns):
                                    password_found = True
                                    break
                        except Exception:
                            time.sleep(0.1)
                    
                    # 2. 立即尝试发送密码，无论是否找到密码提示
                    sock.send((password + "\r\n").encode('ascii'))
                    
                    # 3. 快速等待提示符
                    start_time = time.time()
                    buffer = b""
                    login_success = False
                    
                    # 华为设备通常在发送密码后很快出现提示符
                    while time.time() - start_time < 5:
                        try:
                            ready_to_read, _, _ = select.select([sock], [], [], 0.2)
                            if ready_to_read:
                                chunk = sock.recv(1024)
                                if not chunk:
                                    break
                                buffer += chunk
                                
                                # 检查华为特有的提示符以及常规提示符
                                if any(pattern in buffer for pattern in success_patterns + huawei_prompts):
                                    login_success = True
                                    break
                                    
                                # 检查是否有登录错误信息
                                if (b"failed" in buffer.lower() or b"incorrect" in buffer.lower() or 
                                    b"invalid" in buffer.lower()):
                                    return None, "华为设备认证失败: 用户名或密码不正确"
                        except Exception:
                            time.sleep(0.1)
                    
                    # 如果登录成功，补充发送一条系统命令获取设备信息
                    if login_success:
                        # 发送华为设备专用命令获取设备信息
                        sock.send(b"display version\r\n")
                        time.sleep(1)
                        
                        # 快速读取响应
                        try:
                            response_data = b""
                            for _ in range(3):
                                ready_to_read, _, _ = select.select([sock], [], [], 0.3)
                                if ready_to_read:
                                    chunk = sock.recv(1024)
                                    if not chunk:
                                        break
                                    response_data += chunk
                                else:
                                    break
                        except Exception:
                            pass
                            
                        # 提取设备信息
                        device_info = "Huawei Device"
                        try:
                            decoded_data = response_data.decode('ascii', errors='replace')
                            # 查找版本信息
                            version_match = re.search(r'VRP.+?(\d+\.\d+)', decoded_data)
                            if version_match:
                                device_info = f"Huawei {version_match.group(0)}"
                            else:
                                # 查找产品型号
                                product_match = re.search(r'(Quidway|HUAWEI|S\d+|CE\d+|NE\d+)[^\n\r]+', decoded_data)
                                if product_match:
                                    device_info = f"Huawei {product_match.group(0).strip()}"
                        except Exception:
                            pass
                            
                        return client, device_info
                    
                    return None, "华为设备连接失败 - 未检测到命令提示符"
                    
                except Exception as e:
                    return None, f"华为设备连接过程出错: {str(e)}"
            
            # 在线程池中执行连接函数
            client, error_or_info = await asyncio.get_event_loop().run_in_executor(
                self.executor, huawei_connect
            )
            
            if client:
                logger.info("使用华为设备专用连接方法成功")
                return True, client, error_or_info
            
            logger.debug(f"华为设备专用连接方法失败: {error_or_info}")
            return False, None, None
        except Exception as e:
            logger.debug(f"华为设备专用连接方法异常: {str(e)}")
            return False, None, None
    
    async def _connect_fast_method(self, host, port, username, password, timeout):
        """使用直接socket连接的快速方法"""
        try:
            # 创建一个事件，用于通知连接成功
            connected_event = threading.Event()
            client_container = [None]
            device_info_container = ["Unknown device"]
            error_container = [None]
            
            # 定义要在线程中运行的函数
            def connect_thread():
                try:
                    # 创建socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(30)  # 设置socket级别超时
                    
                    # 连接到服务器
                    sock.connect((host, port))
                    
                    # 设置为非阻塞模式
                    sock.setblocking(False)
                    
                    # 创建telnetlib连接对象
                    client = telnetlib.Telnet()
                    client.sock = sock
                    
                    # 先读取初始欢迎信息
                    initial_output = b""
                    login_found = False
                    start_time = time.time()
                    
                    # 等待登录提示最多15秒
                    while time.time() - start_time < 15:
                        try:
                            # 尝试读取数据
                            ready_to_read, _, _ = select.select([sock], [], [], 0.5)
                            if ready_to_read:
                                chunk = sock.recv(1024)
                                if not chunk:
                                    break
                                initial_output += chunk
                                
                                # 检查是否包含登录提示
                                if b"login:" in initial_output or b"Username:" in initial_output:
                                    login_found = True
                                    break
                        except (socket.timeout, BlockingIOError):
                            time.sleep(0.1)
                        except Exception as e:
                            error_container[0] = str(e)
                            return

                    # 如果没有找到登录提示，发送回车尝试触发
                    if not login_found:
                        try:
                            sock.send(b"\r\n")
                            time.sleep(1)
                            
                            # 再次尝试读取数据
                            try:
                                ready_to_read, _, _ = select.select([sock], [], [], 2)
                                if ready_to_read:
                                    chunk = sock.recv(1024)
                                    initial_output += chunk
                            except:
                                pass
                            
                            # 检查是否包含登录提示
                            if b"login:" in initial_output or b"Username:" in initial_output:
                                login_found = True
                        except:
                            pass
                    
                    # 仍未找到登录提示，使用老方法：直接发送用户名
                    if not login_found and len(initial_output) > 0:
                        try:
                            sock.send((username + "\r\n").encode('ascii'))
                            time.sleep(0.5)
                        except:
                            pass
                    elif login_found:
                        # 发送用户名
                        try:
                            sock.send((username + "\r\n").encode('ascii'))
                            time.sleep(0.5)
                        except Exception as e:
                            error_container[0] = f"发送用户名错误: {str(e)}"
                            return
                    
                    # 等待密码提示最多5秒
                    password_found = False
                    password_output = b""
                    start_time = time.time()
                    
                    while time.time() - start_time < 5:
                        try:
                            ready_to_read, _, _ = select.select([sock], [], [], 0.5)
                            if ready_to_read:
                                chunk = sock.recv(1024)
                                if not chunk:
                                    break
                                password_output += chunk
                                
                                # 检查是否包含密码提示
                                if b"Password:" in password_output or b"password:" in password_output:
                                    password_found = True
                                    break
                        except:
                            time.sleep(0.1)
                    
                    # 如果找到密码提示或不确定，尝试发送密码
                    if password_found or not login_found:
                        try:
                            sock.send((password + "\r\n").encode('ascii'))
                            time.sleep(0.5)
                        except Exception as e:
                            error_container[0] = f"发送密码错误: {str(e)}"
                            return
                    
                    # 等待登录成功最多10秒，检查是否有命令提示符
                    command_output = b""
                    login_success = False
                    start_time = time.time()
                    
                    # 常见的命令提示符
                    prompts = [b"#", b">", b"$", b"%", b"]"]
                    
                    while time.time() - start_time < 10:
                        try:
                            ready_to_read, _, _ = select.select([sock], [], [], 0.5)
                            if ready_to_read:
                                chunk = sock.recv(1024)
                                if not chunk:
                                    break
                                command_output += chunk
                                
                                # 检查是否包含命令提示符
                                if any(prompt in command_output for prompt in prompts):
                                    login_success = True
                                    break
                                
                                # 检查是否包含错误信息
                                if b"incorrect" in command_output.lower() or b"failed" in command_output.lower():
                                    error_container[0] = "认证失败: 用户名或密码不正确"
                                    return
                        except:
                            time.sleep(0.1)
                    
                    # 额外检查，尝试发送回车获取响应
                    if not login_success and len(command_output) > 0:
                        try:
                            sock.send(b"\r\n")
                            time.sleep(1)
                            
                            try:
                                ready_to_read, _, _ = select.select([sock], [], [], 1)
                                if ready_to_read:
                                    chunk = sock.recv(1024)
                                    command_output += chunk
                                    
                                    # 再次检查提示符
                                    if any(prompt in command_output for prompt in prompts):
                                        login_success = True
                            except:
                                pass
                        except:
                            pass
                    
                    # 尝试解码获取设备信息
                    try:
                        decoded_output = command_output.decode('ascii', errors='replace')
                        if login_success:
                            lines = [line for line in decoded_output.split('\n') if line.strip()]
                            if lines:
                                device_info_container[0] = lines[0]
                    except:
                        pass
                    
                    # 如果登录成功，保存客户端
                    if login_success:
                        client_container[0] = client
                        connected_event.set()
                    else:
                        error_container[0] = "未能检测到命令提示符"
                        
                except Exception as e:
                    error_container[0] = str(e)
            
            # 在线程池中执行连接函数
            await asyncio.get_event_loop().run_in_executor(
                self.executor, connect_thread
            )
            
            # 检查是否有错误
            if error_container[0]:
                logger.warning(f"快速连接方法出错: {error_container[0]}")
                return False, None, None
            
            # 检查是否有客户端连接
            if client_container[0]:
                logger.info("使用快速连接方法成功连接")
                return True, client_container[0], device_info_container[0]
            
            return False, None, None
        except Exception as e:
            logger.warning(f"快速连接方法异常: {str(e)}")
            return False, None, None
    
    async def _check_host_reachable(self, host: str, port: int, timeout: float = 5.0) -> bool:
        """快速检查主机是否可达"""
        try:
            # 创建套接字并设置超时
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            # 尝试连接
            result = await asyncio.to_thread(
                lambda: sock.connect_ex((host, port))
            )
            
            sock.close()
            return result == 0
        except Exception as e:
            logger.debug(f"检查主机可达性时出错: {str(e)}")
            return False
    
    async def _connect_telnet_optimized(self, host, port, username, password, timeout):
        """使用优化的Telnet连接方法"""
        try:
            # 定义要在线程中运行的函数
            def telnet_connect():
                try:
                    # 建立连接
                    client = telnetlib.Telnet(host, port, timeout=30)
                    
                    # 一次性设置所有可能的提示符
                    login_prompts = [b"login:", b"Username:", b"user:", b"User:"]
                    password_prompts = [b"Password:", b"password:", b"passwd:"]
                    success_prompts = [b"#", b">", b"$", b"%", b"]", b":", b"<"]
                    
                    # 等待登录提示，缩短超时时间
                    login_output = b""
                    login_found = False
                    
                    # 快速读取初始内容
                    try:
                        login_output = client.read_until(login_prompts[0], 5)
                        if login_prompts[0] in login_output:
                            login_found = True
                    except:
                        pass
                    
                    # 如果第一次读取失败，尝试其他登录提示
                    if not login_found:
                        for prompt in login_prompts[1:]:
                            try:
                                result = client.read_until(prompt, 2)
                                login_output += result
                                if prompt in result:
                                    login_found = True
                                    break
                            except:
                                continue
                    
                    # 如果仍未找到登录提示，读取所有可用数据并检查
                    if not login_found:
                        try:
                            available_data = client.read_very_eager()
                            login_output += available_data
                            
                            if any(prompt in login_output for prompt in login_prompts):
                                login_found = True
                        except:
                            pass
                    
                    # 如果仍未找到登录提示，发送回车尝试触发
                    if not login_found:
                        try:
                            client.write(b"\r\n")
                            time.sleep(0.5)
                            
                            # 读取响应
                            try:
                                result = client.read_very_eager()
                                login_output += result
                                
                                if any(prompt in login_output for prompt in login_prompts):
                                    login_found = True
                            except:
                                pass
                        except:
                            pass
                    
                    # 无论是否找到登录提示，都尝试发送用户名
                    # 有些设备可能不显示登录提示，直接期待输入
                    try:
                        client.write(username.encode('ascii') + b"\r\n")
                    except:
                        return None, "发送用户名失败"
                    
                    # 短暂等待后检查是否有密码提示，缩短超时时间
                    password_found = False
                    password_output = b""
                    
                    # 快速检查密码提示
                    for prompt in password_prompts:
                        try:
                            result = client.read_until(prompt, 3)
                            password_output += result
                            if prompt in result:
                                password_found = True
                                break
                        except:
                            continue
                    
                    # 如果未找到密码提示，检查已有输出
                    if not password_found:
                        try:
                            more_data = client.read_very_eager()
                            password_output += more_data
                            
                            if any(prompt in password_output for prompt in password_prompts):
                                password_found = True
                        except:
                            pass
                    
                    # 无论是否找到密码提示，都尝试发送密码
                    # 原因同上，有些设备可能不显示密码提示
                    try:
                        client.write(password.encode('ascii') + b"\r\n")
                    except:
                        return None, "发送密码失败"
                    
                    # 等待登录成功 - 更短的超时，积极匹配多种提示符
                    login_success = False
                    command_output = b""
                    
                    # 等待成功提示的时间更短
                    for _ in range(3):  # 最多尝试3次
                        try:
                            time.sleep(1)  # 短暂等待
                            data = client.read_very_eager()
                            command_output += data
                            
                            # 检查是否包含错误信息
                            if b"incorrect" in command_output.lower() or b"failed" in command_output.lower():
                                return None, "认证失败: 用户名或密码不正确"
                            
                            # 检查是否已包含成功提示符
                            if any(prompt in command_output for prompt in success_prompts):
                                login_success = True
                                break
                        except:
                            pass
                        
                        # 尝试主动等待各种提示符
                        for prompt in success_prompts:
                            try:
                                response = client.read_until(prompt, 2)
                                command_output += response
                                if prompt in response:
                                    login_success = True
                                    break
                            except:
                                continue
                            
                        if login_success:
                            break
                    
                    # 如果仍未成功，发送一次回车，检查是否有提示符
                    if not login_success:
                        try:
                            client.write(b"\r\n")
                            time.sleep(0.5)
                            response = client.read_very_eager()
                            command_output += response
                            
                            if any(prompt in command_output for prompt in success_prompts):
                                login_success = True
                        except:
                            pass
                    
                    # 提取设备信息
                    device_info = "Unknown device"
                    try:
                        decoded_output = command_output.decode('ascii', errors='replace')
                        lines = [line for line in decoded_output.split('\n') if line.strip()]
                        if lines:
                            device_info = lines[0]
                    except:
                        pass
                    
                    if login_success:
                        return client, device_info
                    
                    # 登录失败，关闭连接
                    try:
                        client.close()
                    except:
                        pass
                    
                    return None, "登录失败 - 未检测到命令提示符"
                except Exception as e:
                    return None, f"Telnet连接过程中出错: {str(e)}"
            
            # 在线程池中执行连接函数
            client, error_or_info = await asyncio.get_event_loop().run_in_executor(
                self.executor, telnet_connect
            )
            
            if client:
                logger.info("使用优化Telnet方法成功连接")
                return True, client, error_or_info
            
            logger.warning(f"优化Telnet方法失败: {error_or_info}")
            return False, None, None
        except Exception as e:
            logger.warning(f"优化Telnet方法异常: {str(e)}")
            return False, None, None
    
    async def _get_device_info(self, client) -> str:
        """获取设备信息（通过发送常见命令）"""
        try:
            # 常见的设备信息命令，按优先级排序
            commands = [
                "show version", 
                "version", 
                "display version", 
                "system-view", 
                "show system", 
                "show info",
                "show running-config | include hostname"
            ]
            
            device_info = "Unknown device"
            
            # 清空缓冲区
            client.read_very_eager()
            
            for cmd in commands:
                try:
                    logger.debug(f"尝试使用命令获取设备信息: {cmd}")
                    client.write(cmd.encode('ascii') + b"\n")
                    # 给设备更多时间来响应
                    await asyncio.sleep(2)
                    response = client.read_very_eager().decode('ascii', errors='replace')
                    
                    # 过滤掉命令回显
                    response_lines = response.split('\n')
                    if len(response_lines) > 1:
                        response_lines = response_lines[1:]
                    filtered_response = '\n'.join(response_lines)
                    
                    # 如果响应非空，开始提取有用信息
                    if filtered_response.strip():
                        # 尝试找出版本信息
                        version_match = re.search(r'(Software|Version|System).*?(\d+\.\d+\.\d+)', filtered_response)
                        if version_match:
                            device_info = version_match.group(0)
                            break
                        
                        # 尝试找出设备型号信息
                        model_match = re.search(r'(Model|Platform|Hardware|Device).*?(\w+-\w+|\w+\d+)', filtered_response)
                        if model_match:
                            device_info = model_match.group(0)
                            break
                        
                        # 尝试找出主机名信息
                        hostname_match = re.search(r'hostname\s+(\S+)', filtered_response, re.IGNORECASE)
                        if hostname_match:
                            device_info = f"Hostname: {hostname_match.group(1)}"
                            break
                        
                        # 如果没有找到特定模式，但有输出，使用前几行作为设备信息
                        info_lines = [line for line in filtered_response.split('\n') if line.strip()]
                        if info_lines:
                            # 提取前三行非空内容作为设备信息
                            device_info = '\n'.join(info_lines[:3])
                            break
                except Exception as e:
                    logger.debug(f"执行命令'{cmd}'失败: {str(e)}")
                    continue
            
            # 清理和格式化设备信息
            device_info = device_info.strip()
            if len(device_info) > 500:  # 限制信息长度
                device_info = device_info[:497] + "..."
                
            return device_info
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
            device_type = self.clients[session_id].get("device_type", DEVICE_TYPE_UNKNOWN)
            
            # 记录最后一条命令
            self.clients[session_id]["last_command"] = command
            self.clients[session_id]["last_active"] = time.time()
            
            # 针对不同设备类型使用优化的执行方法
            if device_type == DEVICE_TYPE_HUAWEI:
                output = await asyncio.to_thread(
                    self._execute_huawei_command, client, command
                )
            else:
                # 使用通用方法
                output = await asyncio.to_thread(
                    self._execute_telnet_command_with_pagination, client, command
                )
            
            return True, output
            
        except Exception as e:
            error_msg = f"执行Telnet命令时出错: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _execute_huawei_command(self, client, command) -> str:
        """针对华为设备优化的命令执行方法"""
        try:
            # 清空缓冲区
            client.read_very_eager()
            
            # 发送命令
            client.write(command.encode('ascii') + b"\n")
            
            # 华为设备通常响应较快，缩短初始等待时间
            time.sleep(0.5)
            
            # 读取初始响应
            response = client.read_very_eager().decode('ascii', errors='replace')
            full_response = response
            
            # 华为设备分页提示符
            more_prompts = ["---- More ----", "--More--"]
            
            # 最大尝试次数
            max_attempts = 50
            attempt = 0
            
            # 处理分页 - 华为设备通常使用空格继续
            while attempt < max_attempts:
                has_more_prompt = False
                for prompt in more_prompts:
                    if prompt in response:
                        has_more_prompt = True
                        break
                
                if has_more_prompt:
                    # 发送空格继续
                    client.write(b" ")
                    # 华为设备分页后响应很快，减少等待时间
                    time.sleep(0.2)
                    
                    # 读取下一页
                    response = client.read_very_eager().decode('ascii', errors='replace')
                    
                    # 从响应中移除分页提示
                    for prompt in more_prompts:
                        response = response.replace(prompt, "")
                        
                    full_response += response
                else:
                    # 检查是否还有更多数据
                    time.sleep(0.1)  # 减少等待时间
                    more_data = client.read_very_eager().decode('ascii', errors='replace')
                    if more_data:
                        full_response += more_data
                        response = more_data
                    else:
                        break
                
                attempt += 1
            
            # 处理响应，移除命令回显和提示符
            lines = full_response.split('\n')
            processed_lines = []
            
            # 华为设备特有提示符模式
            huawei_prompts = [r'<.+>', r'\[.+\]', r'.+>\s*$']
            
            command_found = False
            for i, line in enumerate(lines):
                # 跳过空行
                if not line.strip():
                    continue
                    
                # 跳过命令回显行
                if not command_found and command.strip() in line:
                    command_found = True
                    continue
                    
                # 跳过提示符行
                if (any(re.match(pattern, line.strip()) for pattern in huawei_prompts) or
                    any(prompt in line for prompt in more_prompts)):
                    continue
                    
                # 处理行
                line = self._normalize_line(line)
                if line:
                    processed_lines.append(line)
            
            return '\n'.join(processed_lines)
            
        except Exception as e:
            raise Exception(f"执行华为设备命令失败: {str(e)}")
    
    def _execute_telnet_command_with_pagination(self, client, command) -> str:
        """执行Telnet命令（同步方法），支持处理分页"""
        try:
            # 清空缓冲区
            client.read_very_eager()
            
            # 发送命令
            client.write(command.encode('ascii') + b"\n")
            
            # 减少初始等待时间
            time.sleep(0.5)
            
            # 读取初始响应
            response = client.read_very_eager().decode('ascii', errors='replace')
            full_response = response
            
            # 定义常见分页提示符模式
            more_prompts = ["---- More ----", "--More--", "---- more ----", "--more--", 
                           "按任意键继续", "按空格键继续", "Press any key to continue"]
            
            # 最大尝试次数，防止无限循环
            max_attempts = 50
            attempt = 0
            
            # 减少分页检查间隔时间，加快处理速度
            while attempt < max_attempts:
                has_more_prompt = False
                for prompt in more_prompts:
                    if prompt in response:
                        has_more_prompt = True
                        break
                
                if has_more_prompt:
                    # 发现分页提示，发送空格继续
                    client.write(b" ")
                    time.sleep(0.2)  # 减少等待时间
                    
                    # 读取下一页
                    response = client.read_very_eager().decode('ascii', errors='replace')
                    
                    # 从响应中移除分页提示
                    for prompt in more_prompts:
                        response = response.replace(prompt, "")
                        
                    full_response += response
                else:
                    # 快速检查是否还有更多数据
                    time.sleep(0.1) # 减少等待时间
                    more_data = client.read_very_eager().decode('ascii', errors='replace')
                    if more_data:
                        full_response += more_data
                        response = more_data  # 更新response以便下次检查分页提示
                    else:
                        # 没有更多数据，退出循环
                        break
                
                attempt += 1
            
            # 如果达到最大尝试次数，记录警告
            if attempt >= max_attempts:
                logger.warning(f"Telnet命令输出过长，已达到最大尝试次数({max_attempts})，可能未获取完整输出")
            
            # 使用更高效的一次性处理方式
            processed_lines = []
            
            # 使用正则表达式一次匹配多种提示符格式
            prompt_pattern = re.compile(r'^[\w\-\.]+[>#\$\]\)}\s]*$')
            more_pattern = re.compile('|'.join(more_prompts))
            
            for line in full_response.split('\n'):
                line = line.strip()
                
                # 跳过空行
                if not line:
                    continue
                
                # 跳过命令回显行
                if command.strip() in line and len(processed_lines) == 0:
                    continue
                
                # 跳过提示符行或分页提示
                if prompt_pattern.match(line) or more_pattern.search(line):
                    continue
                
                processed_lines.append(line)
            
            # 移除最后一行如果是提示符
            if processed_lines and prompt_pattern.match(processed_lines[-1]):
                processed_lines.pop()
                
            return '\n'.join(processed_lines)
            
        except Exception as e:
            raise Exception(f"执行Telnet命令失败: {str(e)}")
    
    def _normalize_line(self, line: str) -> str:
        """规范化输出行，调整空格和格式"""
        # 如果行基本上是空的，返回空字符串
        if not line.strip():
            return ""
            
        # 如果行前面有超过8个空格，只保留4个作为缩进（保留基本格式）
        if line.startswith("        "):  # 8个空格
            # 统计前导空格数量
            leading_spaces = len(line) - len(line.lstrip())
            if leading_spaces > 8:
                # 保留最多4个空格的缩进
                indent = " " * min(4, leading_spaces // 2)
                return indent + line.strip()
        
        return line
    
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
    
    async def _connect_direct_tcp(self, host, port, username, password, timeout):
        """使用直接TCP套接字连接，绕过标准telnet处理以提高性能"""
        try:
            def tcp_connect():
                try:
                    # 创建TCP套接字
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(10)  # 较短的连接超时
                    
                    # 连接到目标设备
                    sock.connect((host, port))
                    
                    # 设置为非阻塞模式以支持快速读取
                    sock.setblocking(False)
                    
                    # 缓冲区接收数据
                    buffer = b""
                    
                    # 1. 接收初始欢迎信息
                    start_time = time.time()
                    while time.time() - start_time < 3:
                        try:
                            ready = select.select([sock], [], [], 0.2)
                            if ready[0]:
                                data = sock.recv(4096)
                                if not data:
                                    break
                                buffer += data
                            else:
                                break
                        except Exception:
                            pass
                    
                    # 2. 无论收到什么，先发送回车激活提示符
                    sock.send(b"\r\n")
                    time.sleep(0.2)
                    
                    # 清空缓冲区
                    try:
                        while True:
                            ready = select.select([sock], [], [], 0.1)
                            if ready[0]:
                                data = sock.recv(4096)
                                if not data:
                                    break
                                buffer = data  # 只保留最新数据
                            else:
                                break
                    except Exception:
                        pass
                    
                    # 3. 直接发送用户名 - 无需等待提示
                    sock.send((username + "\r\n").encode('ascii'))
                    time.sleep(0.3)
                    
                    # 4. 直接发送密码 - 无需等待提示
                    sock.send((password + "\r\n").encode('ascii'))
                    
                    # 5. 快速检查是否成功登录 (检查命令提示符)
                    success = False
                    login_output = b""
                    
                    # 常见的各种设备提示符
                    prompts = [b">", b"#", b"$", b"%", b"]", b"}", b":", b"<"]
                    
                    # 等待登录成功的标志
                    start_time = time.time()
                    while time.time() - start_time < 5:
                        try:
                            ready = select.select([sock], [], [], 0.2)
                            if ready[0]:
                                data = sock.recv(4096)
                                if not data:
                                    break
                                login_output += data
                                
                                # 检查是否包含任何提示符
                                if any(p in login_output for p in prompts):
                                    success = True
                                    break
                                
                                # 检查是否有登录失败信息
                                if (b"incorrect" in login_output.lower() or 
                                    b"invalid" in login_output.lower() or 
                                    b"failed" in login_output.lower()):
                                    return None, "认证失败: 用户名或密码不正确"
                            else:
                                # 没有更多数据可读
                                time.sleep(0.1)
                        except Exception:
                            time.sleep(0.1)
                    
                    if not success:
                        # 最后尝试
                        sock.send(b"\r\n")
                        time.sleep(0.5)
                        
                        try:
                            data = sock.recv(4096)
                            if any(p in data for p in prompts):
                                success = True
                                login_output += data
                        except Exception:
                            pass
                    
                    if success:
                        # 创建一个telnetlib对象，但使用我们的已连接套接字
                        client = telnetlib.Telnet()
                        client.sock = sock
                        
                        # 提取设备信息
                        device_info = "Unknown device"
                        try:
                            decoded_output = login_output.decode('ascii', errors='replace')
                            # 提取有意义的行
                            lines = [line for line in decoded_output.split('\n') if line.strip()]
                            if lines:
                                device_info = lines[0].strip()
                        except Exception:
                            pass
                        
                        return client, device_info
                    
                    return None, "TCP直连失败 - 未检测到命令提示符"
                except Exception as e:
                    return None, f"TCP直连过程出错: {str(e)}"
            
            # 在线程池中执行连接函数
            client, error_or_info = await asyncio.get_event_loop().run_in_executor(
                self.executor, tcp_connect
            )
            
            if client:
                logger.info("使用TCP直连方法成功连接")
                return True, client, error_or_info
            
            logger.debug(f"TCP直连方法失败: {error_or_info}")
            return False, None, None
        except Exception as e:
            logger.debug(f"TCP直连方法异常: {str(e)}")
            return False, None, None 