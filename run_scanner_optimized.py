#!/usr/bin/env python3
"""
优化版扫描器运行脚本
- 更好的速率限制处理
- 优雅关闭
- 错误恢复
"""

import os
import sys
import asyncio
import signal
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from app.api_key_scanner_super import SuperAPIKeyScanner
from common.Logger import Logger

logger = Logger

# 全局扫描器实例
scanner = None

def signal_handler(signum, frame):
    """处理关闭信号"""
    global scanner
    logger.info(f"\n⚠️ 收到信号 {signum}，正在优雅关闭...")
    if scanner:
        scanner.shutdown()
    sys.exit(0)

async def run_optimized_scan():
    """运行优化的扫描"""
    global scanner
    
    print("=" * 60)
    print("🚀 优化版API密钥扫描器")
    print("=" * 60)
    
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 创建扫描器
        scanner = SuperAPIKeyScanner()
        
        # 检查凭证状态
        status = scanner.credential_manager.get_status()
        github_pool = status['pools'].get('github', {})
        
        print(f"\n📊 GitHub 池状态:")
        print(f"  总数: {github_pool.get('total', 0)}")
        print(f"  可用: {github_pool.get('available', 0)}")
        
        if github_pool.get('available', 0) == 0:
            print("\n❌ 没有可用的GitHub tokens!")
            print("请检查:")
            print("1. github_tokens.txt 文件是否存在")
            print("2. tokens 是否有效")
            print("3. 环境变量 GITHUB_TOKENS 是否设置")
            return
        
        # 加载查询（只使用前5个测试）
        queries_file = Path("queries.txt")
        if not queries_file.exists():
            logger.error("❌ queries.txt 文件不存在")
            return
        
        with open(queries_file, 'r') as f:
            all_queries = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        # 限制查询数量避免快速耗尽tokens
        queries = all_queries[:5]  # 只使用前5个查询
        
        print(f"\n📋 测试扫描 {len(queries)} 个查询")
        print("💡 提示: 使用较少的查询以避免快速耗尽API配额")
        
        # 运行扫描
        await scanner.run_scan(queries)
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if scanner:
            scanner.shutdown()
        print("\n✅ 扫描器已关闭")

if __name__ == "__main__":
    # 设置一些优化参数
    os.environ['CREDENTIAL_HEALTH_CHECK_INTERVAL'] = '300'  # 5分钟健康检查
    os.environ['CREDENTIAL_DISCOVERY_INTERVAL'] = '600'  # 10分钟发现
    
    # 运行扫描
    asyncio.run(run_optimized_scan())