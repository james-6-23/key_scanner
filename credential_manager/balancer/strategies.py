"""
负载均衡策略实现
"""

import random
import time
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class LoadBalancingStrategy(ABC):
    """负载均衡策略基类"""
    
    @abstractmethod
    def select(self, credentials: List[Any]) -> Optional[Any]:
        """
        选择一个凭证
        
        Args:
            credentials: 可用凭证列表
            
        Returns:
            选中的凭证，无可用返回None
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """获取策略名称"""
        pass


class RandomStrategy(LoadBalancingStrategy):
    """随机选择策略"""
    
    def select(self, credentials: List[Any]) -> Optional[Any]:
        if not credentials:
            return None
        return random.choice(credentials)
    
    def get_name(self) -> str:
        return "random"


class RoundRobinStrategy(LoadBalancingStrategy):
    """轮询策略"""
    
    def __init__(self):
        self.counters = defaultdict(int)
    
    def select(self, credentials: List[Any]) -> Optional[Any]:
        if not credentials:
            return None
        
        # 获取服务类型作为key
        key = credentials[0].service_type.value if credentials else "default"
        
        # 获取当前索引
        index = self.counters[key] % len(credentials)
        selected = credentials[index]
        
        # 更新计数器
        self.counters[key] += 1
        
        return selected
    
    def get_name(self) -> str:
        return "round_robin"


class WeightedRoundRobinStrategy(LoadBalancingStrategy):
    """加权轮询策略"""
    
    def __init__(self):
        self.current_weights = defaultdict(float)
        self.effective_weights = defaultdict(float)
    
    def select(self, credentials: List[Any]) -> Optional[Any]:
        if not credentials:
            return None
        
        if len(credentials) == 1:
            return credentials[0]
        
        # 计算权重（基于健康评分）
        total_weight = 0
        best_credential = None
        best_weight = 0
        
        for cred in credentials:
            # 使用健康评分作为权重
            weight = cred.calculate_health_score()
            
            # 更新当前权重
            cred_id = cred.id
            self.current_weights[cred_id] += weight
            total_weight += weight
            
            # 选择权重最高的
            if self.current_weights[cred_id] > best_weight:
                best_weight = self.current_weights[cred_id]
                best_credential = cred
        
        if best_credential:
            # 减少选中凭证的权重
            self.current_weights[best_credential.id] -= total_weight
        
        return best_credential
    
    def get_name(self) -> str:
        return "weighted_round_robin"


class LeastConnectionsStrategy(LoadBalancingStrategy):
    """最少连接策略"""
    
    def __init__(self):
        self.active_connections = defaultdict(int)
    
    def select(self, credentials: List[Any]) -> Optional[Any]:
        if not credentials:
            return None
        
        # 选择活跃连接最少的凭证
        best_credential = None
        min_connections = float('inf')
        
        for cred in credentials:
            connections = self.active_connections.get(cred.id, 0)
            if connections < min_connections:
                min_connections = connections
                best_credential = cred
        
        if best_credential:
            # 增加连接计数
            self.active_connections[best_credential.id] += 1
            
            # 模拟连接释放（实际应用中应在请求完成后调用）
            # self._release_connection(best_credential.id)
        
        return best_credential
    
    def release_connection(self, credential_id: str):
        """释放连接"""
        if credential_id in self.active_connections:
            self.active_connections[credential_id] = max(0, self.active_connections[credential_id] - 1)
    
    def get_name(self) -> str:
        return "least_connections"


class ResponseTimeStrategy(LoadBalancingStrategy):
    """响应时间策略 - 选择响应最快的"""
    
    def select(self, credentials: List[Any]) -> Optional[Any]:
        if not credentials:
            return None
        
        # 按平均响应时间排序（升序）
        sorted_creds = sorted(
            credentials,
            key=lambda c: c.metrics.avg_response_time if c.metrics.avg_response_time > 0 else float('inf')
        )
        
        # 选择响应最快的
        return sorted_creds[0] if sorted_creds else None
    
    def get_name(self) -> str:
        return "response_time"


class QuotaAwareStrategy(LoadBalancingStrategy):
    """配额感知策略 - 智能分配基于剩余配额"""
    
    def __init__(self):
        self.last_selections = defaultdict(float)
        self.selection_interval = 1.0  # 最小选择间隔（秒）
    
    def select(self, credentials: List[Any]) -> Optional[Any]:
        if not credentials:
            return None
        
        current_time = time.time()
        candidates = []
        
        for cred in credentials:
            # 计算配额得分
            quota_score = self._calculate_quota_score(cred)
            
            # 计算时间惩罚（避免频繁使用同一凭证）
            time_penalty = self._calculate_time_penalty(cred.id, current_time)
            
            # 计算性能得分
            performance_score = self._calculate_performance_score(cred)
            
            # 综合得分
            total_score = (
                quota_score * 0.5 +      # 配额权重50%
                performance_score * 0.3 +  # 性能权重30%
                time_penalty * 0.2        # 时间分散权重20%
            )
            
            candidates.append((cred, total_score))
        
        # 按得分排序
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # 选择得分最高的
        if candidates:
            selected = candidates[0][0]
            self.last_selections[selected.id] = current_time
            
            logger.debug(f"Selected credential {selected.masked_value} with score {candidates[0][1]:.2f}")
            return selected
        
        return None
    
    def _calculate_quota_score(self, credential: Any) -> float:
        """计算配额得分"""
        if credential.total_quota == 0:
            return 0.5  # 未知配额给中等分数
        
        quota_ratio = credential.remaining_quota / credential.total_quota
        
        # 非线性映射，剩余配额越多得分越高
        if quota_ratio > 0.8:
            return 1.0
        elif quota_ratio > 0.5:
            return 0.8
        elif quota_ratio > 0.2:
            return 0.5
        elif quota_ratio > 0.1:
            return 0.3
        else:
            return 0.1
    
    def _calculate_time_penalty(self, credential_id: str, current_time: float) -> float:
        """计算时间惩罚"""
        last_used = self.last_selections.get(credential_id, 0)
        time_since_last = current_time - last_used
        
        if time_since_last < self.selection_interval:
            # 最近刚用过，给低分
            return 0.2
        elif time_since_last < self.selection_interval * 5:
            return 0.5
        else:
            # 很久没用，给高分
            return 1.0
    
    def _calculate_performance_score(self, credential: Any) -> float:
        """计算性能得分"""
        # 成功率得分
        success_score = credential.metrics.success_rate
        
        # 响应时间得分
        avg_response = credential.metrics.avg_response_time
        if avg_response <= 0:
            response_score = 0.5
        elif avg_response < 1:
            response_score = 1.0
        elif avg_response < 2:
            response_score = 0.8
        elif avg_response < 5:
            response_score = 0.5
        else:
            response_score = 0.2
        
        # 综合性能得分
        return success_score * 0.7 + response_score * 0.3
    
    def get_name(self) -> str:
        return "quota_aware"


class AdaptiveStrategy(LoadBalancingStrategy):
    """自适应策略 - 根据实时情况动态调整"""
    
    def __init__(self):
        self.strategies = {
            "quota_aware": QuotaAwareStrategy(),
            "weighted_round_robin": WeightedRoundRobinStrategy(),
            "response_time": ResponseTimeStrategy()
        }
        self.current_strategy = "quota_aware"
        self.performance_history = defaultdict(list)
        self.adaptation_interval = 100  # 每100次请求评估一次
        self.request_count = 0
    
    def select(self, credentials: List[Any]) -> Optional[Any]:
        if not credentials:
            return None
        
        # 定期评估并切换策略
        self.request_count += 1
        if self.request_count % self.adaptation_interval == 0:
            self._adapt_strategy()
        
        # 使用当前策略选择
        strategy = self.strategies[self.current_strategy]
        selected = strategy.select(credentials)
        
        # 记录性能
        if selected:
            self._record_performance(selected)
        
        return selected
    
    def _adapt_strategy(self):
        """根据性能历史自适应调整策略"""
        # 评估各策略的性能
        best_strategy = self.current_strategy
        best_score = 0
        
        for strategy_name in self.strategies:
            score = self._evaluate_strategy_performance(strategy_name)
            if score > best_score:
                best_score = score
                best_strategy = strategy_name
        
        # 切换到最佳策略
        if best_strategy != self.current_strategy:
            logger.info(f"Switching strategy from {self.current_strategy} to {best_strategy}")
            self.current_strategy = best_strategy
    
    def _evaluate_strategy_performance(self, strategy_name: str) -> float:
        """评估策略性能"""
        history = self.performance_history.get(strategy_name, [])
        if not history:
            return 0.5  # 无历史数据，给中等分数
        
        # 计算最近的平均性能
        recent_history = history[-50:]  # 最近50次
        avg_success = sum(h["success"] for h in recent_history) / len(recent_history)
        avg_response = sum(h["response_time"] for h in recent_history) / len(recent_history)
        
        # 综合评分
        success_score = avg_success
        response_score = 1.0 / (1.0 + avg_response)  # 响应时间越短得分越高
        
        return success_score * 0.7 + response_score * 0.3
    
    def _record_performance(self, credential: Any):
        """记录性能数据"""
        self.performance_history[self.current_strategy].append({
            "success": credential.metrics.success_rate,
            "response_time": credential.metrics.avg_response_time,
            "timestamp": time.time()
        })
        
        # 限制历史记录大小
        if len(self.performance_history[self.current_strategy]) > 1000:
            self.performance_history[self.current_strategy] = \
                self.performance_history[self.current_strategy][-500:]
    
    def get_name(self) -> str:
        return f"adaptive({self.current_strategy})"


class HealthBasedStrategy(LoadBalancingStrategy):
    """基于健康评分的策略"""
    
    def __init__(self, threshold: float = 60.0):
        self.threshold = threshold
    
    def select(self, credentials: List[Any]) -> Optional[Any]:
        if not credentials:
            return None
        
        # 过滤健康的凭证
        healthy_creds = [
            c for c in credentials 
            if c.calculate_health_score() >= self.threshold
        ]
        
        if not healthy_creds:
            # 如果没有健康的，选择得分最高的
            credentials.sort(key=lambda c: c.calculate_health_score(), reverse=True)
            return credentials[0]
        
        # 在健康凭证中随机选择
        return random.choice(healthy_creds)
    
    def get_name(self) -> str:
        return "health_based"


# 策略工厂
_strategies: Dict[str, LoadBalancingStrategy] = {
    "random": RandomStrategy(),
    "round_robin": RoundRobinStrategy(),
    "weighted_round_robin": WeightedRoundRobinStrategy(),
    "least_connections": LeastConnectionsStrategy(),
    "response_time": ResponseTimeStrategy(),
    "quota_aware": QuotaAwareStrategy(),
    "adaptive": AdaptiveStrategy(),
    "health_based": HealthBasedStrategy()
}


def get_strategy(name: str) -> LoadBalancingStrategy:
    """
    获取负载均衡策略
    
    Args:
        name: 策略名称
        
    Returns:
        策略实例
    """
    strategy = _strategies.get(name)
    if not strategy:
        logger.warning(f"Unknown strategy: {name}, using default (quota_aware)")
        strategy = _strategies["quota_aware"]
    
    return strategy


def register_strategy(name: str, strategy: LoadBalancingStrategy):
    """
    注册自定义策略
    
    Args:
        name: 策略名称
        strategy: 策略实例
    """
    _strategies[name] = strategy
    logger.info(f"Registered strategy: {name}")


def list_strategies() -> List[str]:
    """获取所有可用策略名称"""
    return list(_strategies.keys())