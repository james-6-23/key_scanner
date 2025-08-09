#!/usr/bin/env python3
"""
禁用监控系统并运行扫描器
避免 'by_service' 错误和其他监控相关问题
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 禁用所有监控和后台任务
os.environ['MONITORING_ENABLED'] = 'false'
os.environ['CREDENTIAL_HEALTH_CHECK_INTERVAL'] = '0'  # 禁用健康检查
os.environ['CREDENTIAL_DISCOVERY_INTERVAL'] = '0'  # 禁用自动发现
os.environ['CREDENTIAL_AUTO_HARVEST'] = 'false'  # 禁用token收集

print("=" * 60)
print("🚀 运行扫描器（已禁用监控）")
print("=" * 60)
print("\n✅ 已禁用:")
print("  - 监控仪表板")
print("  - 健康检查")
print("  - 自动发现")
print("  - Token收集")
print("\n这将避免 'by_service' 错误和后台线程问题\n")

# 导入并运行扫描器
from app.api_key_scanner_super import SuperAPIKeyScanner
from credential_manager.core.models import ServiceType
import asyncio

async def run_simple_scan():
    """运行简单扫描"""
    try:
        # 创建扫描器
        scanner = SuperAPIKeyScanner()
        
        # 检查凭证
        status = scanner.credential_manager.get_status()
        github_pool = status['pools'].get('github', {})
        
        print(f"\n📊 GitHub 池状态:")
        print(f"  总数: {github_pool.get('total', 0)}")
        print(f"  可用: {github_pool.get('available', 0)}")
        
        if github_pool.get('available', 0) == 0:
            print("\n❌ 没有可用的GitHub tokens!")
            return
        
        # 只使用一个简单查询测试
        queries = ["AIzaSy in:file language:python"]  # 只搜索Python文件
        
        print(f"\n📋 测试查询: {queries[0]}")
        print("💡 提示: 使用简单查询避免快速耗尽配额\n")
        
        # 运行扫描
        await scanner.run_scan(queries)
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n✅ 扫描完成")

if __name__ == "__main__":
    # 运行扫描
    asyncio.run(run_simple_scan())