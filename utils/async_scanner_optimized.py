#!/usr/bin/env python3
"""
异步扫描器模块 - 优化并发性能
"""

import asyncio
import aiohttp
import time
import json
from typing import List, Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConcurrencyMode(Enum):
    """并发模式"""
    CONSERVATIVE = "conservative"  # 保守模式：低并发，稳定
    BALANCED = "balanced"          # 平衡模式：中等并发
    AGGRESSIVE = "aggressive"      # 激进模式：高并发，高性能
    ADAPTIVE = "adaptive"          # 自适应模式：动态调整

@dataclass
class ConcurrencyConfig:
    """并发配置"""
    max_concurrent_requests: int = 100
    max_concurrent_validations: int = 50
    request_timeout: float = 30.0
    validation_timeout: float = 10.0
    retry_count: int = 3
    retry_delay: float = 1.0
    batch_size: int = 100
    rate_limit: Optional[int] = None  # 每秒请求数限制
    
    @classmethod
    def from_mode(cls, mode: ConcurrencyMode) -> 'ConcurrencyConfig':
        """根据模式创建配置"""
        configs = {
            ConcurrencyMode.CONSERVATIVE: cls(
                max_concurrent_requests=20,
                max_concurrent_validations=10,
                batch_size=50,
                rate_limit=10
            ),
            ConcurrencyMode.BALANCED: cls(
                max_concurrent_requests=50,
                max_concurrent_validations=25,
                batch_size=100,
                rate_limit=50
            ),
            ConcurrencyMode.AGGRESSIVE: cls(
                max_concurrent_requests=200,
                max_concurrent_validations=100,
                batch_size=500,
                rate_limit=None
            ),
            ConcurrencyMode.ADAPTIVE: cls(
                max_concurrent_requests=100,
                max_concurrent_validations=50,
                batch_size=200,
                rate_limit=None
            )
        }
        return configs.get(mode, cls())

class RateLimiter:
    """速率限制器"""
    
    def __init__(self, rate_limit: Optional[int] = None):
        self.rate_limit = rate_limit
        self.last_request_time = 0
        self.request_count = 0
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """获取许可"""
        if not self.rate_limit:
            return
        
        async with self.lock:
            current_time = time.time()
            time_passed = current_time - self.last_request_time
            
            if time_passed >= 1.0:
                self.request_count = 0
                self.last_request_time = current_time
            
            if self.request_count >= self.rate_limit:
                sleep_time = 1.0 - time_passed
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    self.request_count = 0
                    self.last_request_time = time.time()
            
            self.request_count += 1

class AsyncScanner:
    """异步扫描器"""
    
    def __init__(self, config: Optional[ConcurrencyConfig] = None):
        self.config = config or ConcurrencyConfig()
        self.rate_limiter = RateLimiter(self.config.rate_limit)
        self.semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)
        self.validation_semaphore = asyncio.Semaphore(self.config.max_concurrent_validations)
        self.session: Optional[aiohttp.ClientSession] = None
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_validations": 0,
            "successful_validations": 0,
            "failed_validations": 0,
            "start_time": None,
            "end_time": None
        }
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        connector = aiohttp.TCPConnector(
            limit=self.config.max_concurrent_requests,
            limit_per_host=30,
            ttl_dns_cache=300
        )
        timeout = aiohttp.ClientTimeout(total=self.config.request_timeout)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        )
        self.stats["start_time"] = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
        self.stats["end_time"] = time.time()
    
    async def fetch(self, url: str, headers: Optional[Dict] = None) -> Optional[Dict]:
        """异步获取URL内容"""
        async with self.semaphore:
            await self.rate_limiter.acquire()
            
            for attempt in range(self.config.retry_count):
                try:
                    self.stats["total_requests"] += 1
                    async with self.session.get(url, headers=headers) as response:
                        if response.status == 200:
                            self.stats["successful_requests"] += 1
                            return await response.json()
                        elif response.status == 429:  # Rate limited
                            retry_after = int(response.headers.get('Retry-After', 60))
                            logger.warning(f"Rate limited, waiting {retry_after}s")
                            await asyncio.sleep(retry_after)
                        else:
                            logger.warning(f"Request failed with status {response.status}")
                except Exception as e:
                    logger.error(f"Request error: {e}")
                    if attempt < self.config.retry_count - 1:
                        await asyncio.sleep(self.config.retry_delay * (attempt + 1))
            
            self.stats["failed_requests"] += 1
            return None
    
    async def validate_key(self, key: str, validator: Callable) -> bool:
        """异步验证密钥"""
        async with self.validation_semaphore:
            try:
                self.stats["total_validations"] += 1
                # 如果validator是同步函数，在线程池中运行
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, validator, key)
                
                if result:
                    self.stats["successful_validations"] += 1
                else:
                    self.stats["failed_validations"] += 1
                
                return result
            except Exception as e:
                logger.error(f"Validation error for key {key[:10]}...: {e}")
                self.stats["failed_validations"] += 1
                return False
    
    async def batch_fetch(self, urls: List[str], headers: Optional[Dict] = None) -> List[Optional[Dict]]:
        """批量异步获取"""
        tasks = [self.fetch(url, headers) for url in urls]
        return await asyncio.gather(*tasks)
    
    async def batch_validate(self, keys: List[str], validator: Callable) -> List[bool]:
        """批量异步验证"""
        tasks = [self.validate_key(key, validator) for key in keys]
        return await asyncio.gather(*tasks)
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        if self.stats["start_time"] and self.stats["end_time"]:
            duration = self.stats["end_time"] - self.stats["start_time"]
            self.stats["duration"] = duration
            self.stats["requests_per_second"] = self.stats["total_requests"] / duration if duration > 0 else 0
            self.stats["validations_per_second"] = self.stats["total_validations"] / duration if duration > 0 else 0
        return self.stats

class AdaptiveConcurrencyManager:
    """自适应并发管理器"""
    
    def __init__(self, initial_config: Optional[ConcurrencyConfig] = None):
        self.config = initial_config or ConcurrencyConfig.from_mode(ConcurrencyMode.ADAPTIVE)
        self.performance_history = []
        self.adjustment_interval = 10  # 每10次操作调整一次
        self.operation_count = 0
    
    def adjust_concurrency(self, success_rate: float, response_time: float):
        """根据性能指标调整并发参数"""
        self.operation_count += 1
        
        if self.operation_count % self.adjustment_interval != 0:
            return
        
        # 记录性能历史
        self.performance_history.append({
            "success_rate": success_rate,
            "response_time": response_time,
            "concurrency": self.config.max_concurrent_requests
        })
        
        # 保留最近的历史记录
        if len(self.performance_history) > 100:
            self.performance_history = self.performance_history[-100:]
        
        # 自适应调整逻辑
        if success_rate > 0.95 and response_time < 1.0:
            # 性能良好，增加并发
            self.config.max_concurrent_requests = min(
                int(self.config.max_concurrent_requests * 1.2),
                500
            )
            self.config.max_concurrent_validations = min(
                int(self.config.max_concurrent_validations * 1.2),
                200
            )
            logger.info(f"Increasing concurrency to {self.config.max_concurrent_requests}")
        
        elif success_rate < 0.8 or response_time > 5.0:
            # 性能下降，减少并发
            self.config.max_concurrent_requests = max(
                int(self.config.max_concurrent_requests * 0.8),
                10
            )
            self.config.max_concurrent_validations = max(
                int(self.config.max_concurrent_validations * 0.8),
                5
            )
            logger.info(f"Decreasing concurrency to {self.config.max_concurrent_requests}")
    
    def get_optimal_config(self) -> ConcurrencyConfig:
        """获取最优配置"""
        if not self.performance_history:
            return self.config
        
        # 找出最佳性能的配置
        best_perf = max(self.performance_history, 
                       key=lambda x: x["success_rate"] / max(x["response_time"], 0.1))
        
        self.config.max_concurrent_requests = best_perf["concurrency"]
        return self.config

class AsyncBatchProcessor:
    """异步批处理器"""
    
    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
        self.queue = asyncio.Queue()
        self.results = []
        self.processing = False
    
    async def add_item(self, item: Any):
        """添加项目到队列"""
        await self.queue.put(item)
    
    async def process_batch(self, processor: Callable):
        """处理一批项目"""
        batch = []
        
        # 收集批次
        while len(batch) < self.batch_size:
            try:
                item = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                batch.append(item)
            except asyncio.TimeoutError:
                break
        
        if batch:
            # 处理批次
            results = await processor(batch)
            self.results.extend(results)
            return results
        
        return []
    
    async def start_processing(self, processor: Callable):
        """开始处理"""
        self.processing = True
        
        try:
            while self.processing or not self.queue.empty():
                await self.process_batch(processor)
        except asyncio.CancelledError:
            # 优雅处理取消
            pass
    
    def stop_processing(self):
        """停止处理"""
        self.processing = False
    
    def get_results(self) -> List:
        """获取结果"""
        return self.results

class OptimizedBatchProcessor:
    """优化的异步批处理器 - 高性能版本"""
    
    def __init__(self, batch_size: int = 100, max_workers: int = 10):
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.results = []
    
    async def process_all(self, items: List[Any], processor: Callable) -> List:
        """并行处理所有项目"""
        # 将项目分成批次
        batches = []
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            batches.append(batch)
        
        # 并行处理所有批次
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def process_with_semaphore(batch):
            async with semaphore:
                return await processor(batch)
        
        # 创建所有处理任务
        tasks = [process_with_semaphore(batch) for batch in batches]
        
        # 并行执行所有任务
        batch_results = await asyncio.gather(*tasks)
        
        # 合并结果
        for batch_result in batch_results:
            if batch_result:
                self.results.extend(batch_result)
        
        return self.results
    
    async def process_stream(self, item_generator, processor: Callable) -> List:
        """流式处理项目（适用于大数据集）"""
        batch = []
        tasks = []
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def process_with_semaphore(batch_to_process):
            async with semaphore:
                return await processor(batch_to_process)
        
        async for item in item_generator:
            batch.append(item)
            
            if len(batch) >= self.batch_size:
                # 启动批处理任务
                task = asyncio.create_task(process_with_semaphore(batch.copy()))
                tasks.append(task)
                batch.clear()
        
        # 处理剩余的项目
        if batch:
            task = asyncio.create_task(process_with_semaphore(batch))
            tasks.append(task)
        
        # 等待所有任务完成
        batch_results = await asyncio.gather(*tasks)
        
        # 合并结果
        for batch_result in batch_results:
            if batch_result:
                self.results.extend(batch_result)
        
        return self.results

# 示例：优化的GitHub搜索
async def optimized_github_search(queries: List[str], tokens: List[str]):
    """优化的GitHub搜索"""
    config = ConcurrencyConfig.from_mode(ConcurrencyMode.AGGRESSIVE)
    
    async with AsyncScanner(config) as scanner:
        # 构建搜索URL
        base_url = "https://api.github.com/search/code"
        urls = []
        headers_list = []
        
        for query in queries:
            for token in tokens:
                urls.append(f"{base_url}?q={query}")
                headers_list.append({"Authorization": f"token {token}"})
        
        # 批量搜索
        results = await scanner.batch_fetch(urls, headers_list[0])
        
        # 获取统计
        stats = scanner.get_stats()
        logger.info(f"Search completed: {stats['requests_per_second']:.1f} req/s")
        
        return results, stats

# 示例：优化的密钥验证
async def optimized_key_validation(keys: List[str], validator: Callable):
    """优化的密钥验证"""
    config = ConcurrencyConfig.from_mode(ConcurrencyMode.AGGRESSIVE)
    
    async with AsyncScanner(config) as scanner:
        # 批量验证
        results = await scanner.batch_validate(keys, validator)
        
        # 获取统计
        stats = scanner.get_stats()
        logger.info(f"Validation completed: {stats['validations_per_second']:.1f} keys/s")
        
        return results, stats

if __name__ == "__main__":
    # 测试异步扫描器
    async def test():
        # 模拟密钥验证
        def mock_validator(key):
            time.sleep(0.01)  # 模拟验证延迟
            return len(key) > 10
        
        # 生成测试密钥
        test_keys = [f"test_key_{i:05d}" for i in range(100)]
        
        # 运行优化的验证
        results, stats = await optimized_key_validation(test_keys, mock_validator)
        
        print(f"Validated {len(results)} keys")
        print(f"Success rate: {sum(results)/len(results)*100:.1f}%")
        print(f"Speed: {stats['validations_per_second']:.1f} keys/s")
    
    # 运行测试
    asyncio.run(test())