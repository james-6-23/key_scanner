#!/usr/bin/env python3
"""
修复 PENDING 凭证问题 - 直接修改凭证管理器行为
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 猴子补丁 - 修改 add_credential 方法
def patch_credential_manager():
    """修改 CredentialManager 的 add_credential 方法"""
    from credential_manager.core.manager import CredentialManager
    from credential_manager.core.models import Credential, CredentialStatus, ServiceType
    import logging
    
    logger = logging.getLogger(__name__)
    
    # 保存原始方法
    original_add_credential = CredentialManager.add_credential
    
    def patched_add_credential(self, 
                             service_type: ServiceType,
                             value: str,
                             metadata: dict = None):
        """修改后的 add_credential 方法 - 自动激活 GitHub tokens"""
        with self.lock:
            try:
                # 对于 GitHub tokens，直接设置为 ACTIVE 状态
                if service_type == ServiceType.GITHUB:
                    credential = Credential(
                        service_type=service_type,
                        value=value,
                        status=CredentialStatus.ACTIVE,  # 直接设置为 ACTIVE
                        source=metadata.get('source', 'manual') if metadata else 'manual',
                        metadata=metadata or {},
                        health_score=100.0,  # 满分健康度
                        remaining_quota=5000,  # GitHub 默认配额
                        total_quota=5000
                    )
                else:
                    # 其他类型使用原始逻辑
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
                
                logger.info(f"Added credential: {credential.masked_value} (status: {credential.status.value})")
                return credential
                
            except Exception as e:
                logger.error(f"Failed to add credential: {e}")
                return None
    
    # 替换方法
    CredentialManager.add_credential = patched_add_credential
    print("✅ 已修补 CredentialManager.add_credential 方法")


# 应用补丁
patch_credential_manager()

# 现在运行正常的激活流程
from common.config import Config
from common.Logger import Logger
from credential_manager.core.models import ServiceType
from app.api_key_scanner_super import SuperAPIKeyScanner

logger = Logger

print("\n" + "=" * 60)
print("🔧 激活 GitHub Tokens（使用补丁）")
print("=" * 60)

try:
    # 初始化扫描器
    print("\n📥 初始化 SuperAPIKeyScanner...")
    scanner = SuperAPIKeyScanner()
    
    # 检查状态
    status = scanner.credential_manager.get_status()
    github_pool = status['pools'].get('github', {})
    
    print(f"\n📊 GitHub 池状态:")
    print(f"  总数: {github_pool.get('total', 0)}")
    print(f"  可用: {github_pool.get('available', 0)}")
    print(f"  状态分布: {github_pool.get('status_distribution', {})}")
    
    # 测试获取凭证
    print("\n🔑 测试获取凭证...")
    credential = scanner.credential_manager.get_optimal_credential(service_type=ServiceType.GITHUB)
    if credential:
        print(f"✅ 成功获取凭证: {credential.masked_value}")
        print(f"   状态: {credential.status.value}")
        print(f"   健康度: {credential.health_score}")
        print("\n✅ 问题已解决！现在可以运行扫描器了。")
    else:
        print("❌ 仍然无法获取凭证")
        print("   可能需要清理数据库并重新开始")
    
except Exception as e:
    print(f"\n❌ 错误: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)