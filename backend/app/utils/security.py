import secrets
import base64
from typing import Optional
from datetime import datetime, timedelta

from jose import jwt
from passlib.context import CryptContext

from app.config.settings import settings

# 密码上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)

def create_access_token(
    data: dict, expires_delta: Optional[timedelta] = None
) -> str:
    """创建JWT访问令牌"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
        
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt

def encrypt_device_password(password: str) -> str:
    """简单加密设备密码，用于内存存储"""
    # 注意：这不是强安全加密，仅用于避免明文内存存储
    # 生成随机密钥
    key = secrets.token_bytes(32)
    
    # XOR加密
    password_bytes = password.encode('utf-8')
    encrypted = bytes(a ^ b for a, b in zip(password_bytes, key))
    
    # Base64编码结果和密钥
    result = base64.b64encode(encrypted).decode('utf-8')
    key_str = base64.b64encode(key).decode('utf-8')
    
    return f"{result}|{key_str}"

def decrypt_device_password(encrypted_str: str) -> str:
    """解密设备密码"""
    result, key_str = encrypted_str.split('|')
    
    # 解码Base64
    encrypted = base64.b64decode(result)
    key = base64.b64decode(key_str)
    
    # XOR解密
    decrypted = bytes(a ^ b for a, b in zip(encrypted, key))
    
    return decrypted.decode('utf-8') 