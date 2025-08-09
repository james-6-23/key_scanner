"""
凭证管理系统测试和示例脚本
"""

import asyncio
import logging
import json
from pathlib import Path
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入凭证管理系统组件
from credential_manager.core.models import ServiceType, CredentialStatus
from credential_manager.core.manager import CredentialManager
from credential_manager.storage.vault import CredentialVault
from credential_manager.balancer.strategies import get_strategy, list_strategies
from credential_manager.healing.health_check import HealthChecker, SelfHealingEngine
from credential_manager.discovery.discovery import (
    CredentialDiscoveryEngine,
    FileScanner,
    EnvironmentScanner
)
from credential_manager.integration.credential_bridge import (
    CredentialBridge,
    GitHubTokenBridge,
    TokenManagerAdapter,
    create_bridge_from_env
)


def test_basic_credential_management():
    """测试基本的凭证管理功能"""
    print("\n=== 测试基本凭证管理 ===")
    
    # 创建管理器配置
    config = {
        "encryption_enabled": False,  # 禁用加密以避免cryptography依赖问题
        "balancing_strategy": "round_robin",
        "min_pool_size": 5,
        "max_pool_size": 50,
        "health_check_interval": 0,  # 禁用后台健康检查
        "discovery_enabled": False    # 禁用自动发现
    }
    
    # 创建管理器
    manager = CredentialManager(config=config)
    
    # 添加测试凭证
    test_tokens = [
        "ghp_test1234567890abcdefghijklmnopqrstuv",
        "ghp_test2234567890abcdefghijklmnopqrstuv",
        "sk-test1234567890abcdefghijklmnopqrstuvwxyz123456"
    ]
    
    for token in test_tokens:
        if token.startswith('ghp_'):
            service_type = ServiceType.GITHUB
        elif token.startswith('sk-'):
            service_type = ServiceType.OPENAI
        else:
            service_type = ServiceType.GENERIC
            
        credential = manager.add_credential(
            service_type=service_type,
            value=token,
            metadata={"source": "test"}
        )
        if credential:
            print(f"添加凭证: {credential.id[:8]}... (类型: {service_type.value})")
    
    # 获取最优凭证
    optimal = manager.get_optimal_credential(service_type=ServiceType.GITHUB)
    if optimal:
        print(f"获取最优GitHub凭证: {optimal.masked_value}")
    
    # 显示统计信息
    stats = manager.get_statistics()
    print(f"凭证统计: {json.dumps(stats, indent=2)}")
    
    return manager


def test_load_balancing_strategies():
    """测试负载均衡策略"""
    print("\n=== 测试负载均衡策略 ===")
    
    # 列出所有可用策略
    strategies = list_strategies()
    print(f"可用策略: {strategies}")
    
    for strategy_name in ['random', 'round_robin', 'quota_aware']:
        print(f"\n测试策略: {strategy_name}")
        
        # 为每个策略创建新的管理器
        config = {
            "encryption_enabled": False,
            "balancing_strategy": strategy_name,
            "health_check_interval": 0,
            "discovery_enabled": False
        }
        manager = CredentialManager(config=config)
        
        # 添加测试凭证
        for i in range(3):
            manager.add_credential(
                service_type=ServiceType.CUSTOM,
                value=f"test_token_{strategy_name}_{i}",
                metadata={"test": True}
            )
        
        # 获取凭证多次，观察分配模式
        selections = []
        for _ in range(5):
            cred = manager.get_optimal_credential(ServiceType.CUSTOM)
            if cred:
                selections.append(cred.masked_value)
        
        print(f"  选择序列: {selections}")


def test_health_checking():
    """测试健康检查功能"""
    print("\n=== 测试健康检查 ===")
    
    # 创建管理器
    config = {
        "encryption_enabled": False,
        "health_check_interval": 0,
        "discovery_enabled": False
    }
    manager = CredentialManager(config=config)
    
    # 添加测试凭证
    credential = manager.add_credential(
        service_type=ServiceType.GITHUB,
        value="ghp_healthtest1234567890abcdefghijklmnop",
        metadata={"test": True}
    )
    
    # 创建健康检查器
    health_checker = HealthChecker()
    
    # 获取凭证并检查健康状态
    credentials = manager.get_all_credentials()
    for cred in credentials:
        result = health_checker.check_credential(cred)
        print(f"凭证 {cred.masked_value}:")
        print(f"  状态: {result.status.value}")
        print(f"  评分: {result.score:.2f}")
        print(f"  问题: {result.issues}")
        print(f"  建议: {result.recommendations}")
    
    # 获取健康趋势
    if credentials:
        trend = health_checker.get_health_trend(credentials[0].id, hours=1)
        print(f"\n健康趋势: {json.dumps(trend, indent=2)}")


async def test_self_healing():
    """测试自愈机制"""
    print("\n=== 测试自愈机制 ===")
    
    # 创建管理器
    config = {
        "encryption_enabled": False,
        "health_check_interval": 0,
        "discovery_enabled": False
    }
    manager = CredentialManager(config=config)
    
    # 添加一个"有问题"的凭证
    credential = manager.add_credential(
        service_type=ServiceType.GITHUB,
        value="ghp_healingtest234567890abcdefghijklmnop",
        metadata={"test": True}
    )
    
    if not credential:
        print("无法创建测试凭证")
        return
    
    # 模拟凭证出现问题
    credential.status = CredentialStatus.DEGRADED
    credential.metrics.success_rate = 0.3  # 低成功率
    
    # 创建健康检查器和自愈引擎
    health_checker = HealthChecker()
    healing_engine = SelfHealingEngine(health_checker)
    
    # 执行诊断和自愈
    actions = await healing_engine.diagnose_and_heal(credential, manager)
    
    print(f"执行了 {len(actions)} 个自愈动作:")
    for action in actions:
        print(f"  - {action.action_type}: {action.description}")
        print(f"    成功: {action.success}, 结果: {action.result}")
    
    # 获取自愈报告
    report = healing_engine.get_healing_report(hours=1)
    print(f"\n自愈报告: {json.dumps(report, indent=2)}")


def test_credential_discovery():
    """测试凭证发现功能"""
    print("\n=== 测试凭证发现 ===")
    
    # 创建测试文件
    test_dir = Path("test_discovery")
    test_dir.mkdir(exist_ok=True)
    
    # 创建包含凭证的测试文件
    env_file = test_dir / ".env"
    env_file.write_text("""
# GitHub Token
GITHUB_TOKEN=ghp_discovery1234567890abcdefghijklmnop
# OpenAI API Key
OPENAI_API_KEY=sk-discovery234567890abcdefghijklmnopqrstuvwxyz12
# Generic API Key
API_KEY=generic_key_1234567890
    """)
    
    json_file = test_dir / "config.json"
    json_file.write_text(json.dumps({
        "github": {
            "token": "ghp_jsontest1234567890abcdefghijklmnopq"
        },
        "openai": {
            "api_key": "sk-jsontest234567890abcdefghijklmnopqrstuvwxyz123"
        }
    }, indent=2))
    
    # 创建发现引擎
    discovery_engine = CredentialDiscoveryEngine()
    
    # 添加扫描器
    discovery_engine.add_scanner(FileScanner([str(test_dir)]))
    discovery_engine.add_scanner(EnvironmentScanner())
    
    # 执行发现
    discovered = discovery_engine.discover()
    
    print(f"发现了 {len(discovered)} 个凭证:")
    for cred in discovered:
        print(f"  - {cred.masked_value}")
        print(f"    来源: {cred.source}")
        print(f"    类型: {cred.service_type}")
        print(f"    置信度: {cred.confidence:.2f}")
    
    # 导出报告
    report_path = test_dir / "discovery_report.json"
    discovery_engine.export_report(str(report_path))
    print(f"\n发现报告已导出到: {report_path}")
    
    # 清理测试文件
    import shutil
    shutil.rmtree(test_dir)


def test_credential_bridge():
    """测试凭证桥接器"""
    print("\n=== 测试凭证桥接器 ===")
    
    # 创建配置
    config = {
        'vault_db_path': 'test_bridge.db',
        'balancing_strategy': 'quota_aware',
        'health_check_interval': 0,  # 禁用后台任务
        'auto_import_threshold': 0.7
    }
    
    # 保存配置文件
    config_path = 'test_bridge_config.json'
    with open(config_path, 'w') as f:
        json.dump(config, f)
    
    # 创建桥接器
    bridge = CredentialBridge(
        config_path=config_path,
        auto_discover=False,  # 禁用自动发现以避免扫描整个系统
        enable_healing=False  # 禁用自愈以简化测试
    )
    
    # 手动添加凭证
    bridge.manager.add_credential(
        service_type=ServiceType.GITHUB,
        value="ghp_bridge1234567890abcdefghijklmnopqrst",
        metadata={"source": "test"}
    )
    
    # 使用桥接器获取凭证
    cred = bridge.get_credential(service_type='github')
    if cred:
        print(f"通过桥接器获取凭证: {cred['masked_value']}")
        print(f"  状态: {cred['status']}")
        print(f"  健康评分: {cred['health_score']:.2f}")
    
    # 获取健康报告
    health_report = bridge.get_health_report()
    print(f"\n健康报告摘要: {json.dumps(health_report['summary'], indent=2)}")
    
    # 测试Token管理器适配器
    adapter = bridge.token_adapter
    token = adapter.get_token()
    if token:
        print(f"\n通过适配器获取Token: {token[:10]}...")
        adapter.mark_token_used(token, success=True)
    
    stats = adapter.get_token_stats()
    print(f"Token统计: {json.dumps(stats, indent=2)}")
    
    # 清理
    Path(config_path).unlink()


def test_github_token_bridge():
    """测试GitHub Token桥接器"""
    print("\n=== 测试GitHub Token桥接器 ===")
    
    # 创建测试token文件
    tokens_file = 'test_github_tokens.txt'
    with open(tokens_file, 'w') as f:
        f.write("ghp_file1234567890abcdefghijklmnopqrstuv\n")
        f.write("ghp_file2234567890abcdefghijklmnopqrstuv\n")
        f.write("# This is a comment\n")
        f.write("ghp_file3234567890abcdefghijklmnopqrstuv\n")
    
    # 创建GitHub Token桥接器
    github_bridge = GitHubTokenBridge(tokens_file=tokens_file)
    
    # 获取下一个token
    next_token = github_bridge.get_next_token()
    if next_token:
        print(f"获取下一个Token: {next_token[:10]}...")
    
    # 添加新token
    new_token = "ghp_new1234567890abcdefghijklmnopqrstuvw"
    if github_bridge.add_new_token(new_token):
        print(f"添加新Token成功: {new_token[:10]}...")
    
    # 获取状态
    status = github_bridge.get_status()
    print(f"GitHub Token状态: {json.dumps(status, indent=2)}")
    
    # 标记token耗尽
    if next_token:
        github_bridge.mark_token_exhausted(next_token)
        print(f"标记Token耗尽: {next_token[:10]}...")
    
    # 移除无效tokens
    github_bridge.remove_invalid_tokens()
    
    # 同步到文件
    github_bridge.sync_to_file()
    print(f"已同步到文件: {tokens_file}")
    
    # 清理
    Path(tokens_file).unlink()
    Path('github_credentials.db').unlink(missing_ok=True)


async def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("凭证管理系统测试套件")
    print("=" * 60)
    
    try:
        # 基础功能测试
        test_basic_credential_management()
        
        # 负载均衡测试
        test_load_balancing_strategies()
        
        # 健康检查测试
        test_health_checking()
        
        # 自愈机制测试
        await test_self_healing()
        
        # 凭证发现测试
        test_credential_discovery()
        
        # 桥接器测试
        test_credential_bridge()
        
        # GitHub Token桥接器测试
        test_github_token_bridge()
        
        print("\n" + "=" * 60)
        print("所有测试完成！")
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
        
    finally:
        # 清理测试数据库
        for db_file in Path('.').glob('test_*.db'):
            db_file.unlink(missing_ok=True)
            logger.info(f"清理测试数据库: {db_file}")


def main():
    """主函数"""
    # 运行异步测试
    asyncio.run(run_all_tests())


if __name__ == "__main__":
    main()