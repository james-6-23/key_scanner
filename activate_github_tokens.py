#!/usr/bin/env python3
"""
直接激活 GitHub tokens - 简单解决方案
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from common.config import Config
from common.Logger import Logger
from credential_manager.core.models import ServiceType
from app.api_key_scanner_super import SuperAPIKeyScanner

logger = Logger

print("=" * 60)
print("🔧 直接激活 GitHub Tokens")
print("=" * 60)

# 方案1：直接运行扫描器的初始化，让它正确导入 tokens
print("\n📥 初始化 SuperAPIKeyScanner...")
try:
    scanner = SuperAPIKeyScanner()
    
    # 检查凭证管理器状态
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
    else:
        print("❌ 无法获取凭证")
        
        # 方案2：强制重新加载 tokens
        print("\n🔄 尝试强制重新加载 tokens...")
        
        # 清理现有的 pending 凭证
        print("  清理 pending 凭证...")
        if hasattr(scanner.credential_manager, 'pools') and ServiceType.GITHUB in scanner.credential_manager.pools:
            github_pool_obj = scanner.credential_manager.pools[ServiceType.GITHUB]
            if hasattr(github_pool_obj, 'credentials'):
                # 清空凭证列表
                if isinstance(github_pool_obj.credentials, list):
                    github_pool_obj.credentials.clear()
                elif isinstance(github_pool_obj.credentials, dict):
                    github_pool_obj.credentials.clear()
        
        # 重新导入 tokens
        print("  重新导入 tokens...")
        config = Config()
        tokens = config.get_github_tokens()
        imported = 0
        
        for token in tokens:
            if token:
                try:
                    # 直接添加为 active 状态
                    result = scanner.credential_manager.add_credential(
                        ServiceType.GITHUB,
                        token,
                        {
                            'source': 'activate_script',
                            'status': 'active',
                            'health_score': 100.0
                        }
                    )
                    if result:
                        imported += 1
                        print(f"    ✅ 导入 token {imported}")
                except Exception as e:
                    print(f"    ❌ 导入失败: {e}")
        
        print(f"\n✅ 成功导入 {imported} 个 tokens")
        
        # 再次测试
        credential = scanner.credential_manager.get_optimal_credential(service_type=ServiceType.GITHUB)
        if credential:
            print(f"✅ 现在可以获取凭证了: {credential.masked_value}")
        else:
            print("❌ 问题仍未解决")
    
    # 显示最终状态
    print("\n📊 最终状态:")
    status = scanner.credential_manager.get_status()
    github_pool = status['pools'].get('github', {})
    print(f"  总数: {github_pool.get('total', 0)}")
    print(f"  可用: {github_pool.get('available', 0)}")
    print(f"  状态分布: {github_pool.get('status_distribution', {})}")
    
except Exception as e:
    print(f"\n❌ 错误: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)