#!/usr/bin/env python3
"""
凭证管理系统启动脚本
快速启动和演示凭证管理系统的功能
"""

import os
import sys
import asyncio
import argparse
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_dependencies():
    """检查依赖"""
    required_modules = [
        'cryptography',
        'pyyaml'
    ]
    
    missing = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    
    if missing:
        print(f"缺少依赖包: {', '.join(missing)}")
        print(f"请运行: pip install {' '.join(missing)}")
        return False
    
    return True


def init_demo_environment():
    """初始化演示环境"""
    # 创建演示目录
    demo_dir = Path("demo_credentials")
    demo_dir.mkdir(exist_ok=True)
    
    # 创建示例配置文件
    config_file = demo_dir / "config.json"
    if not config_file.exists():
        import json
        config = {
            "vault_db_path": str(demo_dir / "credentials.db"),
            "balancing_strategy": "quota_aware",
            "health_check_interval": 30,
            "auto_import_threshold": 0.8
        }
        config_file.write_text(json.dumps(config, indent=2))
        logger.info(f"创建配置文件: {config_file}")
    
    # 创建示例凭证文件
    tokens_file = demo_dir / "github_tokens.txt"
    if not tokens_file.exists():
        tokens_file.write_text("""# GitHub Tokens for Demo
ghp_demo1234567890abcdefghijklmnopqrstuv
ghp_demo2234567890abcdefghijklmnopqrstuv
ghp_demo3234567890abcdefghijklmnopqrstuv
""")
        logger.info(f"创建示例token文件: {tokens_file}")
    
    # 创建.env文件
    env_file = demo_dir / ".env"
    if not env_file.exists():
        env_file.write_text("""# Demo Environment Variables
GITHUB_TOKEN=ghp_env1234567890abcdefghijklmnopqrstuv
OPENAI_API_KEY=sk-demo234567890abcdefghijklmnopqrstuvwxyz12
API_SECRET=demo_secret_key_1234567890
""")
        logger.info(f"创建示例.env文件: {env_file}")
    
    return demo_dir


async def demo_basic_usage():
    """演示基本使用"""
    print("\n" + "="*60)
    print("演示：基本凭证管理")
    print("="*60)
    
    from credential_manager.core.models import ServiceType, CredentialStatus
    from credential_manager.core.manager import CredentialManager
    from credential_manager.storage.vault import CredentialVault
    
    # 创建管理器
    vault = CredentialVault(db_path='demo_credentials/basic.db')
    manager = CredentialManager(vault=vault, strategy='quota_aware')
    
    # 添加凭证
    print("\n1. 添加凭证...")
    tokens = [
        ("ghp_basic1234567890abcdefghijklmnopqrstuv", ServiceType.GITHUB),
        ("sk-basic234567890abcdefghijklmnopqrstuvwxyz12", ServiceType.OPENAI),
    ]
    
    for token, service_type in tokens:
        cred_id = manager.add_credential(value=token, service_type=service_type)
        print(f"   ✓ 添加 {service_type.value} 凭证: {cred_id[:8]}...")
    
    # 获取凭证
    print("\n2. 获取最优凭证...")
    credential = manager.get_optimal_credential(ServiceType.GITHUB)
    if credential:
        print(f"   ✓ 获取到: {credential.masked_value}")
        print(f"   - 健康评分: {credential.calculate_health_score():.1f}")
    
    # 显示统计
    print("\n3. 凭证统计...")
    stats = manager.get_statistics()
    print(f"   - 总凭证数: {stats['total_credentials']}")
    print(f"   - 平均健康评分: {stats['average_health_score']:.1f}")
    print(f"   - 状态分布: {stats['by_status']}")


async def demo_discovery():
    """演示凭证发现"""
    print("\n" + "="*60)
    print("演示：凭证自动发现")
    print("="*60)
    
    from credential_manager.discovery.discovery import (
        CredentialDiscoveryEngine,
        FileScanner,
        EnvironmentScanner
    )
    
    demo_dir = init_demo_environment()
    
    # 创建发现引擎
    discovery = CredentialDiscoveryEngine()
    
    # 添加扫描器
    print("\n1. 配置扫描器...")
    discovery.add_scanner(FileScanner([str(demo_dir)]))
    discovery.add_scanner(EnvironmentScanner())
    print("   ✓ 文件扫描器")
    print("   ✓ 环境变量扫描器")
    
    # 执行发现
    print("\n2. 执行扫描...")
    discovered = discovery.discover()
    
    print(f"\n3. 发现结果: 找到 {len(discovered)} 个凭证")
    for i, cred in enumerate(discovered[:5], 1):  # 只显示前5个
        print(f"   {i}. {cred.masked_value}")
        print(f"      - 来源: {cred.source}")
        print(f"      - 类型: {cred.service_type}")
        print(f"      - 置信度: {cred.confidence:.2f}")
    
    # 导出报告
    report_path = demo_dir / "discovery_report.json"
    discovery.export_report(str(report_path))
    print(f"\n4. 报告已导出到: {report_path}")


async def demo_health_check():
    """演示健康检查"""
    print("\n" + "="*60)
    print("演示：健康检查与自愈")
    print("="*60)
    
    from credential_manager.core.models import ServiceType, CredentialStatus
    from credential_manager.core.manager import CredentialManager
    from credential_manager.storage.vault import CredentialVault
    from credential_manager.healing.health_check import HealthChecker, SelfHealingEngine
    
    # 创建管理器
    vault = CredentialVault(db_path='demo_credentials/health.db')
    manager = CredentialManager(vault=vault)
    
    # 添加测试凭证
    print("\n1. 创建测试凭证...")
    cred_id = manager.add_credential(
        value="ghp_health1234567890abcdefghijklmnopqrst",
        service_type=ServiceType.GITHUB
    )
    
    # 模拟问题
    credential = manager.vault.load(cred_id)
    credential.metrics.success_rate = 0.3  # 低成功率
    credential.remaining_quota = 10  # 低配额
    manager.vault.save(credential)
    print("   ✓ 模拟凭证问题（低成功率、低配额）")
    
    # 健康检查
    print("\n2. 执行健康检查...")
    health_checker = HealthChecker()
    result = health_checker.check_credential(credential)
    
    print(f"   - 健康状态: {result.status.value}")
    print(f"   - 健康评分: {result.score:.1f}")
    print(f"   - 发现问题: {len(result.issues)}")
    for issue in result.issues:
        print(f"     • {issue}")
    print(f"   - 建议: {len(result.recommendations)}")
    for rec in result.recommendations:
        print(f"     • {rec}")
    
    # 自愈
    print("\n3. 执行自愈...")
    healing_engine = SelfHealingEngine(health_checker)
    actions = await healing_engine.diagnose_and_heal(credential, manager)
    
    print(f"   执行了 {len(actions)} 个自愈动作:")
    for action in actions:
        print(f"   - {action.action_type}: {action.description}")


async def demo_monitoring():
    """演示监控仪表板"""
    print("\n" + "="*60)
    print("演示：监控仪表板")
    print("="*60)
    
    from credential_manager.core.models import ServiceType
    from credential_manager.core.manager import CredentialManager
    from credential_manager.storage.vault import CredentialVault
    from credential_manager.monitoring.dashboard import Dashboard
    
    # 创建管理器
    vault = CredentialVault(db_path='demo_credentials/monitoring.db')
    manager = CredentialManager(vault=vault)
    
    # 添加一些凭证
    print("\n1. 准备测试数据...")
    for i in range(3):
        manager.add_credential(
            value=f"ghp_monitor{i}234567890abcdefghijklmnopq",
            service_type=ServiceType.GITHUB
        )
    print("   ✓ 添加了3个测试凭证")
    
    # 创建仪表板
    print("\n2. 启动监控仪表板...")
    dashboard = Dashboard(manager, update_interval=2)
    dashboard.start()
    print("   ✓ 仪表板已启动")
    
    # 等待收集一些数据
    await asyncio.sleep(3)
    
    # 获取摘要
    print("\n3. 监控摘要:")
    summary = dashboard.get_summary()
    
    print(f"   当前指标:")
    for name, data in summary['current_metrics'].items():
        if isinstance(data['value'], float):
            print(f"   - {name}: {data['value']:.2f}")
        else:
            print(f"   - {name}: {data['value']}")
    
    # 生成报告
    report_path = "demo_credentials/monitoring_report.json"
    dashboard.generate_report(report_path)
    print(f"\n4. 监控报告已生成: {report_path}")
    
    # 停止仪表板
    dashboard.stop()


async def demo_integration():
    """演示系统集成"""
    print("\n" + "="*60)
    print("演示：系统集成桥接器")
    print("="*60)
    
    from credential_manager.integration.credential_bridge import (
        CredentialBridge,
        GitHubTokenBridge
    )
    
    demo_dir = init_demo_environment()
    
    # 创建桥接器
    print("\n1. 创建凭证桥接器...")
    bridge = CredentialBridge(
        config_path=str(demo_dir / "config.json"),
        auto_discover=True,
        enable_healing=True
    )
    print("   ✓ 桥接器已创建（启用自动发现和自愈）")
    
    # 获取凭证
    print("\n2. 通过桥接器获取凭证...")
    cred = bridge.get_credential(service_type='github')
    if cred:
        print(f"   ✓ 获取到凭证: {cred['masked_value']}")
        print(f"   - 状态: {cred['status']}")
        print(f"   - 健康评分: {cred['health_score']:.1f}")
    
    # GitHub Token桥接器
    print("\n3. GitHub Token专用桥接器...")
    github_bridge = GitHubTokenBridge(
        tokens_file=str(demo_dir / "github_tokens.txt")
    )
    
    token = github_bridge.get_next_token()
    if token:
        print(f"   ✓ 获取Token: {token[:10]}...")
    
    status = github_bridge.get_status()
    print(f"   - 总Tokens: {status['total_tokens']}")
    print(f"   - 活跃: {status['active']}")
    print(f"   - 平均健康度: {status['average_health']:.1f}")
    
    # 健康报告
    print("\n4. 生成健康报告...")
    health_report = bridge.get_health_report()
    print(f"   凭证健康状态汇总:")
    for key, value in health_report['summary'].items():
        print(f"   - {key}: {value}")


async def run_interactive_dashboard():
    """运行交互式仪表板"""
    from credential_manager.core.manager import CredentialManager
    from credential_manager.storage.vault import CredentialVault
    from credential_manager.monitoring.dashboard import Dashboard, ConsoleDashboard
    
    # 创建管理器
    vault = CredentialVault(db_path='demo_credentials/interactive.db')
    manager = CredentialManager(vault=vault)
    
    # 创建仪表板
    dashboard = Dashboard(manager)
    dashboard.start()
    
    # 运行控制台界面
    console = ConsoleDashboard(dashboard)
    console.run_interactive(refresh_interval=5)


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='凭证管理系统启动脚本')
    parser.add_argument(
        '--mode',
        choices=['demo', 'test', 'dashboard', 'all'],
        default='demo',
        help='运行模式'
    )
    parser.add_argument(
        '--clean',
        action='store_true',
        help='清理演示数据'
    )
    
    args = parser.parse_args()
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 清理模式
    if args.clean:
        import shutil
        if Path('demo_credentials').exists():
            shutil.rmtree('demo_credentials')
            print("✓ 演示数据已清理")
        for db_file in Path('.').glob('*.db'):
            db_file.unlink()
            print(f"✓ 删除数据库: {db_file}")
        sys.exit(0)
    
    print("="*60)
    print(" " * 15 + "凭证管理系统演示")
    print("="*60)
    
    try:
        if args.mode == 'demo':
            # 运行基本演示
            await demo_basic_usage()
            await demo_discovery()
            await demo_health_check()
            await demo_monitoring()
            await demo_integration()
            
        elif args.mode == 'test':
            # 运行测试
            print("\n运行测试套件...")
            os.system('python test_credential_manager.py')
            
        elif args.mode == 'dashboard':
            # 运行交互式仪表板
            print("\n启动交互式监控仪表板...")
            print("按 Ctrl+C 退出\n")
            await run_interactive_dashboard()
            
        elif args.mode == 'all':
            # 运行所有演示
            await demo_basic_usage()
            await demo_discovery()
            await demo_health_check()
            await demo_monitoring()
            await demo_integration()
            print("\n运行测试套件...")
            os.system('python test_credential_manager.py')
        
        print("\n" + "="*60)
        print("演示完成！")
        print("="*60)
        print("\n下一步:")
        print("1. 查看生成的文件: demo_credentials/")
        print("2. 阅读使用指南: CREDENTIAL_MANAGER_GUIDE.md")
        print("3. 运行交互式仪表板: python start_credential_manager.py --mode dashboard")
        print("4. 清理演示数据: python start_credential_manager.py --clean")
        
    except KeyboardInterrupt:
        print("\n\n演示已中断")
    except Exception as e:
        logger.error(f"演示失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())