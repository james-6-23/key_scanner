"""
凭证数据模型定义
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
import time
import hashlib
import json


class ServiceType(Enum):
    """支持的服务类型"""
    GITHUB = "github"
    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE = "azure"
    AWS = "aws"
    CUSTOM = "custom"


class CredentialStatus(Enum):
    """凭证状态"""
    ACTIVE = "active"           # 活跃可用
    EXHAUSTED = "exhausted"     # 配额耗尽
    RATE_LIMITED = "rate_limited"  # 被限流
    INVALID = "invalid"         # 无效
    EXPIRED = "expired"         # 过期
    PENDING = "pending"         # 待验证
    ARCHIVED = "archived"       # 已归档


@dataclass
class CredentialMetrics:
    """凭证性能指标"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    last_response_time: float = 0.0
    error_count: int = 0
    
    @property
    def success_rate(self) -> float:
        """计算成功率"""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    @property
    def avg_response_time(self) -> float:
        """计算平均响应时间"""
        if self.successful_requests == 0:
            return 0.0
        return self.total_response_time / self.successful_requests
    
    def update(self, success: bool, response_time: float):
        """更新指标"""
        self.total_requests += 1
        self.last_response_time = response_time
        self.total_response_time += response_time
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            self.error_count += 1


@dataclass
class Credential:
    """凭证实体"""
    id: str = field(default_factory=lambda: "")
    service_type: ServiceType = ServiceType.CUSTOM
    value: str = ""
    status: CredentialStatus = CredentialStatus.PENDING
    
    # 配额信息
    remaining_quota: int = 0
    total_quota: int = 0
    reset_time: Optional[datetime] = None
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    # 性能指标
    metrics: CredentialMetrics = field(default_factory=CredentialMetrics)
    
    # 元数据
    source: str = "unknown"  # 凭证来源
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 加密相关
    encrypted: bool = False
    encryption_key_id: Optional[str] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.id:
            # 生成唯一ID
            self.id = self._generate_id()
        
        # 掩码处理敏感信息
        self.masked_value = self._mask_value()
    
    def _generate_id(self) -> str:
        """生成唯一ID"""
        content = f"{self.service_type.value}:{self.value}:{time.time()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _mask_value(self) -> str:
        """掩码处理凭证值"""
        if len(self.value) <= 10:
            return "***"
        return f"{self.value[:7]}...{self.value[-4:]}"
    
    def is_valid(self) -> bool:
        """检查凭证是否有效"""
        if self.status not in [CredentialStatus.ACTIVE, CredentialStatus.RATE_LIMITED]:
            return False
        
        # 检查是否过期
        if self.expires_at and datetime.now() > self.expires_at:
            self.status = CredentialStatus.EXPIRED
            return False
        
        return True
    
    def is_available(self) -> bool:
        """检查凭证是否可用"""
        if not self.is_valid():
            return False
        
        # 检查是否被限流
        if self.status == CredentialStatus.RATE_LIMITED:
            if self.reset_time and datetime.now() > self.reset_time:
                self.status = CredentialStatus.ACTIVE
                return True
            return False
        
        # 检查配额
        if self.remaining_quota <= 0:
            return False
        
        return True
    
    def update_quota(self, remaining: int, total: int = None, reset_time: datetime = None):
        """更新配额信息"""
        self.remaining_quota = remaining
        if total is not None:
            self.total_quota = total
        if reset_time:
            self.reset_time = reset_time
        
        # 根据配额更新状态
        if remaining <= 0:
            if reset_time and reset_time > datetime.now():
                self.status = CredentialStatus.RATE_LIMITED
            else:
                self.status = CredentialStatus.EXHAUSTED
        elif self.status in [CredentialStatus.RATE_LIMITED, CredentialStatus.EXHAUSTED]:
            self.status = CredentialStatus.ACTIVE
        
        self.updated_at = datetime.now()
    
    def calculate_health_score(self) -> float:
        """计算健康评分 (0-100)"""
        score = 0.0
        
        # 状态评分 (40分)
        status_scores = {
            CredentialStatus.ACTIVE: 40,
            CredentialStatus.RATE_LIMITED: 20,
            CredentialStatus.EXHAUSTED: 10,
            CredentialStatus.PENDING: 15,
            CredentialStatus.INVALID: 0,
            CredentialStatus.EXPIRED: 0,
            CredentialStatus.ARCHIVED: 0
        }
        score += status_scores.get(self.status, 0)
        
        # 配额评分 (30分)
        if self.total_quota > 0:
            quota_ratio = self.remaining_quota / self.total_quota
            score += quota_ratio * 30
        
        # 成功率评分 (20分)
        score += self.metrics.success_rate * 20
        
        # 响应时间评分 (10分)
        if self.metrics.avg_response_time > 0:
            # 响应时间越短分数越高
            if self.metrics.avg_response_time < 1:
                score += 10
            elif self.metrics.avg_response_time < 2:
                score += 8
            elif self.metrics.avg_response_time < 5:
                score += 5
            else:
                score += 2
        
        return min(100, max(0, score))
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "service_type": self.service_type.value,
            "masked_value": self.masked_value,
            "status": self.status.value,
            "remaining_quota": self.remaining_quota,
            "total_quota": self.total_quota,
            "reset_time": self.reset_time.isoformat() if self.reset_time else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "health_score": self.calculate_health_score(),
            "metrics": {
                "total_requests": self.metrics.total_requests,
                "success_rate": self.metrics.success_rate,
                "avg_response_time": self.metrics.avg_response_time
            },
            "source": self.source,
            "tags": self.tags,
            "metadata": self.metadata
        }
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class CredentialPool:
    """凭证池"""
    service_type: ServiceType
    credentials: List[Credential] = field(default_factory=list)
    min_pool_size: int = 10
    max_pool_size: int = 100
    
    def add(self, credential: Credential) -> bool:
        """添加凭证到池"""
        if len(self.credentials) >= self.max_pool_size:
            return False
        
        # 检查是否已存在
        for cred in self.credentials:
            if cred.value == credential.value:
                return False
        
        self.credentials.append(credential)
        return True
    
    def remove(self, credential_id: str) -> bool:
        """从池中移除凭证"""
        for i, cred in enumerate(self.credentials):
            if cred.id == credential_id:
                del self.credentials[i]
                return True
        return False
    
    def get_available(self) -> List[Credential]:
        """获取所有可用凭证"""
        return [c for c in self.credentials if c.is_available()]
    
    def get_by_status(self, status: CredentialStatus) -> List[Credential]:
        """按状态获取凭证"""
        return [c for c in self.credentials if c.status == status]
    
    def get_best(self) -> Optional[Credential]:
        """获取最佳凭证"""
        available = self.get_available()
        if not available:
            return None
        
        # 按健康评分排序
        available.sort(key=lambda c: c.calculate_health_score(), reverse=True)
        return available[0]
    
    def needs_replenishment(self) -> bool:
        """检查是否需要补充凭证"""
        available_count = len(self.get_available())
        return available_count < self.min_pool_size
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = len(self.credentials)
        available = len(self.get_available())
        
        status_counts = {}
        for status in CredentialStatus:
            count = len(self.get_by_status(status))
            if count > 0:
                status_counts[status.value] = count
        
        avg_health = 0
        if total > 0:
            avg_health = sum(c.calculate_health_score() for c in self.credentials) / total
        
        return {
            "total": total,
            "available": available,
            "status_distribution": status_counts,
            "average_health_score": avg_health,
            "needs_replenishment": self.needs_replenishment()
        }