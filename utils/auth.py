# memorycare_app/utils/auth.py
"""
认证和授权模块

本模块实现了简单的基于 Token 的身份验证系统。
支持医生和患者两种角色，使用内存存储 Token（生产环境应使用 Redis 或数据库）。

注意：这是简化版实现，生产环境需要：
1. 使用 JWT 或 OAuth2
2. 密码哈希加密（bcrypt/argon2）
3. Token 持久化存储
4. 刷新 Token 机制
"""

from typing import Optional
from datetime import datetime, timedelta
import secrets

# Token 存储字典：内存中的临时存储
# 键：Token 字符串
# 值：包含角色、用户名和过期时间的字典
# 注意：服务器重启后所有 Token 会失效
_tokens = {}  # token -> {"role": "doctor"|"patient", "username": str, "expires": datetime}


def issue_doctor_token(username: str, password: str) -> Optional[str]:
    """
    为医生用户颁发认证 Token
    
    参数:
        username: 医生用户名
        password: 医生密码
        
    返回:
        Optional[str]: 如果认证成功返回 Token 字符串，否则返回 None
        
    注意:
        - 当前实现使用硬编码的凭证（doctor/doctor）
        - 生产环境应从数据库验证并返回错误信息
    """
    # 验证医生凭证：当前使用硬编码验证
    # 生产环境应该从数据库查询并验证密码哈希
    if username == "doctor" and password == "doctor":
        # 生成安全的随机 Token：使用 secrets 模块生成 URL 安全的随机字符串
        token = "doc_" + secrets.token_urlsafe(16)
        print(f"[DEBUG] Issued doctor token: {token}")
        
        # 存储 Token 信息：包括角色、用户名和过期时间（8小时后）
        _tokens[token] = {
            "role": "doctor",
            "username": "doctor",
            "expires": datetime.utcnow() + timedelta(hours=8)  # Token 有效期 8 小时
        }
        return token
    
    # 认证失败返回 None
    return None


def issue_patient_token(username: str) -> str:
    """
    为患者用户颁发认证 Token
    
    参数:
        username: 患者用户名（已通过登录验证）
        
    返回:
        str: 患者 Token 字符串
        
    注意:
        - 此函数假设用户名已经通过密码验证
        - 调用此函数前应确保患者存在且密码正确
    """
    # 生成安全的随机 Token：使用 secrets 模块生成 URL 安全的随机字符串
    token = "pat_" + secrets.token_urlsafe(16)
    print(f"[DEBUG] Issued patient token: {token}")
    
    # 存储 Token 信息：包括角色、用户名和过期时间（8小时后）
    _tokens[token] = {
        "role": "patient",
        "username": username,
        "expires": datetime.utcnow() + timedelta(hours=8)  # Token 有效期 8 小时
    }
    return token


def whoami(token: str) -> Optional[dict]:
    """
    根据 Token 获取用户身份信息
    
    参数:
        token: 用户提供的认证 Token
        
    返回:
        Optional[dict]: 如果 Token 有效，返回包含角色和用户名的字典：
            {
                "role": "doctor" | "patient",
                "username": str,
                "expires": datetime
            }
            如果 Token 无效或已过期，返回 None
            
    使用场景:
        - API 端点验证用户身份
        - 检查用户权限（医生 vs 患者）
        - 获取当前登录用户信息
    """
    # 从 Token 存储中查找用户信息
    info = _tokens.get(token)
    
    # 如果 Token 不存在，返回 None
    if not info:
        return None
    
    # 检查 Token 是否已过期
    if info["expires"] < datetime.utcnow():
        # Token 已过期，从存储中删除并返回 None
        del _tokens[token]
        return None
    
    # Token 有效，返回用户信息
    return info
