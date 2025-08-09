#!/usr/bin/env python3
"""
修复凭证状态 - 将 pending 状态的凭证激活
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from common.config import Config
from common.Logger import Logger
from credential_manager.core.models import ServiceType, CredentialStatus
from credential_manager.integration.credential_bridge import CredentialBridge
from credential_manager.core.manager import get_credential_manager

logger = Logger

print("=" * 60)
print("🔧 修复凭证状态")
print("=" * 60)

# 1. 创建 CredentialBridge
config_path = os.getenv('CREDENTIAL_CONFIG_PATH', 'config/credentials.json')
credential_bridge = CredentialBridge(config_path)
credential_manager = credential_bridge.manager

# 2. 检查初始状态
print("\n📊 初始状态:")
status = credential_manager.get_status()
github_pool_status = status['pools'].get('github', {})
print(f"GitHub 池: 总数={github_pool_status.get('total', 0)}, 可用={github_pool_status.get('available', 0)}")
print(f"状态分布: {github_pool_status.get('status_distribution', {})}")

# 3. 激活 pending 状态的凭证
print("\n🔧 开始激活 pending 状态的凭证...")

# 获取凭证池
if hasattr(credential_manager, 'pools') and ServiceType.GITHUB in credential_manager.pools:
    github_pool = credential_manager.pools[ServiceType.GITHUB]
    
    activated_count = 0
    
    # 检查池中的所有凭证
    if hasattr(github_pool, 'credentials'):
        # 处理 credentials 可能是列表或字典的情况
        if isinstance(github_pool.credentials, dict):
            credentials_list = list(github_pool.credentials.values())
        else:
            credentials_list = github_pool.credentials
            
        for credential in credentials_list:
            if hasattr(credential, 'status') and credential.status == CredentialStatus.PENDING:
                # 激活凭证
                credential.status = CredentialStatus.ACTIVE
                credential.health_score = 100.0  # 设置健康度为满分
                credential.last_validated = datetime.now()
                
                # 更新到存储
                if hasattr(credential_manager, 'vault'):
                    credential_manager.vault.update_credential(credential)
                
                activated_count += 1
                print(f"  ✅ 激活凭证: {credential.masked_value}")
    
    # 刷新池状态
    if hasattr(github_pool, 'refresh_pool'):
        github_pool.refresh_pool()
    
    print(f"\n✅ 成功激活 {activated_count} 个凭证")
else:
    print("❌ 无法访问 GitHub 凭证池")

# 4. 检查修复后的状态
print("\n📊 修复后的状态:")
status = credential_manager.get_status()
github_pool_status = status['pools'].get('github', {})
print(f"GitHub 池: 总数={github_pool_status.get('total', 0)}, 可用={github_pool_status.get('available', 0)}")
print(f"状态分布: {github_pool_status.get('status_distribution', {})}")

# 5. 测试获取凭证
print("\n🔑 测试获取凭证:")
credential = credential_manager.get_optimal_credential(service_type=ServiceType.GITHUB)
if credential:
    print(f"✅ 成功获取凭证: {credential.masked_value}")
    print(f"   状态: {credential.status}")
    print(f"   健康度: {credential.health_score}")
else:
    print("❌ 仍然无法获取凭证")

# 6. 如果还是无法获取，尝试直接从配置重新导入
if not credential:
    print("\n🔄 尝试重新导入 tokens...")
    config = Config()
    tokens = config.get_github_tokens()
    
    success_count = 0
    for token in tokens:
        if token:
            # 先移除旧的（如果存在）
            try:
                credential_manager.remove_credential(ServiceType.GITHUB, token)
            except:
                pass
            
            # 添加新的并设置为活跃状态
            result = credential_manager.add_credential(
                ServiceType.GITHUB,
                token,
                {
                    'source': 'fix_script',
                    'imported_at': datetime.now().isoformat(),
                    'status': 'active'
                }
            )
            if result:
                success_count += 1
    
    print(f"✅ 重新导入了 {success_count} 个 tokens")
    
    # 再次测试
    credential = credential_manager.get_optimal_credential(service_type=ServiceType.GITHUB)
    if credential:
        print(f"✅ 现在可以获取凭证了: {credential.masked_value}")
    else:
        print("❌ 问题仍未解决")

print("\n" + "=" * 60)