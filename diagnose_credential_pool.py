#!/usr/bin/env python3
"""
深入诊断凭证池问题
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
print("🔍 深入诊断凭证池问题")
print("=" * 60)

# 1. 创建 CredentialBridge
config_path = os.getenv('CREDENTIAL_CONFIG_PATH', 'config/credentials.json')
credential_bridge = CredentialBridge(config_path)
credential_manager = credential_bridge.manager

print("\n📊 初始状态:")
status = credential_manager.get_status()
print(f"凭证池状态: {status}")

# 2. 检查所有凭证（不仅仅是活跃的）
print("\n🔍 检查所有存储的凭证:")
all_credentials = credential_manager.vault.list_credentials()
print(f"总凭证数: {len(all_credentials)}")

github_creds = [c for c in all_credentials if c.service_type == ServiceType.GITHUB]
print(f"GitHub 凭证数: {len(github_creds)}")

if github_creds:
    print("\n📋 GitHub 凭证详情:")
    for i, cred in enumerate(github_creds[:5]):  # 只显示前5个
        print(f"  {i+1}. {cred.masked_value}")
        print(f"     状态: {cred.status}")
        print(f"     健康度: {cred.health_score}")
        print(f"     最后使用: {cred.last_used}")
        print(f"     元数据: {cred.metadata}")

# 3. 检查凭证池的内部状态
print("\n🔧 检查凭证池内部状态:")
if hasattr(credential_manager, 'pools'):
    github_pool = credential_manager.pools.get(ServiceType.GITHUB)
    if github_pool:
        print(f"GitHub 池存在: 是")
        print(f"池中凭证数: {len(github_pool.credentials) if hasattr(github_pool, 'credentials') else '未知'}")
        if hasattr(github_pool, 'active_credentials'):
            print(f"活跃凭证数: {len(github_pool.active_credentials)}")
        if hasattr(github_pool, 'inactive_credentials'):
            print(f"非活跃凭证数: {len(github_pool.inactive_credentials)}")
    else:
        print("GitHub 池不存在！")
else:
    print("凭证管理器没有 pools 属性")

# 4. 尝试手动创建 GitHub 池
print("\n🔨 尝试手动初始化 GitHub 池:")
try:
    # 尝试通过添加一个凭证来触发池的创建
    test_token = "test_token_" + datetime.now().strftime("%Y%m%d%H%M%S")
    result = credential_manager.add_credential(
        ServiceType.GITHUB,
        test_token,
        {'source': 'diagnostic_test'}
    )
    print(f"添加测试凭证结果: {result}")
    
    # 再次检查状态
    status = credential_manager.get_status()
    github_pool_status = status['pools'].get('github', {})
    print(f"GitHub 池状态: {github_pool_status}")
    
    # 删除测试凭证
    if result:
        credential_manager.remove_credential(ServiceType.GITHUB, test_token)
        print("已删除测试凭证")
except Exception as e:
    print(f"错误: {e}")

# 5. 检查配置
print("\n⚙️ 检查配置:")
config = Config()
print(f"USE_EXTERNAL_TOKEN_FILE: {os.getenv('USE_EXTERNAL_TOKEN_FILE', 'false')}")
print(f"GITHUB_TOKENS_FILE: {os.getenv('GITHUB_TOKENS_FILE', 'github_tokens.txt')}")
print(f"TOKEN_MODE: {os.getenv('TOKEN_MODE', 'env')}")

# 6. 尝试直接从配置加载并添加 tokens
print("\n📥 尝试直接加载并添加 tokens:")
tokens = config.get_github_tokens()
print(f"从配置加载的 tokens: {len(tokens)} 个")

success_count = 0
for i, token in enumerate(tokens[:3]):  # 只测试前3个
    try:
        # 先检查是否已存在
        existing = credential_manager.vault.get_credential(ServiceType.GITHUB, token)
        if existing:
            print(f"  Token {i+1}: 已存在 (状态: {existing.status})")
            # 如果存在但不活跃，尝试激活
            if existing.status != 'active':
                existing.status = 'active'
                credential_manager.vault.update_credential(existing)
                print(f"    已激活凭证")
        else:
            # 不存在则添加
            result = credential_manager.add_credential(
                ServiceType.GITHUB,
                token,
                {'source': 'diagnostic_direct', 'index': i}
            )
            if result:
                success_count += 1
                print(f"  Token {i+1}: ✅ 添加成功")
            else:
                print(f"  Token {i+1}: ❌ 添加失败")
    except Exception as e:
        print(f"  Token {i+1}: ❌ 错误 - {e}")

print(f"\n成功添加: {success_count} 个")

# 7. 最终状态
print("\n📊 最终状态:")
status = credential_manager.get_status()
github_pool_status = status['pools'].get('github', {})
print(f"GitHub 池: 活跃={github_pool_status.get('active_count', 0)}/{github_pool_status.get('total_count', 0)}")

# 8. 测试获取凭证
print("\n🔑 测试获取凭证:")
credential = credential_manager.get_optimal_credential(service_type=ServiceType.GITHUB)
if credential:
    print(f"✅ 成功获取凭证: {credential.masked_value}")
else:
    print("❌ 无法获取凭证")

print("\n" + "=" * 60)