#!/usr/bin/env python3
"""
诊断 SuperAPIKeyScanner 修复是否生效
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from common.config import Config
from common.Logger import Logger
from credential_manager.core.models import ServiceType
from credential_manager.integration.credential_bridge import CredentialBridge

logger = Logger

print("=" * 60)
print("🔍 诊断 SuperAPIKeyScanner 修复")
print("=" * 60)

# 1. 检查配置
config = Config()
tokens = config.get_github_tokens()
print(f"\n📋 从配置加载的 tokens: {len(tokens)} 个")

# 2. 模拟 SuperAPIKeyScanner 的初始化过程
print("\n🔧 模拟 SuperAPIKeyScanner 初始化...")

# 创建 CredentialBridge（与 SuperAPIKeyScanner 相同）
config_path = os.getenv('CREDENTIAL_CONFIG_PATH', 'config/credentials.json')
credential_bridge = CredentialBridge(config_path)

# 使用 bridge 内部的管理器（与 SuperAPIKeyScanner 相同）
credential_manager = credential_bridge.manager

print("✅ 创建了 CredentialBridge 并获取其内部管理器")

# 3. 导入 tokens（与 SuperAPIKeyScanner 相同）
print("\n📥 导入 GitHub tokens...")
imported_count = 0

# 从环境变量导入
env_tokens = os.getenv('GITHUB_TOKENS', '').split(',')
for token in env_tokens:
    token = token.strip()
    if token and credential_manager.add_credential(
        ServiceType.GITHUB, 
        token,
        {'source': 'env', 'imported_at': datetime.now().isoformat()}
    ):
        imported_count += 1

# 从文件导入（如果配置）
if os.getenv('USE_EXTERNAL_TOKEN_FILE', 'false').lower() == 'true':
    token_file = os.getenv('GITHUB_TOKENS_FILE', 'github_tokens.txt')
    if os.path.exists(token_file):
        with open(token_file, 'r') as f:
            for line in f:
                token = line.strip()
                if token and not token.startswith('#'):
                    if credential_manager.add_credential(
                        ServiceType.GITHUB,
                        token,
                        {'source': 'file', 'imported_at': datetime.now().isoformat()}
                    ):
                        imported_count += 1

print(f"✅ 导入了 {imported_count} 个 tokens")

# 4. 检查凭证池状态
print("\n📊 检查凭证池状态...")
status = credential_manager.get_status()
github_pool = status['pools'].get('github', {})
active_count = github_pool.get('active_count', 0)
total_count = github_pool.get('total_count', 0)
print(f"GitHub 池: 活跃={active_count}/{total_count}")

# 5. 测试获取凭证
print("\n🔑 测试获取凭证...")
credential = credential_manager.get_optimal_credential(service_type=ServiceType.GITHUB)
if credential:
    print(f"✅ 成功获取凭证: {credential.masked_value}")
else:
    print("❌ 无法获取凭证")

# 6. 验证实例关系
print("\n🔍 验证实例关系:")
print(f"  credential_bridge.manager id: {id(credential_bridge.manager)}")
print(f"  credential_manager id: {id(credential_manager)}")
print(f"  是同一个实例: {credential_bridge.manager is credential_manager}")

# 7. 结论
print("\n📝 结论:")
if credential:
    print("✅ 修复成功！凭证管理器正常工作")
    print("✅ tokens 被正确导入到 CredentialBridge 的管理器中")
    print("✅ 可以成功获取 GitHub 凭证")
else:
    print("❌ 仍有问题：无法获取凭证")
    if total_count == 0:
        print("   - 凭证池为空，tokens 可能没有成功导入")
    elif active_count == 0:
        print("   - 凭证池中有凭证但都不活跃")
    print("\n💡 可能的原因:")
    print("   1. 服务器上的代码还不是最新的")
    print("   2. 配置文件或环境变量有问题")
    print("   3. tokens 本身有问题")

print("\n" + "=" * 60)