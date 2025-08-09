"""
Credential Manager - 高级API凭证管理系统

一个企业级的API凭证生命周期管理解决方案，提供：
- 智能发现和收集
- 动态轮换和负载均衡
- 自愈机制
- 安全存储
"""

__version__ = "1.0.0"
__author__ = "Key Scanner Team"

from .core.manager import CredentialManager
from .core.models import Credential, CredentialStatus, ServiceType

__all__ = [
    "CredentialManager",
    "Credential",
    "CredentialStatus",
    "ServiceType",
]