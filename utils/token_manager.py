"""
GitHub Token Manager - 双模式Token配置和生命周期管理系统
支持：
1. 从.env文件读取逗号分隔的tokens（小规模部署）
2. 从外部txt文件读取行分隔的tokens（大规模部署）
3. 自动监控API速率限制
4. 自动移除耗尽的tokens
5. 归档无效tokens到备份文件
"""

import os
import time
import json
import threading
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from collections import deque
from pathlib import Path
import requests

from common.Logger import logger


@dataclass
class TokenStatus:
    """Token状态信息"""
    token: str
    remaining_calls: int = 5000  # GitHub默认限制
    reset_time: int = 0  # Unix时间戳
    last_used: float = 0
    total_requests: int = 0
    failed_requests: int = 0
    is_active: bool = True
    added_time: float = field(default_factory=time.time)
    
    def __post_init__(self):
        # 隐藏token中间部分用于日志
        if len(self.token) > 10:
            self.masked_token = f"{self.token[:7]}...{self.token[-4:]}"
        else:
            self.masked_token = "***"
    
    def is_rate_limited(self) -> bool:
        """检查是否被限流"""
        if self.remaining_calls <= 0:
            # 检查是否已经过了重置时间
            if time.time() >= self.reset_time:
                self.remaining_calls = 5000  # 重置
                return False
            return True
        return False
    
    def update_from_headers(self, headers: Dict[str, str]) -> None:
        """从GitHub响应头更新状态"""
        if 'X-RateLimit-Remaining' in headers:
            self.remaining_calls = int(headers['X-RateLimit-Remaining'])
        if 'X-RateLimit-Reset' in headers:
            self.reset_time = int(headers['X-RateLimit-Reset'])
        self.last_used = time.time()


class TokenManager:
    """GitHub Token管理器"""
    
    def __init__(self, 
                 env_tokens: Optional[str] = None,
                 tokens_file: Optional[str] = None,
                 use_external_file: bool = False,
                 archive_dir: str = "./data/archived_tokens",
                 auto_remove_exhausted: bool = True,
                 min_remaining_calls: int = 10):
        """
        初始化Token管理器
        
        Args:
            env_tokens: 从环境变量读取的逗号分隔tokens
            tokens_file: 外部tokens文件路径
            use_external_file: 是否使用外部文件模式
            archive_dir: 归档目录
            auto_remove_exhausted: 是否自动移除耗尽的tokens
            min_remaining_calls: 最小剩余调用次数阈值
        """
        self.tokens: Dict[str, TokenStatus] = {}
        self.token_queue: deque = deque()
        self.archive_dir = Path(archive_dir)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self.auto_remove_exhausted = auto_remove_exhausted
        self.min_remaining_calls = min_remaining_calls
        self.lock = threading.Lock()
        self.stats_file = self.archive_dir / "token_stats.json"
        
        # 加载tokens
        self._load_tokens(env_tokens, tokens_file, use_external_file)
        
        # 加载历史统计
        self._load_stats()
        
        # 启动监控线程
        self.monitor_thread = threading.Thread(target=self._monitor_tokens, daemon=True)
        self.monitor_thread.start()
        
        logger.info(f"🔑 TokenManager initialized with {len(self.tokens)} tokens")
    
    def _load_tokens(self, env_tokens: Optional[str], 
                     tokens_file: Optional[str], 
                     use_external_file: bool) -> None:
        """加载tokens"""
        loaded_tokens = []
        
        if use_external_file and tokens_file and os.path.exists(tokens_file):
            # 模式1：从外部文件加载
            logger.info(f"📂 Loading tokens from external file: {tokens_file}")
            try:
                with open(tokens_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        token = line.strip()
                        if token and not token.startswith('#') and self._validate_token_format(token):
                            loaded_tokens.append(token)
                logger.info(f"✅ Loaded {len(loaded_tokens)} tokens from file")
            except Exception as e:
                logger.error(f"❌ Failed to load tokens from file: {e}")
        
        elif env_tokens:
            # 模式2：从环境变量加载（逗号分隔）
            logger.info("🔧 Loading tokens from environment variable")
            for token in env_tokens.split(','):
                token = token.strip()
                if token and self._validate_token_format(token):
                    loaded_tokens.append(token)
            logger.info(f"✅ Loaded {len(loaded_tokens)} tokens from env")
        
        # 初始化token状态
        for token in loaded_tokens:
            if token not in self.tokens:
                self.tokens[token] = TokenStatus(token=token)
                self.token_queue.append(token)
    
    def _validate_token_format(self, token: str) -> bool:
        """验证token格式"""
        # GitHub token格式验证
        if not token:
            return False
        
        # 支持多种token格式：
        # 1. 经典token格式：40个字符的十六进制
        # 2. 新token格式：ghp_ 开头
        # 3. GitHub PAT v2格式：github_pat_ 开头
        if token.startswith('ghp_') and len(token) > 10:
            return True
        if token.startswith('github_pat_') and len(token) > 20:
            return True
        if len(token) == 40 and all(c in '0123456789abcdef' for c in token.lower()):
            return True
        
        logger.warning(f"⚠️ Invalid token format: {token[:10]}...")
        return False
    
    def get_next_token(self) -> Optional[Tuple[str, TokenStatus]]:
        """
        获取下一个可用的token
        
        Returns:
            (token, status) 或 None
        """
        with self.lock:
            attempts = 0
            max_attempts = len(self.token_queue)
            
            while attempts < max_attempts:
                if not self.token_queue:
                    logger.error("❌ No tokens available in queue")
                    return None
                
                # 轮换到下一个token
                token = self.token_queue.popleft()
                self.token_queue.append(token)
                
                if token not in self.tokens:
                    attempts += 1
                    continue
                
                status = self.tokens[token]
                
                # 检查token是否可用
                if not status.is_active:
                    attempts += 1
                    continue
                
                # 检查是否被限流
                if status.is_rate_limited():
                    reset_time = datetime.fromtimestamp(status.reset_time).strftime('%H:%M:%S')
                    logger.debug(f"⏳ Token {status.masked_token} rate limited until {reset_time}")
                    attempts += 1
                    continue
                
                # 检查剩余调用次数
                if status.remaining_calls < self.min_remaining_calls:
                    logger.warning(f"⚠️ Token {status.masked_token} has low remaining calls: {status.remaining_calls}")
                    if self.auto_remove_exhausted:
                        self._archive_token(token, "exhausted")
                        attempts += 1
                        continue
                
                status.total_requests += 1
                return token, status
                
                attempts += 1
            
            logger.error("❌ All tokens are exhausted or rate limited")
            return None
    
    def update_token_status(self, token: str, headers: Dict[str, str], 
                          success: bool = True) -> None:
        """
        更新token状态
        
        Args:
            token: token字符串
            headers: GitHub API响应头
            success: 请求是否成功
        """
        with self.lock:
            if token in self.tokens:
                status = self.tokens[token]
                status.update_from_headers(headers)
                
                if not success:
                    status.failed_requests += 1
                    
                    # 连续失败过多，标记为无效
                    if status.failed_requests > 10:
                        logger.warning(f"⚠️ Token {status.masked_token} has too many failures, archiving")
                        self._archive_token(token, "invalid")
                
                # 记录低剩余次数警告
                if status.remaining_calls < 100:
                    logger.warning(f"⚠️ Token {status.masked_token} low on calls: {status.remaining_calls} remaining")
    
    def _archive_token(self, token: str, reason: str) -> None:
        """
        归档token
        
        Args:
            token: 要归档的token
            reason: 归档原因
        """
        if token not in self.tokens:
            return
        
        status = self.tokens[token]
        status.is_active = False
        
        # 从队列中移除
        try:
            self.token_queue.remove(token)
        except ValueError:
            pass
        
        # 写入归档文件
        archive_file = self.archive_dir / f"archived_tokens_{datetime.now().strftime('%Y%m%d')}.txt"
        
        try:
            with open(archive_file, 'a', encoding='utf-8') as f:
                archive_entry = {
                    "token": status.masked_token,
                    "reason": reason,
                    "timestamp": datetime.now().isoformat(),
                    "total_requests": status.total_requests,
                    "failed_requests": status.failed_requests,
                    "last_remaining": status.remaining_calls
                }
                f.write(json.dumps(archive_entry) + '\n')
            
            logger.info(f"📦 Archived token {status.masked_token} (reason: {reason})")
        except Exception as e:
            logger.error(f"❌ Failed to archive token: {e}")
        
        # 从活动tokens中移除
        del self.tokens[token]
    
    def _monitor_tokens(self) -> None:
        """监控token状态（后台线程）"""
        while True:
            try:
                time.sleep(60)  # 每分钟检查一次
                
                with self.lock:
                    active_count = sum(1 for s in self.tokens.values() if s.is_active)
                    total_remaining = sum(s.remaining_calls for s in self.tokens.values() if s.is_active)
                    
                    if active_count == 0:
                        logger.error("❌ No active tokens available!")
                    elif active_count < 3:
                        logger.warning(f"⚠️ Only {active_count} active tokens remaining")
                    
                    # 保存统计信息
                    self._save_stats()
                    
                    # 检查并重新激活已重置的tokens
                    current_time = time.time()
                    for token, status in list(self.tokens.items()):
                        if not status.is_active and status.reset_time < current_time:
                            status.is_active = True
                            status.remaining_calls = 5000
                            if token not in self.token_queue:
                                self.token_queue.append(token)
                            logger.info(f"♻️ Reactivated token {status.masked_token}")
                    
            except Exception as e:
                logger.error(f"❌ Monitor thread error: {e}")
    
    def _save_stats(self) -> None:
        """保存统计信息"""
        try:
            stats = {
                "timestamp": datetime.now().isoformat(),
                "active_tokens": len([s for s in self.tokens.values() if s.is_active]),
                "total_tokens": len(self.tokens),
                "total_requests": sum(s.total_requests for s in self.tokens.values()),
                "total_failures": sum(s.failed_requests for s in self.tokens.values()),
                "tokens": [
                    {
                        "masked": s.masked_token,
                        "remaining": s.remaining_calls,
                        "requests": s.total_requests,
                        "failures": s.failed_requests,
                        "active": s.is_active
                    }
                    for s in self.tokens.values()
                ]
            }
            
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save stats: {e}")
    
    def _load_stats(self) -> None:
        """加载历史统计信息"""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
                    logger.info(f"📊 Loaded stats from {stats.get('timestamp', 'unknown')}")
            except Exception as e:
                logger.debug(f"Could not load stats: {e}")
    
    def add_token(self, token: str) -> bool:
        """
        动态添加新token
        
        Args:
            token: 新的token
            
        Returns:
            是否添加成功
        """
        if not self._validate_token_format(token):
            return False
        
        with self.lock:
            if token not in self.tokens:
                self.tokens[token] = TokenStatus(token=token)
                self.token_queue.append(token)
                logger.info(f"➕ Added new token {self.tokens[token].masked_token}")
                return True
            return False
    
    def remove_token(self, token: str, reason: str = "manual") -> bool:
        """
        手动移除token
        
        Args:
            token: 要移除的token
            reason: 移除原因
            
        Returns:
            是否移除成功
        """
        with self.lock:
            if token in self.tokens:
                self._archive_token(token, reason)
                return True
            return False
    
    def get_status_summary(self) -> Dict[str, Any]:
        """获取状态摘要"""
        with self.lock:
            active_tokens = [s for s in self.tokens.values() if s.is_active]
            return {
                "total_tokens": len(self.tokens),
                "active_tokens": len(active_tokens),
                "total_remaining_calls": sum(s.remaining_calls for s in active_tokens),
                "total_requests": sum(s.total_requests for s in self.tokens.values()),
                "total_failures": sum(s.failed_requests for s in self.tokens.values()),
                "tokens": [
                    {
                        "token": s.masked_token,
                        "remaining": s.remaining_calls,
                        "active": s.is_active,
                        "requests": s.total_requests,
                        "failures": s.failed_requests
                    }
                    for s in self.tokens.values()
                ]
            }
    
    def validate_token_with_github(self, token: str) -> bool:
        """
        通过GitHub API验证token有效性
        
        Args:
            token: 要验证的token
            
        Returns:
            token是否有效
        """
        try:
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            }
            response = requests.get("https://api.github.com/user", headers=headers, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"✅ Token validation successful")
                return True
            elif response.status_code == 401:
                logger.warning(f"❌ Token validation failed: unauthorized")
                return False
            else:
                logger.warning(f"⚠️ Token validation returned status: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Token validation error: {e}")
            return False


# 全局Token管理器实例
_token_manager: Optional[TokenManager] = None


def get_token_manager() -> TokenManager:
    """获取全局Token管理器实例"""
    global _token_manager
    if _token_manager is None:
        raise RuntimeError("TokenManager not initialized. Call init_token_manager() first.")
    return _token_manager


def init_token_manager(env_tokens: Optional[str] = None,
                       tokens_file: Optional[str] = None,
                       use_external_file: bool = False,
                       **kwargs) -> TokenManager:
    """
    初始化全局Token管理器
    
    Args:
        env_tokens: 环境变量中的tokens
        tokens_file: 外部tokens文件路径
        use_external_file: 是否使用外部文件模式
        **kwargs: 其他TokenManager参数
        
    Returns:
        TokenManager实例
    """
    global _token_manager
    _token_manager = TokenManager(env_tokens, tokens_file, use_external_file, **kwargs)
    return _token_manager