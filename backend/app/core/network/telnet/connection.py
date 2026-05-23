"""
Telnet连接实现
处理基础Telnet连接操作
"""

import asyncio
import concurrent.futures
import re
import socket
import time
from typing import Optional

from app.core.network.base import ConnectionStatus, NetworkConnection
from app.core.network.telnet.client import TelnetClient
from app.core.network.telnet.protocols import TelnetProtocol
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TelnetConnection(NetworkConnection):
    """Telnet连接实现类"""

    def __init__(self, host: str, port: int, username: str, password: str):
        super().__init__(host, port, username, password)
        self.protocol = TelnetProtocol()
        self.login_timeout = 10
        self.command_timeout = 30
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        self.prompt_pattern = None  # 动态记录提示符
        self.username_prompt_patterns = [
            re.compile(rb"(?:username|user name|login)\s*(?::|\xef\xbc\x9a)", re.IGNORECASE),
        ]
        self.password_prompt_patterns = [
            re.compile(rb"password\s*(?::|\xef\xbc\x9a)", re.IGNORECASE),
        ]
        self.shell_prompt_patterns = [
            re.compile(rb"(?:^|[\r\n])\s*[<\[]?[\w.\-()/@]+[>\]#$]\s*$"),
            re.compile(rb"[>\]#$]\s*$"),
        ]

    async def connect(self, timeout: int = 30) -> tuple[bool, str]:
        """建立Telnet连接"""
        try:
            self.status = ConnectionStatus.CONNECTING
            logger.info(f"正在连接到 {self.host}:{self.port}")

            # 在线程池中执行连接操作
            loop = asyncio.get_event_loop()
            success, message = await loop.run_in_executor(
                self.executor,
                self._connect_sync,
                timeout,
            )

            if success:
                self.status = ConnectionStatus.CONNECTED
                self.connection_time = time.time()
                self.last_activity_time = time.time()
                logger.info(f"成功连接到 {self.host}:{self.port}")
            else:
                self.status = ConnectionStatus.ERROR
                logger.error(f"连接失败: {message}")

            return success, message

        except Exception as e:
            self.status = ConnectionStatus.ERROR
            error_msg = f"连接异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def _connect_sync(self, timeout: int) -> tuple[bool, str]:
        """同步连接实现"""
        try:
            # 检查主机可达性
            if not self._check_host_reachable(timeout):
                return False, f"主机 {self.host}:{self.port} 不可达"

            # 创建Telnet客户端
            self.client = TelnetClient()
            self.client.open(self.host, self.port, timeout)

            success, message = self._perform_login(line_ending=b"\n")
            if not success:
                return False, message

            return True, "连接成功"

        except socket.timeout:
            return False, "连接超时"
        except ConnectionRefusedError:
            return False, "连接被拒绝"
        except Exception as e:
            return False, f"连接失败: {str(e)}"

    def _perform_login(self, line_ending: bytes = b"\n") -> tuple[bool, str]:
        """使用小型状态机完成 Telnet 登录。"""
        auth_output = b""
        sent_username = False
        sent_password = False

        for _ in range(4):
            prompt_type, data = self._expect_login_prompt()
            auth_output += data

            if prompt_type == "username":
                self.client.write(self.username.encode("utf-8") + line_ending)
                sent_username = True
                continue

            if prompt_type == "password":
                self.client.write(self.password.encode("utf-8") + line_ending)
                sent_password = True
                continue

            if prompt_type == "shell":
                self._detect_prompt_pattern(data or auth_output)
                return True, "登录成功"

            break

        if not sent_username:
            return False, "未收到用户名或登录提示"
        if not sent_password:
            return False, "未收到密码提示"

        time.sleep(0.5)
        prompt_response = self.client.read_very_eager()
        auth_output += prompt_response

        if self._looks_like_shell_prompt(auth_output):
            self._detect_prompt_pattern(auth_output)
            return True, "登录成功"

        return False, "登录失败，未检测到设备提示符"

    def _expect_login_prompt(self) -> tuple[str, bytes]:
        """等待用户名、密码或登录后的设备提示符。"""
        patterns = (
            self.username_prompt_patterns
            + self.password_prompt_patterns
            + self.shell_prompt_patterns
        )
        index, _match, data = self.client.expect(patterns, self.login_timeout)

        if index < 0:
            return "unknown", data or b""

        username_end = len(self.username_prompt_patterns)
        password_end = username_end + len(self.password_prompt_patterns)

        if index < username_end:
            return "username", data or b""
        if index < password_end:
            return "password", data or b""
        return "shell", data or b""

    def _looks_like_shell_prompt(self, data: bytes) -> bool:
        """判断登录输出中是否包含设备命令提示符。"""
        if not data:
            return False

        lines = data.decode("utf-8", errors="ignore").splitlines()
        for line in reversed(lines[-3:]):
            stripped = line.strip()
            if self._is_pagination_text(stripped):
                continue
            if stripped and re.search(r"[>\]#$]\s*$", stripped):
                return True
        return False

    def _is_pagination_text(self, text: str) -> bool:
        """识别分页提示，避免误判为命令提示符。"""
        lowered = text.lower()
        pagination_markers = [
            "more",
            "press any key to continue",
            "press space to continue",
        ]
        return any(marker in lowered for marker in pagination_markers)

    def _check_host_reachable(self, timeout: float) -> bool:
        """检查主机是否可达"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((self.host, self.port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def _detect_prompt_pattern(self, response: bytes):
        """检测提示符模式"""
        try:
            if not response:
                return

            response_str = response.decode('utf-8', errors='ignore').strip()
            logger.debug(f"检测到的响应: {repr(response_str)}")

            # 常见提示符模式
            common_prompts = [b'#', b'>', b'$', b']']

            # 检查响应中的最后一个字符
            if response_str:
                last_char = response_str[-1].encode('utf-8')
                if last_char in common_prompts:
                    self.prompt_pattern = last_char
                    logger.info(f"检测到提示符: {last_char.decode('utf-8')}")
                    return

            # 如果没有找到，使用默认提示符
            for prompt in common_prompts:
                if prompt in response:
                    self.prompt_pattern = prompt
                    logger.info(f"使用提示符: {prompt.decode('utf-8')}")
                    return

            # 如果都没找到，使用默认
            self.prompt_pattern = b'#'
            logger.warning("未检测到明确提示符，使用默认 '#'")

        except Exception as e:
            logger.error(f"提示符检测失败: {str(e)}")
            self.prompt_pattern = b'#'

    def _detect_device_info(self) -> Optional[dict]:
        """检测设备信息 - 改进版本"""
        try:
            if not self.client:
                return None

            # 对于非华为设备，不执行设备检测命令，避免错误
            return {'device_type': 'unknown', 'model': 'unknown'}

        except Exception as e:
            logger.warning(f"设备信息检测失败: {str(e)}")

        return None

    async def execute_command(self, command: str) -> tuple[bool, str]:
        """执行命令"""
        try:
            if self.status != ConnectionStatus.CONNECTED or not self.client:
                return False, "连接未建立"

            self.last_activity_time = time.time()

            # 在线程池中执行命令
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                self._execute_command_sync,
                command,
            )

            return result

        except Exception as e:
            error_msg = f"命令执行异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def _execute_command_sync(self, command: str) -> tuple[bool, str]:
        """同步执行命令 - 改进版本支持分页"""
        try:
            logger.debug(f"执行命令: {command}")

            # 发送命令
            self.client.write(command.encode('utf-8') + b"\n")

            # 使用支持分页的方式读取响应
            response = self._read_command_response_with_pagination()

            if response:
                response_str = response.decode('utf-8', errors='ignore')
                # 清理响应数据
                response_str = self._clean_command_response(response_str, command)
                return True, response_str
            else:
                return False, "命令执行超时"

        except Exception as e:
            logger.error(f"命令执行异常: {str(e)}")
            return False, f"命令执行失败: {str(e)}"

    def _read_command_response_with_pagination(self) -> bytes:
        """读取命令响应，支持分页处理 - 修复缓冲区同步问题"""
        try:
            full_response = b""
            start_time = time.time()

            # 先等待一个短暂的时间，让命令开始执行
            time.sleep(0.5)

            # 常见的分页提示符
            pagination_patterns = [
                b"---- More ----",
                b"--More--",
                b"-- More --",
                b"<--- More --->",
                b"Press any key to continue",
                b"Press SPACE to continue",
                b"\x1b[7m--More--\x1b[m",  # 高亮显示的More
            ]

            # 记录稳定状态
            stable_cycles = 0
            last_response_length = 0
            max_stable_cycles = 5  # 最大稳定周期数

            while time.time() - start_time < self.command_timeout:
                # 读取当前可用数据
                chunk = self.client.read_very_eager()

                if chunk:
                    full_response += chunk
                    stable_cycles = 0  # 重置稳定计数
                    last_response_length = len(full_response)

                    logger.debug(f"读取到数据块: {len(chunk)} 字节，总长度: {len(full_response)}")

                    # 检查是否包含分页提示
                    response_str = chunk.decode('utf-8', errors='ignore')
                    has_pagination = any(pattern.decode('utf-8', errors='ignore') in response_str
                                        for pattern in pagination_patterns
                                        if pattern not in [b"\x1b[7m--More--\x1b[m"])

                    # 检查ANSI编码的More提示
                    if b"\x1b[7m--More--\x1b[m" in chunk or re.search(rb'\x1b\[\d*m--More--\x1b\[\d*m', chunk):
                        has_pagination = True

                    if has_pagination:
                        logger.debug("检测到分页提示，发送空格键继续")
                        # 发送空格键继续显示
                        self.client.write(b" ")
                        time.sleep(0.3)  # 等待响应
                        continue

                    # 检查是否出现提示符（命令结束）
                    if self._check_command_completion(chunk, full_response):
                        logger.debug("检测到命令完成标记")
                        break

                else:
                    # 没有新数据，检查是否稳定
                    if len(full_response) == last_response_length and len(full_response) > 0:
                        stable_cycles += 1
                        logger.debug(f"稳定周期: {stable_cycles}/{max_stable_cycles}")

                        if stable_cycles >= max_stable_cycles:
                            logger.debug("数据稳定，命令可能已完成")
                            # 再次检查是否有提示符
                            if self._check_command_completion(b"", full_response):
                                break
                            # 如果没有提示符但数据稳定，尝试发送回车键触发提示符
                            if stable_cycles == max_stable_cycles:
                                logger.debug("尝试发送回车键触发提示符")
                                self.client.write(b"\n")
                                time.sleep(0.2)
                    else:
                        stable_cycles = 0

                time.sleep(0.1)  # 等待100ms

            # 最后再次尝试读取任何剩余数据
            final_chunk = self.client.read_very_eager()
            if final_chunk:
                full_response += final_chunk
                logger.debug(f"最终读取到额外数据: {len(final_chunk)} 字节")

            logger.info(f"命令响应读取完成，总长度: {len(full_response)} 字节")
            return full_response

        except (ConnectionResetError, BrokenPipeError, OSError) as e:
            logger.error(f"读取分页响应失败: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"读取分页响应失败: {str(e)}")
            return full_response if 'full_response' in locals() else b""

    def _check_command_completion(self, chunk: bytes, full_response: bytes) -> bool:
        """检查命令是否完成"""
        try:
            chunk_text = chunk.decode('utf-8', errors='ignore').strip()
            if chunk_text and self._is_pagination_text(chunk_text):
                return False

            # 检查动态检测的提示符
            if self.prompt_pattern and self.prompt_pattern in chunk:
                logger.debug(f"检测到动态提示符: {self.prompt_pattern.decode('utf-8')}")
                return True

            # 检查通用提示符
            common_prompts = [b'#', b'>', b'$', b']']

            # 在当前数据块中检查
            if chunk:
                lines = chunk.split(b'\n')
                for line in lines:
                    line = line.strip()
                    if line and any(prompt in line for prompt in common_prompts):
                        # 检查是否像提示符（在行尾或单独一行）
                        line_str = line.decode('utf-8', errors='ignore')
                        if self._is_pagination_text(line_str):
                            continue
                        if any(line_str.endswith(prompt.decode('utf-8')) for prompt in common_prompts):
                            logger.debug(f"检测到通用提示符: {line_str}")
                            return True

            # 在全部响应中检查最后几行
            if full_response:
                response_str = full_response.decode('utf-8', errors='ignore')
                lines = response_str.split('\n')
                # 检查最后3行
                for line in lines[-3:]:
                    line = line.strip()
                    if not line or self._is_pagination_text(line):
                        continue
                    if any(line.endswith(prompt.decode('utf-8')) for prompt in common_prompts):
                        logger.debug(f"检测到响应末尾提示符: {line}")
                        return True

            return False

        except Exception as e:
            logger.error(f"检查命令完成状态失败: {str(e)}")
            return False

    def _clean_command_response(self, response: str, command: str) -> str:
        """清理命令响应数据 - 改进版本"""
        try:
            # 移除命令回显
            if command in response:
                response = response.replace(command, "", 1)

            # 移除分页提示符
            import re
            pagination_patterns = [
                r'---- More ----',
                r'--More--',
                r'-- More --',
                r'<--- More --->',
                r'Press any key to continue.*?\n?',
                r'Press SPACE to continue.*?\n?',
                r'\x1b\[\d*m--More--\x1b\[\d*m',  # ANSI编码的More
            ]

            for pattern in pagination_patterns:
                response = re.sub(pattern, '', response, flags=re.IGNORECASE)

            # 移除常见的控制字符
            response = re.sub(r'\x1b\[[0-9;]*[mK]', '', response)  # ANSI转义序列
            response = re.sub(r'\r\n|\r', '\n', response)  # 统一换行符
            response = re.sub(r'\x00|\x07|\x08', '', response)  # 移除控制字符

            # 移除连续空行
            response = re.sub(r'\n\s*\n\s*\n', '\n\n', response)

            # 移除开头和结尾的空行
            response = response.strip()

            # 移除最后一行的提示符
            lines = response.split('\n')
            if lines and lines[-1].strip():
                last_line = lines[-1].strip()
                # 检查最后一行是否是提示符
                if any(prompt in last_line.encode('utf-8') for prompt in [b'#', b'>', b'$', b']']):
                    lines = lines[:-1]
                    response = '\n'.join(lines)

            return response

        except Exception as e:
            logger.error(f"清理响应数据失败: {str(e)}")
            return response

    async def disconnect(self) -> tuple[bool, str]:
        """断开连接"""
        try:
            if self.client:
                self.client.close()
                self.client = None

            self.status = ConnectionStatus.DISCONNECTED
            logger.info(f"已断开与 {self.host}:{self.port} 的连接")
            return True, "断开成功"

        except Exception as e:
            error_msg = f"断开连接异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def is_alive(self) -> bool:
        """检查连接是否活跃"""
        if not self.client or self.status != ConnectionStatus.CONNECTED:
            return False

        try:
            # 检查连接是否断开
            self.client.sock.settimeout(0.1)
            self.client.sock.recv(1, socket.MSG_PEEK)
            return True
        except socket.timeout:
            return True  # 没有数据可读，连接正常
        except OSError:
            return False

    def __del__(self):
        """析构函数"""
        try:
            if self.executor:
                self.executor.shutdown(wait=False)
        except Exception:
            pass
