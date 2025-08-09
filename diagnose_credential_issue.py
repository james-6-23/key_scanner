#!/usr/bin/env python3
"""
诊断凭证管理器问题
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from common.config import Config
from credential_manager.core.manager import get_credential_manager
from credential_manager.core.models import ServiceType
from credential_manager.integration.credential_bridge import CredentialBridge

print("=" * 60)
print("🔍 诊断凭证管理器问题")
print("=" * 60)

# 1. 检查配置
config = Config()
tokens = config.get_github_tokens()
print(f"\n📋 从配置加载的 tokens: {len(tokens)} 个")

# 2. 创建凭证管理器（模拟 SuperAPIKeyScanner 的行为）
credential_config = {
    'encryption_enabled': os.getenv('CREDENTIAL_ENCRYPTION_ENABLED', 'true').lower() == 'true',
    'balancing_strategy': os.getenv('CREDENTIAL_BALANCING_STRATEGY', 'quota_aware'),
    'min_pool_size': int(os.getenv('CREDENTIAL_MIN_POOL_SIZE', '10')),
    'max_pool_size': int(os.getenv('CREDENTIAL_MAX_POOL_SIZE', '100')),
    'health_check_interval': int(os.getenv('CREDENTIAL_HEALTH_CHECK_INTERVAL', '60')),
    'discovery_interval': int(os.getenv('CREDENTIAL_DISCOVERY_INTERVAL', '300')),
    'harvesting_enabled': os.getenv('CREDENTIAL_AUTO_HARVEST', 'false').lower() == 'true'
}

# 创建第一个管理器实例
manager1 = get_credential_manager(credential_config)
print(f"\n🔧 创建了第一个 CredentialManager 实例")

# 导入 tokens 到第一个管理器
imported_count = 0
for token in tokens:
    if token and manager1.add_credential(
        ServiceType.GITHUB, 
        token,
        {'source': 'test', 'imported_at': 'now'}
    ):
        imported_count += 1

print(f"📥 导入了 {imported_count} 个 tokens 到第一个管理器")

# 检查第一个管理器的状态
status1 = manager1.get_status()
github_pool1 = status1['pools'].get('github', {})
print(f"📊 第一个管理器 GitHub 池: 活跃={github_pool1.get('active_count', 0)}/{github_pool1.get('total', 0)}")

# 创建 CredentialBridge（它会创建自己的管理器）
config_path = os.getenv('CREDENTIAL_CONFIG_PATH', 'config/credentials.json')
bridge = CredentialBridge(config_path)
print(f"\n🌉 创建了 CredentialBridge（包含第二个管理器）")

# 检查 bridge 内部管理器的状态
status2 = bridge.manager.get_status()
github_pool2 = status2['pools'].get('github', {})
print(f"📊 Bridge 内部管理器 GitHub 池: 活跃={github_pool2.get('active_count', 0)}/{github_pool2.get('total', 0)}")

# 测试从 bridge 获取凭证
print("\n🔑 尝试从 Bridge 获取凭证...")
credential = bridge.manager.get_optimal_credential(service_type=ServiceType.GITHUB)
if credential:
    print(f"✅ 成功获取凭证: {credential.masked_value}")
else:
    print("❌ 无法获取凭证")

# 检查是否是同一个实例
print(f"\n🔍 管理器实例检查:")
print(f"  manager1 id: {id(manager1)}")
print(f"  bridge.manager id: {id(bridge.manager)}")
print(f"  是同一个实例: {manager1 is bridge.manager}")

# 解决方案
print("\n💡 解决方案:")
print("1. SuperAPIKeyScanner 应该只使用 CredentialBridge，不要单独创建 CredentialManager")
print("2. 或者将 tokens 导入到 CredentialBridge 的管理器中")
print("3. 或者让 CredentialBridge 使用传入的 CredentialManager 实例")

print("\n" + "=" * 60)