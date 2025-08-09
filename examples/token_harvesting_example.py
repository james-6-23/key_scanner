"""
Token收集功能示例
演示如何安全地使用自动Token发现和验证功能

⚠️ 重要提醒：
- 此功能默认关闭，需要在.env中设置 CREDENTIAL_AUTO_HARVEST=true 启用
- 仅应在符合法律法规和服务条款的情况下使用
- 建议仅在开发/测试环境中使用，生产环境需要额外配置
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from credential_manager.core.manager import get_credential_manager
from credential_manager.core.models import ServiceType
from credential_manager.discovery.token_harvester import get_token_harvester
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_feature_status():
    """检查Token收集功能状态"""
    is_enabled = os.getenv('CREDENTIAL_AUTO_HARVEST', 'false').lower() == 'true'
    environment = os.getenv('ENVIRONMENT', 'development')
    
    print("=" * 60)
    print("Token收集功能状态检查")
    print("=" * 60)
    print(f"功能开关 (CREDENTIAL_AUTO_HARVEST): {is_enabled}")
    print(f"运行环境 (ENVIRONMENT): {environment}")
    
    if environment == 'production':
        prod_enabled = os.getenv('CREDENTIAL_HARVEST_PRODUCTION', 'false').lower() == 'true'
        print(f"生产环境开关 (CREDENTIAL_HARVEST_PRODUCTION): {prod_enabled}")
        
        if is_enabled and not prod_enabled:
            print("\n⚠️ 警告：生产环境需要设置 CREDENTIAL_HARVEST_PRODUCTION=true 才能启用")
    
    if is_enabled:
        print("\n✅ Token收集功能已启用")
        print("配置详情：")
        print(f"  - 风险阈值: {os.getenv('CREDENTIAL_HARVEST_RISK_THRESHOLD', '2')}")
        print(f"  - 验证发现的tokens: {os.getenv('CREDENTIAL_VALIDATE_DISCOVERED', 'true')}")
        print(f"  - 最大发现数量: {os.getenv('CREDENTIAL_MAX_DISCOVERED', '10')}")
        print(f"  - 沙箱验证: {os.getenv('CREDENTIAL_SANDBOX_VALIDATION', 'true')}")
        print(f"  - 蜜罐检测: {os.getenv('CREDENTIAL_HONEYPOT_DETECTION', 'true')}")
    else:
        print("\n🔒 Token收集功能已禁用（默认状态）")
        print("如需启用，请在.env文件中设置：")
        print("  CREDENTIAL_AUTO_HARVEST=true")
    
    print("=" * 60)
    return is_enabled


async def demonstrate_token_harvesting():
    """演示Token收集功能"""
    
    # 检查功能状态
    if not check_feature_status():
        print("\n功能未启用，演示结束")
        return
    
    print("\n开始演示Token收集功能...")
    
    # 初始化凭证管理器（会自动初始化TokenHarvester）
    config = {
        "harvesting_enabled": os.getenv('CREDENTIAL_AUTO_HARVEST', 'false').lower() == 'true',
        "encryption_enabled": True,
        "balancing_strategy": "quota_aware"
    }
    
    manager = get_credential_manager(config)
    harvester = get_token_harvester()
    
    # 显示初始状态
    print("\n初始状态：")
    stats = harvester.get_statistics()
    print(f"  - 功能状态: {'启用' if stats['enabled'] else '禁用'}")
    print(f"  - 已发现: {stats['stats']['total_discovered']}")
    print(f"  - 已验证: {stats['stats']['total_validated']}")
    print(f"  - 已添加: {stats['stats']['total_added']}")
    
    # 模拟扫描内容（示例内容，不包含真实token）
    sample_content = """
    # 示例配置文件
    # 注意：这些都是示例token，不是真实的
    
    github_token = "ghp_ExampleToken1234567890ABCDEFGHIJKLMN"
    api_key = "test_key_123"
    
    # 另一个示例
    GITHUB_PAT = "github_pat_ExampleFineGrained_1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    """
    
    print("\n扫描示例内容...")
    discovered = harvester.extract_tokens_from_content(
        sample_content, 
        source_url="example://demo/config.txt"
    )
    
    print(f"发现 {len(discovered)} 个潜在tokens")
    
    for token in discovered:
        print(f"  - {token.masked_token}")
        print(f"    风险等级: {token.risk_level.name}")
        print(f"    来源: {token.source_url}")
    
    # 验证tokens（异步）
    print("\n验证发现的tokens...")
    validated_count = 0
    for token in discovered:
        if await harvester.validate_token(token):
            validated_count += 1
            print(f"  ✅ 验证成功: {token.masked_token}")
        else:
            print(f"  ❌ 验证失败: {token.masked_token}")
    
    print(f"\n验证结果: {validated_count}/{len(discovered)} 个tokens通过验证")
    
    # 获取最佳token
    best_token = harvester.get_best_discovered_token()
    if best_token:
        print(f"\n最佳可用token: {best_token.masked_token}")
        print(f"  - 剩余配额: {best_token.remaining_quota}")
        print(f"  - 风险等级: {best_token.risk_level.name}")
    
    # 显示最终统计
    print("\n最终统计：")
    final_stats = harvester.get_statistics()
    print(f"  - 总发现: {final_stats['stats']['total_discovered']}")
    print(f"  - 总验证: {final_stats['stats']['total_validated']}")
    print(f"  - 总添加: {final_stats['stats']['total_added']}")
    print(f"  - 总拒绝: {final_stats['stats']['total_rejected']}")
    print(f"  - 蜜罐检测: {final_stats['stats']['honeypots_detected']}")
    
    # 清理过期tokens
    print("\n执行清理...")
    harvester.cleanup_expired_tokens()
    
    print("\n演示完成！")


def demonstrate_safe_usage():
    """演示安全使用方式"""
    print("\n" + "=" * 60)
    print("安全使用指南")
    print("=" * 60)
    
    print("\n1. 环境隔离：")
    print("   - 开发环境：可以启用，用于测试")
    print("   - 测试环境：可以启用，但要限制范围")
    print("   - 生产环境：默认禁用，需要额外确认")
    
    print("\n2. 风险控制：")
    print("   - 设置合适的风险阈值（CREDENTIAL_HARVEST_RISK_THRESHOLD）")
    print("   - 启用蜜罐检测（CREDENTIAL_HONEYPOT_DETECTION=true）")
    print("   - 使用沙箱验证（CREDENTIAL_SANDBOX_VALIDATION=true）")
    
    print("\n3. 合规性：")
    print("   - 仅扫描您有权访问的内容")
    print("   - 遵守GitHub服务条款")
    print("   - 不要滥用发现的凭证")
    
    print("\n4. 监控和审计：")
    print("   - 定期检查统计信息")
    print("   - 记录所有token来源")
    print("   - 设置告警机制")
    
    print("\n5. 最佳实践：")
    print("   - 定期轮换自己的tokens")
    print("   - 使用最小权限原则")
    print("   - 实施token生命周期管理")
    
    print("=" * 60)


def main():
    """主函数"""
    print("Token收集功能演示程序")
    print("=" * 60)
    
    # 显示安全使用指南
    demonstrate_safe_usage()
    
    # 运行演示
    print("\n是否继续运行演示？(y/n): ", end="")
    choice = input().strip().lower()
    
    if choice == 'y':
        asyncio.run(demonstrate_token_harvesting())
    else:
        print("演示已取消")
    
    print("\n程序结束")


if __name__ == "__main__":
    main()