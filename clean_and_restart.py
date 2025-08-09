#!/usr/bin/env python3
"""
清理凭证数据库并重新启动
"""

import os
import sys
import shutil
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("🧹 清理凭证数据库并重新启动")
print("=" * 60)

# 1. 删除所有凭证数据库文件
db_files = [
    "credentials.db",
    "./data/credentials.db",
    "github_credentials.db",
    "./data/github_credentials.db"
]

print("\n📁 清理数据库文件...")
for db_file in db_files:
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
            print(f"  ✅ 删除: {db_file}")
        except Exception as e:
            print(f"  ❌ 无法删除 {db_file}: {e}")

# 2. 清理缓存目录
cache_dirs = [
    "__pycache__",
    "credential_manager/__pycache__",
    "credential_manager/core/__pycache__",
    "credential_manager/storage/__pycache__",
    "credential_manager/integration/__pycache__"
]

print("\n📁 清理缓存目录...")
for cache_dir in cache_dirs:
    if os.path.exists(cache_dir):
        try:
            shutil.rmtree(cache_dir)
            print(f"  ✅ 删除: {cache_dir}")
        except Exception as e:
            print(f"  ❌ 无法删除 {cache_dir}: {e}")

print("\n✅ 清理完成！")

# 3. 现在运行扫描器
print("\n🚀 启动扫描器...")
print("=" * 60)

try:
    from app.api_key_scanner_super import SuperAPIKeyScanner
    from credential_manager.core.models import ServiceType
    import asyncio
    from pathlib import Path
    
    # 创建扫描器实例
    scanner = SuperAPIKeyScanner()
    
    # 检查凭证状态
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
        
        # 运行扫描
        print("\n🔍 开始扫描...")
        queries_file = Path("queries.txt")
        if queries_file.exists():
            with open(queries_file, 'r') as f:
                queries = [line.strip() for line in f if line.strip() and not line.startswith('#')][:3]  # 只测试前3个查询
            
            print(f"📋 测试 {len(queries)} 个查询")
            asyncio.run(scanner.run_scan(queries))
        else:
            print("❌ queries.txt 文件不存在")
    else:
        print("❌ 仍然无法获取凭证")
        print("\n💡 可能的解决方案:")
        print("1. 确保 github_tokens.txt 文件存在并包含有效的 tokens")
        print("2. 检查环境变量配置")
        print("3. 查看日志了解详细错误信息")
        
except Exception as e:
    print(f"\n❌ 错误: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)