"""
健康检查和自愈机制实现
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import threading
from collections import deque
import json

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    RECOVERING = "recovering"


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    credential_id: str
    status: HealthStatus
    score: float
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealingAction:
    """自愈动作"""
    action_type: str
    credential_id: str
    description: str
    priority: int  # 1-10, 10最高
    executed: bool = False
    success: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    result: Optional[str] = None


class HealthChecker:
    """健康检查器"""
    
    def __init__(self, 
                 check_interval: int = 60,
                 history_size: int = 100):
        """
        初始化健康检查器
        
        Args:
            check_interval: 检查间隔（秒）
            history_size: 历史记录大小
        """
        self.check_interval = check_interval
        self.history_size = history_size
        self.check_history: Dict[str, deque] = {}
        self.is_running = False
        self._check_thread: Optional[threading.Thread] = None
        self._validators: List[Callable] = []
        
    def add_validator(self, validator: Callable):
        """添加验证器"""
        self._validators.append(validator)
        
    def check_credential(self, credential: Any) -> HealthCheckResult:
        """
        检查单个凭证健康状态
        
        Args:
            credential: 凭证对象
            
        Returns:
            健康检查结果
        """
        issues = []
        recommendations = []
        
        # 基础健康评分
        health_score = credential.calculate_health_score()
        
        # 检查状态
        if credential.status.value in ["revoked", "invalid"]:
            issues.append(f"Credential status is {credential.status.value}")
            recommendations.append("Remove or replace this credential")
            
        # 检查配额
        if credential.total_quota > 0:
            quota_usage = 1 - (credential.remaining_quota / credential.total_quota)
            if quota_usage > 0.9:
                issues.append(f"Quota usage is {quota_usage*100:.1f}%")
                recommendations.append("Consider adding more credentials")
            elif quota_usage > 0.7:
                issues.append(f"Quota usage is {quota_usage*100:.1f}%")
                recommendations.append("Monitor quota consumption")
                
        # 检查性能指标
        metrics = credential.metrics
        if metrics.success_rate < 0.5:
            issues.append(f"Low success rate: {metrics.success_rate*100:.1f}%")
            recommendations.append("Investigate failure causes")
            
        if metrics.avg_response_time > 5:
            issues.append(f"High response time: {metrics.avg_response_time:.2f}s")
            recommendations.append("Check network or service issues")
            
        # 检查最后使用时间
        if credential.last_used:
            time_since_use = datetime.now() - credential.last_used
            if time_since_use > timedelta(hours=24):
                issues.append(f"Not used for {time_since_use.days} days")
                recommendations.append("Verify credential is still valid")
                
        # 运行自定义验证器
        for validator in self._validators:
            try:
                validator_result = validator(credential)
                if validator_result and isinstance(validator_result, dict):
                    if "issues" in validator_result:
                        issues.extend(validator_result["issues"])
                    if "recommendations" in validator_result:
                        recommendations.extend(validator_result["recommendations"])
            except Exception as e:
                logger.error(f"Validator error: {e}")
                
        # 确定健康状态
        if health_score >= 80 and not issues:
            status = HealthStatus.HEALTHY
        elif health_score >= 60:
            status = HealthStatus.DEGRADED
        elif health_score >= 40:
            status = HealthStatus.UNHEALTHY
        else:
            status = HealthStatus.CRITICAL
            
        # 如果凭证正在恢复
        if credential.status.value == "rate_limited":
            status = HealthStatus.RECOVERING
            
        result = HealthCheckResult(
            credential_id=credential.id,
            status=status,
            score=health_score,
            issues=issues,
            recommendations=recommendations,
            metadata={
                "quota_remaining": credential.remaining_quota,
                "success_rate": metrics.success_rate,
                "avg_response_time": metrics.avg_response_time
            }
        )
        
        # 记录历史
        self._record_history(credential.id, result)
        
        return result
        
    def _record_history(self, credential_id: str, result: HealthCheckResult):
        """记录健康检查历史"""
        if credential_id not in self.check_history:
            self.check_history[credential_id] = deque(maxlen=self.history_size)
        self.check_history[credential_id].append(result)
        
    def get_health_trend(self, credential_id: str, hours: int = 24) -> Dict[str, Any]:
        """
        获取健康趋势
        
        Args:
            credential_id: 凭证ID
            hours: 查看过去多少小时
            
        Returns:
            健康趋势数据
        """
        if credential_id not in self.check_history:
            return {"error": "No history available"}
            
        history = self.check_history[credential_id]
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_checks = [
            check for check in history 
            if check.timestamp >= cutoff_time
        ]
        
        if not recent_checks:
            return {"error": "No recent data"}
            
        # 计算趋势
        scores = [check.score for check in recent_checks]
        avg_score = sum(scores) / len(scores)
        
        # 计算状态分布
        status_counts = {}
        for check in recent_checks:
            status_counts[check.status.value] = status_counts.get(check.status.value, 0) + 1
            
        # 收集所有问题
        all_issues = []
        for check in recent_checks:
            all_issues.extend(check.issues)
            
        # 找出最常见的问题
        issue_counts = {}
        for issue in all_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
            
        return {
            "credential_id": credential_id,
            "period_hours": hours,
            "check_count": len(recent_checks),
            "average_score": avg_score,
            "current_status": recent_checks[-1].status.value if recent_checks else None,
            "status_distribution": status_counts,
            "common_issues": sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            "score_trend": "improving" if len(scores) > 1 and scores[-1] > scores[0] else "declining"
        }
        
    def start_monitoring(self, credentials_provider: Callable):
        """
        启动后台监控
        
        Args:
            credentials_provider: 提供凭证列表的回调函数
        """
        if self.is_running:
            logger.warning("Health monitoring already running")
            return
            
        self.is_running = True
        self._check_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(credentials_provider,),
            daemon=True
        )
        self._check_thread.start()
        logger.info("Health monitoring started")
        
    def stop_monitoring(self):
        """停止监控"""
        self.is_running = False
        if self._check_thread:
            self._check_thread.join(timeout=5)
        logger.info("Health monitoring stopped")
        
    def _monitoring_loop(self, credentials_provider: Callable):
        """监控循环"""
        while self.is_running:
            try:
                credentials = credentials_provider()
                for credential in credentials:
                    if not self.is_running:
                        break
                    self.check_credential(credential)
                    
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                
            # 等待下一次检查
            time.sleep(self.check_interval)


class SelfHealingEngine:
    """自愈引擎"""
    
    def __init__(self, health_checker: HealthChecker):
        """
        初始化自愈引擎
        
        Args:
            health_checker: 健康检查器实例
        """
        self.health_checker = health_checker
        self.healing_actions: deque = deque(maxlen=1000)
        self.healing_strategies: Dict[str, Callable] = {}
        self._register_default_strategies()
        
    def _register_default_strategies(self):
        """注册默认自愈策略"""
        self.register_strategy("quota_exhausted", self._heal_quota_exhausted)
        self.register_strategy("rate_limited", self._heal_rate_limited)
        self.register_strategy("invalid_credential", self._heal_invalid_credential)
        self.register_strategy("performance_degradation", self._heal_performance_degradation)
        self.register_strategy("connection_failure", self._heal_connection_failure)
        
    def register_strategy(self, issue_type: str, strategy: Callable):
        """
        注册自愈策略
        
        Args:
            issue_type: 问题类型
            strategy: 处理策略函数
        """
        self.healing_strategies[issue_type] = strategy
        logger.info(f"Registered healing strategy for: {issue_type}")
        
    async def diagnose_and_heal(self, credential: Any, manager: Any) -> List[HealingAction]:
        """
        诊断并自愈
        
        Args:
            credential: 凭证对象
            manager: 凭证管理器实例
            
        Returns:
            执行的自愈动作列表
        """
        # 执行健康检查
        health_result = self.health_checker.check_credential(credential)
        
        # 如果健康，无需处理
        if health_result.status == HealthStatus.HEALTHY:
            return []
            
        actions = []
        
        # 根据问题类型执行自愈
        for issue in health_result.issues:
            action = await self._create_healing_action(
                credential, 
                issue, 
                health_result,
                manager
            )
            if action:
                actions.append(action)
                
        # 执行自愈动作
        for action in actions:
            await self._execute_healing_action(action, credential, manager)
            
        return actions
        
    async def _create_healing_action(self, 
                                    credential: Any,
                                    issue: str,
                                    health_result: HealthCheckResult,
                                    manager: Any) -> Optional[HealingAction]:
        """创建自愈动作"""
        # 根据问题类型确定动作
        if "Quota usage" in issue and "90%" in issue:
            return HealingAction(
                action_type="quota_exhausted",
                credential_id=credential.id,
                description="Quota nearly exhausted, need rotation",
                priority=8
            )
        elif "rate_limited" in credential.status.value.lower():
            return HealingAction(
                action_type="rate_limited",
                credential_id=credential.id,
                description="Rate limited, waiting for recovery",
                priority=6
            )
        elif "invalid" in credential.status.value.lower():
            return HealingAction(
                action_type="invalid_credential",
                credential_id=credential.id,
                description="Invalid credential, needs replacement",
                priority=10
            )
        elif "Low success rate" in issue:
            return HealingAction(
                action_type="performance_degradation",
                credential_id=credential.id,
                description="Performance degradation detected",
                priority=5
            )
        elif "High response time" in issue:
            return HealingAction(
                action_type="connection_failure",
                credential_id=credential.id,
                description="Connection issues detected",
                priority=4
            )
            
        return None
        
    async def _execute_healing_action(self, 
                                     action: HealingAction,
                                     credential: Any,
                                     manager: Any):
        """执行自愈动作"""
        try:
            strategy = self.healing_strategies.get(action.action_type)
            if strategy:
                result = await strategy(credential, manager)
                action.executed = True
                action.success = result.get("success", False)
                action.result = result.get("message", "")
                
                logger.info(f"Healing action executed: {action.action_type} - {action.result}")
            else:
                logger.warning(f"No strategy for action type: {action.action_type}")
                
        except Exception as e:
            logger.error(f"Healing action failed: {e}")
            action.executed = True
            action.success = False
            action.result = str(e)
            
        finally:
            self.healing_actions.append(action)
            
    async def _heal_quota_exhausted(self, credential: Any, manager: Any) -> Dict[str, Any]:
        """处理配额耗尽"""
        try:
            # 标记凭证为降级状态
            from ..core.models import CredentialStatus
            credential.status = CredentialStatus.DEGRADED
            
            # 降低权重
            credential.metrics.success_rate *= 0.5
            
            # 触发凭证轮换
            manager.rotate_credential(credential.id)
            
            return {
                "success": True,
                "message": f"Credential {credential.masked_value} marked for rotation"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to handle quota exhaustion: {e}"
            }
            
    async def _heal_rate_limited(self, credential: Any, manager: Any) -> Dict[str, Any]:
        """处理速率限制"""
        try:
            from ..core.models import CredentialStatus
            
            # 设置恢复时间
            recovery_time = 60  # 默认60秒
            if "x-ratelimit-reset" in credential.metadata:
                recovery_time = int(credential.metadata["x-ratelimit-reset"]) - time.time()
                
            # 暂时禁用凭证
            credential.status = CredentialStatus.RATE_LIMITED
            
            # 设置恢复计划
            async def recover():
                await asyncio.sleep(recovery_time)
                credential.status = CredentialStatus.ACTIVE
                logger.info(f"Credential {credential.masked_value} recovered from rate limit")
                
            asyncio.create_task(recover())
            
            return {
                "success": True,
                "message": f"Credential will recover in {recovery_time} seconds"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to handle rate limit: {e}"
            }
            
    async def _heal_invalid_credential(self, credential: Any, manager: Any) -> Dict[str, Any]:
        """处理无效凭证"""
        try:
            from ..core.models import CredentialStatus
            
            # 标记为无效
            credential.status = CredentialStatus.INVALID
            
            # 从活跃池中移除
            manager.remove_credential(credential.id)
            
            # 尝试重新验证
            if hasattr(manager, 'validate_credential'):
                is_valid = await manager.validate_credential(credential)
                if is_valid:
                    credential.status = CredentialStatus.ACTIVE
                    return {
                        "success": True,
                        "message": "Credential revalidated successfully"
                    }
                    
            return {
                "success": True,
                "message": f"Invalid credential {credential.masked_value} removed"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to handle invalid credential: {e}"
            }
            
    async def _heal_performance_degradation(self, credential: Any, manager: Any) -> Dict[str, Any]:
        """处理性能降级"""
        try:
            # 重置性能指标
            credential.metrics.reset_metrics()
            
            # 降低使用频率
            credential.metadata["throttle_factor"] = 0.5
            
            # 添加到观察列表
            if hasattr(manager, 'watch_list'):
                manager.watch_list.add(credential.id)
                
            return {
                "success": True,
                "message": "Performance metrics reset, credential under observation"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to handle performance degradation: {e}"
            }
            
    async def _heal_connection_failure(self, credential: Any, manager: Any) -> Dict[str, Any]:
        """处理连接失败"""
        try:
            # 测试连接
            test_success = False
            if hasattr(manager, 'test_connection'):
                test_success = await manager.test_connection(credential)
                
            if test_success:
                # 连接恢复
                credential.metrics.connection_failures = 0
                return {
                    "success": True,
                    "message": "Connection restored"
                }
            else:
                # 标记为降级
                from ..core.models import CredentialStatus
                credential.status = CredentialStatus.DEGRADED
                
                # 增加重试延迟
                credential.metadata["retry_delay"] = 30
                
                return {
                    "success": True,
                    "message": "Connection still failing, credential degraded"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to handle connection failure: {e}"
            }
            
    def get_healing_report(self, hours: int = 24) -> Dict[str, Any]:
        """
        获取自愈报告
        
        Args:
            hours: 统计过去多少小时
            
        Returns:
            自愈统计报告
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_actions = [
            action for action in self.healing_actions
            if action.timestamp >= cutoff_time
        ]
        
        if not recent_actions:
            return {"message": "No healing actions in the specified period"}
            
        # 统计数据
        total_actions = len(recent_actions)
        successful_actions = sum(1 for a in recent_actions if a.success)
        
        # 按类型统计
        action_types = {}
        for action in recent_actions:
            action_types[action.action_type] = action_types.get(action.action_type, 0) + 1
            
        # 按优先级统计
        priority_distribution = {}
        for action in recent_actions:
            priority_distribution[action.priority] = priority_distribution.get(action.priority, 0) + 1
            
        return {
            "period_hours": hours,
            "total_actions": total_actions,
            "successful_actions": successful_actions,
            "success_rate": successful_actions / total_actions if total_actions > 0 else 0,
            "action_types": action_types,
            "priority_distribution": priority_distribution,
            "most_common_issue": max(action_types.items(), key=lambda x: x[1])[0] if action_types else None
        }