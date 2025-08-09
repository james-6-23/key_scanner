"""
凭证管理系统与现有系统的集成桥接器
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from datetime import datetime
import asyncio
from dataclasses import asdict

# 导入核心模块
from ..core.models import (
    Credential, 
    CredentialStatus, 
    ServiceType,
    CredentialMetrics
)
from ..core.manager import CredentialManager
from ..storage.vault import CredentialVault
from ..balancer.strategies import get_strategy
from ..healing.health_check import HealthChecker, SelfHealingEngine
from ..discovery.discovery import (
    CredentialDiscoveryEngine,
    FileScanner,
    EnvironmentScanner,
    CodeScanner
)

logger = logging.getLogger(__name__)


class TokenManagerAdapter:
    """
    适配器：将新的CredentialManager适配到旧的TokenManager接口
    保持向后兼容性
    """
    
    def __init__(self, credential_manager: CredentialManager):
        """
        初始化适配器
        
        Args:
            credential_manager: 新的凭证管理器实例
        """
        self.credential_manager = credential_manager
        self._token_mapping = {}  # 旧token到新credential的映射
        
    def get_token(self) -> Optional[str]:
        """
        获取一个可用的token（兼容旧接口）
        
        Returns:
            Token字符串或None
        """
        credential = self.credential_manager.get_optimal_credential(
            service_type=ServiceType.GITHUB
        )
        
        if credential:
            self._token_mapping[credential.value] = credential.id
            return credential.value
        return None
        
    def mark_token_used(self, token: str, success: bool = True):
        """
        标记token已使用（兼容旧接口）
        
        Args:
            token: Token字符串
            success: 是否成功
        """
        credential_id = self._token_mapping.get(token)
        if credential_id:
            if success:
                self.credential_manager.update_credential_status(
                    credential_id,
                    CredentialStatus.ACTIVE
                )
            else:
                self.credential_manager.update_credential_status(
                    credential_id,
                    CredentialStatus.DEGRADED
                )
                
    def add_token(self, token: str):
        """
        添加新token（兼容旧接口）
        
        Args:
            token: Token字符串
        """
        self.credential_manager.add_credential(
            value=token,
            service_type=ServiceType.GITHUB
        )
        
    def remove_token(self, token: str):
        """
        移除token（兼容旧接口）
        
        Args:
            token: Token字符串
        """
        credential_id = self._token_mapping.get(token)
        if credential_id:
            self.credential_manager.remove_credential(credential_id)
            del self._token_mapping[token]
            
    def get_all_tokens(self) -> List[str]:
        """
        获取所有tokens（兼容旧接口）
        
        Returns:
            Token列表
        """
        credentials = self.credential_manager.list_credentials(
            service_type=ServiceType.GITHUB
        )
        return [cred.value for cred in credentials]
        
    def get_token_stats(self) -> Dict[str, Any]:
        """
        获取token统计信息（兼容旧接口）
        
        Returns:
            统计信息字典
        """
        stats = self.credential_manager.get_statistics()
        
        # 转换为旧格式
        return {
            'total_tokens': stats['total_credentials'],
            'active_tokens': stats['by_status'].get('active', 0),
            'exhausted_tokens': stats['by_status'].get('exhausted', 0),
            'rate_limited_tokens': stats['by_status'].get('rate_limited', 0)
        }


class CredentialBridge:
    """
    凭证管理系统主桥接器
    提供统一的接口来集成新系统
    """
    
    def __init__(self, 
                 config_path: Optional[str] = None,
                 auto_discover: bool = True,
                 enable_healing: bool = True):
        """
        初始化桥接器
        
        Args:
            config_path: 配置文件路径
            auto_discover: 是否自动发现凭证
            enable_healing: 是否启用自愈
        """
        self.config = self._load_config(config_path)
        
        # 初始化组件
        self.vault = CredentialVault(
            db_path=self.config.get('vault_db_path', 'credentials.db')
        )
        
        # 创建配置字典传递给CredentialManager
        manager_config = {
            'encryption_enabled': self.config.get('encryption_enabled', True),
            'balancing_strategy': self.config.get('balancing_strategy', 'quota_aware'),
            'health_check_interval': self.config.get('health_check_interval', 60),
            'min_pool_size': self.config.get('min_pool_size', 10),
            'max_pool_size': self.config.get('max_pool_size', 100),
            'discovery_enabled': self.config.get('discovery_enabled', True),
            'discovery_interval': self.config.get('discovery_interval', 300),
            'harvesting_enabled': self.config.get('harvesting_enabled', False)
        }
        
        self.manager = CredentialManager(manager_config)
        
        self.health_checker = HealthChecker(
            check_interval=self.config.get('health_check_interval', 60)
        )
        
        if enable_healing:
            self.healing_engine = SelfHealingEngine(self.health_checker)
        else:
            self.healing_engine = None
            
        # 创建适配器
        self.token_adapter = TokenManagerAdapter(self.manager)
        
        # 自动发现
        if auto_discover:
            self._auto_discover_credentials()
            
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """加载配置"""
        default_config = {
            'vault_db_path': 'credentials.db',
            'balancing_strategy': 'quota_aware',
            'health_check_interval': 60,
            'discovery_paths': ['.', './config', './secrets'],
            'auto_import_threshold': 0.8
        }
        
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                
        return default_config
        
    def _auto_discover_credentials(self):
        """自动发现并导入凭证"""
        logger.info("Starting automatic credential discovery...")
        
        discovery_engine = CredentialDiscoveryEngine()
        
        # 添加扫描器
        discovery_engine.add_scanner(
            FileScanner(paths=self.config.get('discovery_paths', ['.']))
        )
        discovery_engine.add_scanner(EnvironmentScanner())
        
        # 执行发现
        discovered = discovery_engine.discover()
        
        # 导入高置信度凭证
        threshold = self.config.get('auto_import_threshold', 0.8)
        imported_count = 0
        
        for cred in discovered:
            if cred.confidence >= threshold:
                try:
                    # 确定服务类型
                    service_type = self._determine_service_type(cred.service_type)
                    
                    # 添加到管理器
                    self.manager.add_credential(
                        service_type=service_type,
                        value=cred.value,
                        metadata={
                            'source': cred.source,
                            'discovered_at': cred.discovered_at.isoformat(),
                            'confidence': cred.confidence
                        }
                    )
                    imported_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to import credential: {e}")
                    
        logger.info(f"Imported {imported_count} credentials from discovery")
        
    def _determine_service_type(self, type_hint: Optional[str]) -> ServiceType:
        """确定服务类型"""
        if not type_hint:
            return ServiceType.GENERIC
            
        type_mapping = {
            'github': ServiceType.GITHUB,
            'openai': ServiceType.OPENAI,
            'aws': ServiceType.AWS,
            'azure': ServiceType.AZURE,
            'gcp': ServiceType.GCP
        }
        
        for key, service_type in type_mapping.items():
            if key in type_hint.lower():
                return service_type
                
        return ServiceType.GENERIC
        
    async def initialize(self):
        """异步初始化"""
        # 启动健康监控
        if self.healing_engine:
            self.health_checker.start_monitoring(
                lambda: self.manager.list_credentials()
            )
            
        logger.info("Credential Bridge initialized")
        
    async def shutdown(self):
        """关闭桥接器"""
        # 停止健康监控
        if self.health_checker:
            self.health_checker.stop_monitoring()
            
        # 保存状态
        self.manager.save_state()
        
        logger.info("Credential Bridge shutdown")
        
    def get_credential(self, 
                      service_type: Optional[Union[str, ServiceType]] = None,
                      strategy: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        获取最优凭证
        
        Args:
            service_type: 服务类型
            strategy: 负载均衡策略
            
        Returns:
            凭证信息字典
        """
        if isinstance(service_type, str):
            service_type = ServiceType[service_type.upper()]
            
        credential = self.manager.get_optimal_credential(
            service_type=service_type,
            strategy=strategy
        )
        
        if credential:
            return {
                'id': credential.id,
                'value': credential.value,
                'masked_value': credential.masked_value,
                'service_type': credential.service_type.value,
                'status': credential.status.value,
                'health_score': credential.calculate_health_score()
            }
            
        return None
        
    def add_credential_from_file(self, file_path: str) -> int:
        """
        从文件导入凭证
        
        Args:
            file_path: 文件路径
            
        Returns:
            导入的凭证数量
        """
        imported = 0
        
        try:
            # 使用文件扫描器
            scanner = FileScanner([file_path])
            discovered = scanner.scan()
            
            for cred in discovered:
                if cred.confidence >= 0.5:  # 较低的阈值
                    service_type = self._determine_service_type(cred.service_type)
                    self.manager.add_credential(
                        service_type=service_type,
                        value=cred.value
                    )
                    imported += 1
                    
        except Exception as e:
            logger.error(f"Failed to import from file: {e}")
            
        return imported
        
    def export_credentials(self, output_path: str, include_values: bool = False):
        """
        导出凭证
        
        Args:
            output_path: 输出路径
            include_values: 是否包含实际值（危险！）
        """
        credentials = self.manager.list_credentials()
        
        export_data = {
            'export_time': datetime.now().isoformat(),
            'total_credentials': len(credentials),
            'credentials': []
        }
        
        for cred in credentials:
            cred_data = {
                'id': cred.id,
                'service_type': cred.service_type.value,
                'status': cred.status.value,
                'health_score': cred.calculate_health_score(),
                'created_at': cred.created_at.isoformat(),
                'last_used': cred.last_used.isoformat() if cred.last_used else None
            }
            
            if include_values:
                cred_data['value'] = cred.value
            else:
                cred_data['masked_value'] = cred.masked_value
                
            export_data['credentials'].append(cred_data)
            
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
            
        logger.info(f"Exported {len(credentials)} credentials to {output_path}")
        
    def get_health_report(self) -> Dict[str, Any]:
        """获取健康报告"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'credentials': []
        }
        
        for cred in self.manager.list_credentials():
            health_result = self.health_checker.check_credential(cred)
            
            report['credentials'].append({
                'id': cred.id,
                'masked_value': cred.masked_value,
                'health_status': health_result.status.value,
                'health_score': health_result.score,
                'issues': health_result.issues,
                'recommendations': health_result.recommendations
            })
            
        # 添加汇总统计
        report['summary'] = {
            'total': len(report['credentials']),
            'healthy': sum(1 for c in report['credentials'] if c['health_status'] == 'healthy'),
            'degraded': sum(1 for c in report['credentials'] if c['health_status'] == 'degraded'),
            'unhealthy': sum(1 for c in report['credentials'] if c['health_status'] == 'unhealthy'),
            'critical': sum(1 for c in report['credentials'] if c['health_status'] == 'critical')
        }
        
        return report
        
    async def perform_healing(self) -> Dict[str, Any]:
        """执行自愈"""
        if not self.healing_engine:
            return {'error': 'Healing engine not enabled'}
            
        healing_results = {
            'timestamp': datetime.now().isoformat(),
            'actions': []
        }
        
        for cred in self.manager.list_credentials():
            actions = await self.healing_engine.diagnose_and_heal(cred, self.manager)
            
            for action in actions:
                healing_results['actions'].append({
                    'credential_id': action.credential_id,
                    'action_type': action.action_type,
                    'description': action.description,
                    'success': action.success,
                    'result': action.result
                })
                
        healing_results['summary'] = {
            'total_actions': len(healing_results['actions']),
            'successful': sum(1 for a in healing_results['actions'] if a['success'])
        }
        
        return healing_results


class GitHubTokenBridge:
    """
    专门用于GitHub Token的桥接器
    与现有的github_tokens.txt文件集成
    """
    
    def __init__(self, 
                 tokens_file: str = 'github_tokens.txt',
                 credential_manager: Optional[CredentialManager] = None):
        """
        初始化GitHub Token桥接器
        
        Args:
            tokens_file: Token文件路径
            credential_manager: 凭证管理器实例
        """
        self.tokens_file = Path(tokens_file)
        self.credential_manager = credential_manager or self._create_default_manager()
        
        # 加载现有tokens
        self._load_tokens_from_file()
        
    def _create_default_manager(self) -> CredentialManager:
        """创建默认管理器"""
        config = {
            'encryption_enabled': True,
            'balancing_strategy': 'quota_aware',
            'vault_db_path': 'github_credentials.db'
        }
        return CredentialManager(config)
        
    def _load_tokens_from_file(self):
        """从文件加载tokens"""
        if not self.tokens_file.exists():
            logger.warning(f"Tokens file not found: {self.tokens_file}")
            return
            
        try:
            with open(self.tokens_file, 'r') as f:
                for line in f:
                    token = line.strip()
                    if token and not token.startswith('#'):
                        self.credential_manager.add_credential(
                            service_type=ServiceType.GITHUB,
                            value=token
                        )
                        
            logger.info(f"Loaded tokens from {self.tokens_file}")
            
        except Exception as e:
            logger.error(f"Failed to load tokens: {e}")
            
    def sync_to_file(self):
        """同步凭证到文件"""
        try:
            credentials = self.credential_manager.list_credentials(
                service_type=ServiceType.GITHUB
            )
            
            # 只写入活跃的凭证
            active_tokens = [
                cred.value for cred in credentials
                if cred.status == CredentialStatus.ACTIVE
            ]
            
            with open(self.tokens_file, 'w') as f:
                f.write('\n'.join(active_tokens))
                
            logger.info(f"Synced {len(active_tokens)} tokens to {self.tokens_file}")
            
        except Exception as e:
            logger.error(f"Failed to sync tokens: {e}")
            
    def get_next_token(self) -> Optional[str]:
        """获取下一个可用token"""
        credential = self.credential_manager.get_optimal_credential(
            service_type=ServiceType.GITHUB
        )
        return credential.value if credential else None
        
    def mark_token_exhausted(self, token: str):
        """标记token已耗尽"""
        # 查找对应的凭证
        credentials = self.credential_manager.list_credentials(
            service_type=ServiceType.GITHUB
        )
        
        for cred in credentials:
            if cred.value == token:
                self.credential_manager.update_credential_status(
                    cred.id,
                    CredentialStatus.EXHAUSTED
                )
                break
                
    def add_new_token(self, token: str) -> bool:
        """添加新token"""
        try:
            self.credential_manager.add_credential(
                service_type=ServiceType.GITHUB,
                value=token
            )
            
            # 同步到文件
            self.sync_to_file()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add token: {e}")
            return False
            
    def remove_invalid_tokens(self):
        """移除无效tokens"""
        credentials = self.credential_manager.list_credentials(
            service_type=ServiceType.GITHUB
        )
        
        removed_count = 0
        for cred in credentials:
            if cred.status in [CredentialStatus.INVALID, CredentialStatus.REVOKED]:
                self.credential_manager.remove_credential(cred.id)
                removed_count += 1
                
        if removed_count > 0:
            self.sync_to_file()
            logger.info(f"Removed {removed_count} invalid tokens")
            
    def get_status(self) -> Dict[str, Any]:
        """获取状态信息"""
        stats = self.credential_manager.get_statistics()
        
        return {
            'total_tokens': stats['total_credentials'],
            'active': stats['by_status'].get('active', 0),
            'exhausted': stats['by_status'].get('exhausted', 0),
            'rate_limited': stats['by_status'].get('rate_limited', 0),
            'invalid': stats['by_status'].get('invalid', 0),
            'average_health': stats['average_health_score']
        }


# 便捷函数
def create_bridge_from_env() -> CredentialBridge:
    """从环境变量创建桥接器"""
    config = {
        'vault_db_path': os.getenv('CREDENTIAL_VAULT_DB', 'credentials.db'),
        'balancing_strategy': os.getenv('CREDENTIAL_STRATEGY', 'quota_aware'),
        'health_check_interval': int(os.getenv('HEALTH_CHECK_INTERVAL', '60')),
        'auto_import_threshold': float(os.getenv('AUTO_IMPORT_THRESHOLD', '0.8'))
    }
    
    return CredentialBridge(
        config_path=os.getenv('CREDENTIAL_CONFIG_PATH'),
        auto_discover=os.getenv('AUTO_DISCOVER', 'true').lower() == 'true',
        enable_healing=os.getenv('ENABLE_HEALING', 'true').lower() == 'true'
    )


def migrate_from_token_manager(old_token_file: str, bridge: CredentialBridge) -> int:
    """
    从旧的token管理器迁移
    
    Args:
        old_token_file: 旧的token文件路径
        bridge: 凭证桥接器实例
        
    Returns:
        迁移的token数量
    """
    migrated = 0
    
    try:
        with open(old_token_file, 'r') as f:
            for line in f:
                token = line.strip()
                if token and not token.startswith('#'):
                    bridge.manager.add_credential(
                        service_type=ServiceType.GITHUB,
                        value=token,
                        metadata={'migrated_from': old_token_file}
                    )
                    migrated += 1
                    
        logger.info(f"Migrated {migrated} tokens from {old_token_file}")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        
    return migrated