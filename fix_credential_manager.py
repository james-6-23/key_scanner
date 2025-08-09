#!/usr/bin/env python3
"""
修复凭证管理系统的兼容性问题
"""

import os
import sys
import subprocess

def fix_dependencies():
    """修复依赖问题"""
    print("修复依赖问题...")
    
    # 检查是否使用uv
    try:
        subprocess.run(["uv", "--version"], check=True, capture_output=True)
        print("检测到uv，使用uv安装依赖...")
        
        # 使用uv安装依赖
        deps = ["pyyaml", "cryptography"]
        for dep in deps:
            print(f"安装 {dep}...")
            subprocess.run(["uv", "pip", "install", dep], check=False)
            
    except (subprocess.CalledProcessError, FileNotFoundError):
        # 使用pip安装
        print("使用pip安装依赖...")
        deps = ["pyyaml", "cryptography"]
        for dep in deps:
            print(f"安装 {dep}...")
            subprocess.run([sys.executable, "-m", "pip", "install", dep], check=False)

def create_simple_test():
    """创建简单的测试脚本"""
    test_code = '''#!/usr/bin/env python3
"""
简单的凭证管理系统测试
"""

import sys
import os
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_basic_functionality():
    """测试基本功能"""
    print("\\n" + "="*60)
    print("凭证管理系统基础测试")
    print("="*60)
    
    try:
        # 导入模块
        from credential_manager.core.models import ServiceType, CredentialStatus
        from credential_manager.core.manager import CredentialManager
        print("✓ 模块导入成功")
        
        # 创建管理器（使用正确的初始化方式）
        config = {
            "encryption_enabled": False,  # 禁用加密以避免cryptography依赖
            "balancing_strategy": "round_robin",
            "min_pool_size": 5,
            "max_pool_size": 50
        }
        manager = CredentialManager(config=config)
        print("✓ 管理器创建成功")
        
        # 添加测试凭证
        test_tokens = [
            ("ghp_test1234567890abcdefghijklmnopqrstuv", ServiceType.GITHUB),
            ("ghp_test2234567890abcdefghijklmnopqrstuv", ServiceType.GITHUB),
        ]
        
        for token, service_type in test_tokens:
            credential = manager.add_credential(
                service_type=service_type,
                value=token,
                metadata={"source": "test"}
            )
            if credential:
                print(f"✓ 添加凭证: {credential.masked_value}")
        
        # 获取最优凭证
        optimal = manager.get_optimal_credential(ServiceType.GITHUB)
        if optimal:
            print(f"✓ 获取最优凭证: {optimal.masked_value}")
            print(f"  - 状态: {optimal.status.value}")
            print(f"  - 健康评分: {optimal.calculate_health_score():.1f}")
        
        # 获取状态
        status = manager.get_status()
        print(f"\\n系统状态:")
        print(f"  - 总请求数: {status['stats']['total_requests']}")
        print(f"  - 成功请求: {status['stats']['successful_requests']}")
        print(f"  - 失败请求: {status['stats']['failed_requests']}")
        
        for service_type, pool_stats in status['pools'].items():
            print(f"\\n  {service_type} 池:")
            print(f"    - 总凭证数: {pool_stats['total']}")
            print(f"    - 可用凭证: {pool_stats['available']}")
        
        print("\\n✅ 所有基础测试通过!")
        return True
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("\\n请确保已安装所需依赖:")
        print("  pip install pyyaml")
        print("  pip install cryptography (可选)")
        return False
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_load_balancing():
    """测试负载均衡策略"""
    print("\\n" + "="*60)
    print("负载均衡策略测试")
    print("="*60)
    
    try:
        from credential_manager.balancer.strategies import list_strategies, get_strategy
        
        strategies = list_strategies()
        print(f"可用策略: {strategies}")
        
        # 测试每个策略
        for strategy_name in ['random', 'round_robin', 'quota_aware']:
            strategy = get_strategy(strategy_name)
            print(f"✓ 策略 '{strategy_name}' 加载成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 负载均衡测试失败: {e}")
        return False

def test_health_check():
    """测试健康检查功能"""
    print("\\n" + "="*60)
    print("健康检查功能测试")
    print("="*60)
    
    try:
        from credential_manager.core.models import Credential, ServiceType, CredentialStatus
        from credential_manager.healing.health_check import HealthChecker
        
        # 创建测试凭证
        credential = Credential(
            service_type=ServiceType.GITHUB,
            value="ghp_healthtest1234567890abcdefghijklmnop",
            status=CredentialStatus.ACTIVE
        )
        
        # 创建健康检查器
        health_checker = HealthChecker()
        
        # 执行健康检查
        result = health_checker.check_credential(credential)
        print(f"✓ 健康检查完成")
        print(f"  - 状态: {result.status.value}")
        print(f"  - 评分: {result.score:.1f}")
        
        return True
        
    except Exception as e:
        print(f"❌ 健康检查测试失败: {e}")
        return False

def main():
    """主函数"""
    print("凭证管理系统测试套件 (简化版)")
    print("="*60)
    
    all_passed = True
    
    # 运行测试
    tests = [
        ("基础功能", test_basic_functionality),
        ("负载均衡", test_load_balancing),
        ("健康检查", test_health_check)
    ]
    
    for test_name, test_func in tests:
        try:
            if not test_func():
                all_passed = False
        except Exception as e:
            print(f"\\n❌ {test_name}测试异常: {e}")
            all_passed = False
    
    # 总结
    print("\\n" + "="*60)
    if all_passed:
        print("✅ 所有测试通过!")
    else:
        print("⚠️ 部分测试失败，请检查错误信息")
    print("="*60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
'''
    
    with open("test_credential_simple.py", "w", encoding="utf-8") as f:
        f.write(test_code)
    
    print("创建了简化测试脚本: test_credential_simple.py")

def create_requirements_minimal():
    """创建最小依赖文件"""
    requirements = """# 凭证管理系统最小依赖

# 必需依赖
pyyaml>=6.0              # YAML文件解析

# 可选依赖（建议安装）
cryptography>=41.0.0     # 加密存储（可选，但推荐）

# 如果使用uv包管理器，运行:
# uv pip install pyyaml cryptography

# 如果使用pip，运行:
# pip install pyyaml cryptography
"""
    
    with open("requirements_minimal.txt", "w", encoding="utf-8") as f:
        f.write(requirements)
    
    print("创建了最小依赖文件: requirements_minimal.txt")

def main():
    print("="*60)
    print("凭证管理系统修复工具")
    print("="*60)
    
    # 1. 修复依赖
    fix_dependencies()
    
    # 2. 创建简单测试
    create_simple_test()
    
    # 3. 创建最小依赖文件
    create_requirements_minimal()
    
    print("\n修复完成！")
    print("\n下一步操作:")
    print("1. 运行简化测试: python test_credential_simple.py")
    print("2. 如果仍有问题，手动安装依赖:")
    print("   - uv pip install pyyaml")
    print("   - 或: pip install pyyaml")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())