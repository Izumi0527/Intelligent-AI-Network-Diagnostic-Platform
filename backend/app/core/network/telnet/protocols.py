"""
Telnet协议常量和工具函数
"""

import re
from typing import List, Optional

# Telnet控制字符常量
IAC = bytes([255])  # Interpret As Command
DONT = bytes([254])
DO = bytes([253])
WONT = bytes([252])
WILL = bytes([251])
SB = bytes([250])  # Subnegotiation Begin
SE = bytes([240])  # Subnegotiation End

# Telnet选项常量
OPT_ECHO = bytes([1])
OPT_SGA = bytes([3])  # Suppress Go Ahead
OPT_TTYPE = bytes([24])  # Terminal Type
OPT_NAWS = bytes([31])  # Window Size
OPT_TSPEED = bytes([32])  # Terminal Speed
OPT_LFLOW = bytes([33])  # Remote Flow Control
OPT_LINEMODE = bytes([34])  # Linemode
OPT_NEW_ENVIRON = bytes([39])  # New Environment Option


class TelnetProtocol:
    """Telnet协议处理工具类"""
    
    @staticmethod
    def negotiate_options(data: bytes) -> bytes:
        """处理Telnet选项协商"""
        # 简单的选项协商处理
        response = b''
        i = 0
        while i < len(data):
            if data[i:i+1] == IAC and i + 2 < len(data):
                command = data[i+1:i+2]
                option = data[i+2:i+3]
                
                if command == DO:
                    # 对大多数选项回应 WONT
                    if option in [OPT_ECHO, OPT_SGA]:
                        response += IAC + WILL + option
                    else:
                        response += IAC + WONT + option
                elif command == WILL:
                    # 对大多数选项回应 DONT
                    response += IAC + DONT + option
                
                i += 3
            else:
                i += 1
        
        return response
    
    @staticmethod
    def clean_response(text: str) -> str:
        """清理Telnet响应文本"""
        if not text:
            return ""
        
        # 移除ANSI转义序列
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        text = ansi_escape.sub('', text)
        
        # 移除回车符但保留换行符
        text = text.replace('\r\n', '\n').replace('\r', '')
        
        # 移除控制字符（除了换行和制表符）
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        return text
    
    @staticmethod
    def extract_device_info(response: str) -> dict:
        """从设备响应中提取设备信息"""
        info = {
            'device_type': 'unknown',
            'hostname': '',
            'version': '',
            'model': ''
        }
        
        response_lower = response.lower()
        
        # 检测设备类型
        if any(keyword in response_lower for keyword in ['huawei', 'vrp']):
            info['device_type'] = 'huawei'
        elif any(keyword in response_lower for keyword in ['cisco', 'ios']):
            info['device_type'] = 'cisco'
        elif any(keyword in response_lower for keyword in ['juniper', 'junos']):
            info['device_type'] = 'juniper'
        elif any(keyword in response_lower for keyword in ['h3c', 'comware']):
            info['device_type'] = 'h3c'
        
        # 提取主机名
        hostname_patterns = [
            r'hostname\s+(\S+)',
            r'sysname\s+(\S+)',
            r'([a-zA-Z0-9-_]+)>',
            r'([a-zA-Z0-9-_]+)#'
        ]
        
        for pattern in hostname_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match and not info['hostname']:
                info['hostname'] = match.group(1)
                break
        
        return info
    
    @staticmethod
    def detect_prompt_pattern(text: str) -> Optional[str]:
        """检测命令提示符模式"""
        lines = text.strip().split('\n')
        if not lines:
            return None
            
        last_line = lines[-1].strip()
        
        # 常见提示符模式
        patterns = [
            r'[a-zA-Z0-9\-_\.]+[>#\$]',  # 设备名 + > 或 # 或 $
            r'\[[a-zA-Z0-9\-_\.@]+\][>#\$]',  # [用户@设备名] + > 或 # 或 $
            r'[a-zA-Z0-9\-_\.]+\([a-zA-Z0-9\-_\.]+\)[>#]',  # 设备名(模式) + > 或 #
        ]
        
        for pattern in patterns:
            if re.search(pattern, last_line):
                return pattern
        
        return None
    
    @staticmethod
    def is_more_prompt(text: str) -> bool:
        """检测是否是分页提示符"""
        more_patterns = [
            r'--More--',
            r'-- More --', 
            r'\(more\)',
            r'Press any key to continue',
            r'Press SPACE to continue',
            r'\[Press space to continue or Ctrl-C to abort\]'
        ]
        
        text_lower = text.lower()
        return any(re.search(pattern.lower(), text_lower) for pattern in more_patterns)