import asyncio
import time
import random
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading
from queue import Queue, Empty
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from common.Logger import logger
from common.config import Config


@dataclass
class ValidationResult:
    """验证结果数据类"""
    key: str
    status: str  # "ok", "invalid", "rate_limited", "error"
    timestamp: datetime = field(default_factory=datetime.now)
    error_message: Optional[str] = None
    response_time: Optional[float] = None  # 响应时间（秒）
    proxy_used: Optional[str] = None


@dataclass
class ValidationStats:
    """验证统计数据"""
    total_validated: int = 0
    valid_keys: int = 0
    invalid_keys: int = 0
    rate_limited_keys: int = 0
    errors: int = 0
    total_time: float = 0.0
    avg_response_time: float = 0.0


class ParallelKeyValidator:
    """并行密钥验证器"""
    
    def __init__(self, max_workers: int = 10, batch_size: int = 50):
        """
        初始化并行验证器
        
        Args:
            max_workers: 最大并发工作线程数
            batch_size: 批处理大小
        """
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.stats = ValidationStats()
        self._lock = threading.Lock()
        
        # 代理池管理
        self.proxy_pool = Config.PROXY_LIST.copy() if Config.PROXY_LIST else []
        self.proxy_stats: Dict[str, Dict[str, int]] = {}  # 代理使用统计
        
        # 速率限制管理
        self.rate_limit_tracker: Dict[str, float] = {}  # 记录每个代理的限流时间
        self.rate_limit_cooldown = 60  # 限流冷却时间（秒）
        
        logger.info(f"🚀 Initialized ParallelKeyValidator with {max_workers} workers")
    
    def validate_batch(self, keys: List[str]) -> Dict[str, ValidationResult]:
        """
        批量验证密钥（同步接口）
        
        Args:
            keys: 待验证的密钥列表
            
        Returns:
            Dict[str, ValidationResult]: 密钥到验证结果的映射
        """
        start_time = time.time()
        results = {}
        
        # 分批处理
        for i in range(0, len(keys), self.batch_size):
            batch = keys[i:i + self.batch_size]
            batch_results = self._process_batch_sync(batch)
            results.update(batch_results)
            
            # 批次间短暂延迟，避免瞬时请求过多
            if i + self.batch_size < len(keys):
                time.sleep(0.5)
        
        # 更新统计信息
        self._update_stats(results, time.time() - start_time)
        
        return results
    
    async def validate_batch_async(self, keys: List[str]) -> Dict[str, ValidationResult]:
        """
        批量验证密钥（异步接口）
        
        Args:
            keys: 待验证的密钥列表
            
        Returns:
            Dict[str, ValidationResult]: 密钥到验证结果的映射
        """
        start_time = time.time()
        results = {}
        
        # 创建异步任务
        tasks = []
        for i in range(0, len(keys), self.batch_size):
            batch = keys[i:i + self.batch_size]
            task = self._process_batch_async(batch)
            tasks.append(task)
        
        # 等待所有批次完成
        batch_results = await asyncio.gather(*tasks)
        for batch_result in batch_results:
            results.update(batch_result)
        
        # 更新统计信息
        self._update_stats(results, time.time() - start_time)
        
        return results
    
    def _process_batch_sync(self, keys: List[str]) -> Dict[str, ValidationResult]:
        """同步处理一个批次"""
        futures = []
        results = {}
        
        # 提交验证任务
        for key in keys:
            future = self.executor.submit(self._validate_single_key, key)
            futures.append((key, future))
        
        # 收集结果
        for key, future in futures:
            try:
                result = future.result(timeout=30)  # 30秒超时
                results[key] = result
            except Exception as e:
                logger.error(f"❌ Validation failed for key {key[:10]}...: {e}")
                results[key] = ValidationResult(
                    key=key,
                    status="error",
                    error_message=str(e)
                )
        
        return results
    
    async def _process_batch_async(self, keys: List[str]) -> Dict[str, ValidationResult]:
        """异步处理一个批次"""
        loop = asyncio.get_event_loop()
        tasks = []
        
        # 创建验证任务
        for key in keys:
            task = loop.run_in_executor(self.executor, self._validate_single_key, key)
            tasks.append((key, task))
        
        # 等待所有任务完成
        results = {}
        for key, task in tasks:
            try:
                result = await asyncio.wait_for(task, timeout=30)
                results[key] = result
            except asyncio.TimeoutError:
                logger.error(f"⏱️ Validation timeout for key {key[:10]}...")
                results[key] = ValidationResult(
                    key=key,
                    status="error",
                    error_message="Timeout"
                )
            except Exception as e:
                logger.error(f"❌ Validation failed for key {key[:10]}...: {e}")
                results[key] = ValidationResult(
                    key=key,
                    status="error",
                    error_message=str(e)
                )
        
        return results
    
    def _validate_single_key(self, api_key: str) -> ValidationResult:
        """验证单个密钥"""
        start_time = time.time()
        proxy_config = self._get_best_proxy()
        
        try:
            # 添加随机延迟，避免并发请求过于集中
            time.sleep(random.uniform(0.1, 0.5))
            
            # 配置代理
            if proxy_config:
                proxy_url = proxy_config.get('http')
                import os
                os.environ['grpc_proxy'] = proxy_url
            
            # 配置Gemini客户端
            client_options = {
                "api_endpoint": "generativelanguage.googleapis.com"
            }
            
            genai.configure(
                api_key=api_key,
                client_options=client_options,
            )
            
            # 使用轻量级验证（只列出模型，不生成内容）
            model = genai.GenerativeModel(Config.HAJIMI_CHECK_MODEL)
            
            # 尝试一个最小的API调用
            response = model.generate_content("test", 
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=1,
                    temperature=0
                ))
            
            # 验证成功
            response_time = time.time() - start_time
            self._update_proxy_stats(proxy_config, True)
            
            return ValidationResult(
                key=api_key,
                status="ok",
                response_time=response_time,
                proxy_used=proxy_config.get('http') if proxy_config else None
            )
            
        except (google_exceptions.PermissionDenied, google_exceptions.Unauthenticated) as e:
            # 无效密钥
            response_time = time.time() - start_time
            self._update_proxy_stats(proxy_config, True)
            
            return ValidationResult(
                key=api_key,
                status="invalid",
                error_message="Invalid API key",
                response_time=response_time,
                proxy_used=proxy_config.get('http') if proxy_config else None
            )
            
        except google_exceptions.TooManyRequests as e:
            # 速率限制
            response_time = time.time() - start_time
            self._update_proxy_stats(proxy_config, False)
            self._mark_proxy_rate_limited(proxy_config)
            
            return ValidationResult(
                key=api_key,
                status="rate_limited",
                error_message="Rate limited",
                response_time=response_time,
                proxy_used=proxy_config.get('http') if proxy_config else None
            )
            
        except Exception as e:
            # 其他错误
            response_time = time.time() - start_time
            self._update_proxy_stats(proxy_config, False)
            
            error_msg = str(e)
            if "429" in error_msg or "rate limit" in error_msg.lower():
                status = "rate_limited"
                self._mark_proxy_rate_limited(proxy_config)
            elif "403" in error_msg or "SERVICE_DISABLED" in error_msg:
                status = "invalid"
            else:
                status = "error"
            
            return ValidationResult(
                key=api_key,
                status=status,
                error_message=error_msg,
                response_time=response_time,
                proxy_used=proxy_config.get('http') if proxy_config else None
            )
    
    def _get_best_proxy(self) -> Optional[Dict[str, str]]:
        """获取最佳代理（基于成功率和限流状态）"""
        if not self.proxy_pool:
            return None
        
        current_time = time.time()
        available_proxies = []
        
        for proxy_url in self.proxy_pool:
            # 检查是否在限流冷却期
            last_rate_limit = self.rate_limit_tracker.get(proxy_url, 0)
            if current_time - last_rate_limit < self.rate_limit_cooldown:
                continue
            
            # 计算代理得分
            stats = self.proxy_stats.get(proxy_url, {"success": 0, "failure": 0})
            total = stats["success"] + stats["failure"]
            
            if total == 0:
                # 新代理，给予中等优先级
                score = 0.5
            else:
                # 基于成功率计算得分
                score = stats["success"] / total
            
            available_proxies.append((score, proxy_url))
        
        if not available_proxies:
            # 所有代理都在冷却期，随机选择一个
            return {"http": random.choice(self.proxy_pool), "https": random.choice(self.proxy_pool)}
        
        # 按得分排序，选择最佳代理
        available_proxies.sort(key=lambda x: x[0], reverse=True)
        best_proxy_url = available_proxies[0][1]
        
        return {"http": best_proxy_url, "https": best_proxy_url}
    
    def _update_proxy_stats(self, proxy_config: Optional[Dict[str, str]], success: bool):
        """更新代理统计信息"""
        if not proxy_config:
            return
        
        proxy_url = proxy_config.get('http')
        if not proxy_url:
            return
        
        with self._lock:
            if proxy_url not in self.proxy_stats:
                self.proxy_stats[proxy_url] = {"success": 0, "failure": 0}
            
            if success:
                self.proxy_stats[proxy_url]["success"] += 1
            else:
                self.proxy_stats[proxy_url]["failure"] += 1
    
    def _mark_proxy_rate_limited(self, proxy_config: Optional[Dict[str, str]]):
        """标记代理被限流"""
        if not proxy_config:
            return
        
        proxy_url = proxy_config.get('http')
        if proxy_url:
            self.rate_limit_tracker[proxy_url] = time.time()
    
    def _update_stats(self, results: Dict[str, ValidationResult], total_time: float):
        """更新统计信息"""
        with self._lock:
            self.stats.total_validated += len(results)
            self.stats.total_time += total_time
            
            total_response_time = 0
            response_count = 0
            
            for result in results.values():
                if result.status == "ok":
                    self.stats.valid_keys += 1
                elif result.status == "invalid":
                    self.stats.invalid_keys += 1
                elif result.status == "rate_limited":
                    self.stats.rate_limited_keys += 1
                else:
                    self.stats.errors += 1
                
                if result.response_time:
                    total_response_time += result.response_time
                    response_count += 1
            
            if response_count > 0:
                self.stats.avg_response_time = total_response_time / response_count
    
    def get_stats(self) -> ValidationStats:
        """获取验证统计信息"""
        with self._lock:
            return ValidationStats(
                total_validated=self.stats.total_validated,
                valid_keys=self.stats.valid_keys,
                invalid_keys=self.stats.invalid_keys,
                rate_limited_keys=self.stats.rate_limited_keys,
                errors=self.stats.errors,
                total_time=self.stats.total_time,
                avg_response_time=self.stats.avg_response_time
            )
    
    def get_proxy_stats(self) -> Dict[str, Dict[str, Union[int, float]]]:
        """获取代理统计信息"""
        with self._lock:
            stats = {}
            for proxy_url, counts in self.proxy_stats.items():
                total = counts["success"] + counts["failure"]
                success_rate = counts["success"] / total if total > 0 else 0
                stats[proxy_url] = {
                    "success": counts["success"],
                    "failure": counts["failure"],
                    "total": total,
                    "success_rate": success_rate
                }
            return stats
    
    def shutdown(self):
        """关闭验证器"""
        self.executor.shutdown(wait=True)
        logger.info("🔚 ParallelKeyValidator shutdown complete")


# 为了向后兼容，创建别名
ParallelValidator = ParallelKeyValidator

# 创建全局验证器实例（可选）
parallel_validator = None

def get_parallel_validator(max_workers: int = 10) -> ParallelKeyValidator:
    """获取并行验证器实例"""
    global parallel_validator
    if parallel_validator is None:
        parallel_validator = ParallelKeyValidator(max_workers=max_workers)
    return parallel_validator