#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扫描器诊断工具 - 检查和修复常见问题
"""

import sys
import os
import io

# 设置标准输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
import subprocess
from pathlib import Path
import json

class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(title):
    """打印标题"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{title:^60}{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}\n")

def check_scanner_files():
    """检查扫描器文件是否存在"""
    print(f"{Colors.BOLD}检查扫描器文件:{Colors.RESET}")
    
    scanners = [
        "app/api_key_scanner.py",
        "app/api_key_scanner_improved.py",
        "app/api_key_scanner_super.py",
        "app/api_scanner_universal.py"
    ]
    
    all_exist = True
    for scanner in scanners:
        if Path(scanner).exists():
            print(f"  [OK] {scanner}")
        else:
            print(f"  [X] {scanner} - 缺失")
            all_exist = False
    
    return all_exist

def check_imports():
    """检查导入是否正常"""
    print(f"\n{Colors.BOLD}检查模块导入:{Colors.RESET}")
    
    test_script = """
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

errors = []

# 测试基础导入
try:
    from common.config import Config
    print("[OK] common.config")
except ImportError as e:
    print(f"[X] common.config: {e}")
    errors.append(str(e))

try:
    from common.Logger import Logger
    print("[OK] common.Logger")
except ImportError as e:
    print(f"[X] common.Logger: {e}")
    errors.append(str(e))

try:
    from utils.file_manager import FileManager
    print("[OK] utils.file_manager")
except ImportError as e:
    print(f"[X] utils.file_manager: {e}")
    errors.append(str(e))

try:
    from utils.github_client import GitHubClient
    print("[OK] utils.github_client")
except ImportError as e:
    print(f"[X] utils.github_client: {e}")
    errors.append(str(e))

try:
    from utils.parallel_validator import ParallelValidator
    print("[OK] utils.parallel_validator")
except ImportError as e:
    print(f"[X] utils.parallel_validator: {e}")
    errors.append(str(e))

# 测试凭证管理器
try:
    from credential_manager.core.manager import get_credential_manager
    print("[OK] credential_manager.core.manager")
except ImportError as e:
    print(f"[X] credential_manager.core.manager: {e}")
    errors.append(str(e))

try:
    from credential_manager.core.models import ServiceType, CredentialStatus
    print("[OK] credential_manager.core.models")
except ImportError as e:
    print(f"[X] credential_manager.core.models: {e}")
    errors.append(str(e))

try:
    from credential_manager.integration.credential_bridge import CredentialBridge
    print("[OK] credential_manager.integration.credential_bridge")
except ImportError as e:
    print(f"[X] credential_manager.integration.credential_bridge: {e}")
    errors.append(str(e))

# 测试增强版GitHub客户端
try:
    from utils.github_client_enhanced import EnhancedGitHubClient
    print("[OK] utils.github_client_enhanced")
except ImportError as e:
    print(f"[X] utils.github_client_enhanced: {e}")
    errors.append(str(e))

sys.exit(0 if not errors else 1)
"""
    
    result = subprocess.run([sys.executable, "-c", test_script], 
                          capture_output=True, text=True, cwd=Path.cwd())
    print(result.stdout)
    
    return result.returncode == 0

def test_credential_manager():
    """测试凭证管理器功能"""
    print(f"\n{Colors.BOLD}测试凭证管理器:{Colors.RESET}")
    
    test_script = """
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

try:
    # 测试凭证管理器初始化
    from credential_manager.core.manager import get_credential_manager
    from credential_manager.core.models import ServiceType
    
    config = {
        'encryption_enabled': False,
        'balancing_strategy': 'round_robin',
        'min_pool_size': 1,
        'max_pool_size': 10
    }
    
    manager = get_credential_manager(config)
    print("[OK] 凭证管理器初始化成功")
    
    # 测试get_statistics方法
    if hasattr(manager, 'get_statistics'):
        stats = manager.get_statistics()
        print("[OK] get_statistics方法存在")
    else:
        print("[X] get_statistics方法缺失")
    
    # 测试ServiceType枚举
    if hasattr(ServiceType, 'GCP'):
        print("[OK] ServiceType.GCP存在")
    else:
        print("[X] ServiceType.GCP缺失")
        
except Exception as e:
    print(f"[X] 凭证管理器测试失败: {e}")
    import traceback
    traceback.print_exc()
"""
    
    result = subprocess.run([sys.executable, "-c", test_script],
                          capture_output=True, text=True, cwd=Path.cwd())
    print(result.stdout)
    if result.stderr:
        print(f"{Colors.RED}错误输出:{Colors.RESET}")
        print(result.stderr)
    
    return result.returncode == 0

def test_enhanced_github_client():
    """测试增强版GitHub客户端"""
    print(f"\n{Colors.BOLD}测试增强版GitHub客户端:{Colors.RESET}")
    
    test_script = """
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

try:
    from utils.github_client_enhanced import EnhancedGitHubClient
    
    # 创建实例
    client = EnhancedGitHubClient(use_credential_manager=False)
    print("[OK] EnhancedGitHubClient实例化成功")
    
    # 检查新方法
    if hasattr(client, 'search_repositories'):
        print("[OK] search_repositories方法存在")
    else:
        print("[X] search_repositories方法缺失")
    
    if hasattr(client, 'search_in_repository'):
        print("[OK] search_in_repository方法存在")
    else:
        print("[X] search_in_repository方法缺失")
    
    if hasattr(client, 'get_file_content'):
        # 检查是否有异步版本
        import inspect
        if any(param == 'repo_name' for param in inspect.signature(client.get_file_content).parameters):
            print("[OK] get_file_content异步版本存在")
        print("[OK] get_file_content方法存在")
    else:
        print("[X] get_file_content方法缺失")
        
except Exception as e:
    print(f"[X] GitHub客户端测试失败: {e}")
    import traceback
    traceback.print_exc()
"""
    
    result = subprocess.run([sys.executable, "-c", test_script],
                          capture_output=True, text=True, cwd=Path.cwd())
    print(result.stdout)
    if result.stderr:
        print(f"{Colors.RED}错误输出:{Colors.RESET}")
        print(result.stderr)
    
    return result.returncode == 0

def test_super_scanner():
    """测试超级版扫描器"""
    print(f"\n{Colors.BOLD}测试超级版扫描器:{Colors.RESET}")
    
    # 尝试导入并检查错误
    test_script = """
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

try:
    # 尝试导入
    import app.api_key_scanner_super as scanner
    print("[OK] 成功导入api_key_scanner_super")
    
    # 检查关键类和函数
    if hasattr(scanner, 'HajimiKingSuper'):
        print("[OK] 找到HajimiKingSuper类")
    else:
        print("[X] 缺少HajimiKingSuper类")
    
    if hasattr(scanner, 'validate_api_key'):
        print("[OK] 找到validate_api_key函数")
    else:
        print("[X] 缺少validate_api_key函数")
    
    if hasattr(scanner, 'main'):
        print("[OK] 找到main函数")
    else:
        print("[X] 缺少main函数")
    
    # 测试SuperAPIKeyScanner类
    if hasattr(scanner, 'SuperAPIKeyScanner'):
        print("[OK] 找到SuperAPIKeyScanner类")
        
        # 尝试实例化
        try:
            instance = scanner.SuperAPIKeyScanner(['gemini'])
            print("[OK] SuperAPIKeyScanner实例化成功")
        except Exception as e:
            print(f"[X] SuperAPIKeyScanner实例化失败: {e}")
    else:
        print("[X] 缺少SuperAPIKeyScanner类")
        
except ImportError as e:
    print(f"[X] 导入失败: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"[X] 其他错误: {e}")
    import traceback
    traceback.print_exc()
"""
    
    result = subprocess.run([sys.executable, "-c", test_script], 
                          capture_output=True, text=True, cwd=Path.cwd())
    print(result.stdout)
    if result.stderr:
        print(f"{Colors.RED}错误输出:{Colors.RESET}")
        print(result.stderr)
    
    return result.returncode == 0

def check_api_config():
    """检查API配置"""
    print(f"\n{Colors.BOLD}检查API配置:{Colors.RESET}")
    
    config_file = Path("config/api_patterns.json")
    if not config_file.exists():
        print(f"  [X] config/api_patterns.json 不存在")
        return False
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"  [OK] API配置文件存在")
        print(f"  支持的API类型: {', '.join(config.keys())}")
        
        # 检查查询文件
        for api_type in config.keys():
            query_file = Path(f"config/queries/{api_type}.txt")
            if query_file.exists():
                print(f"  [OK] {api_type}.txt 查询文件存在")
            else:
                print(f"  [!] {api_type}.txt 查询文件缺失")
        
        return True
    except Exception as e:
        print(f"  [X] 读取配置失败: {e}")
        return False

def check_dependencies():
    """检查Python依赖"""
    print(f"\n{Colors.BOLD}检查Python依赖:{Colors.RESET}")
    
    required = {
        "google.generativeai": "google-generativeai",
        "dotenv": "python-dotenv",
        "requests": "requests",
        "aiohttp": "aiohttp",
    }
    
    optional = {
        "cryptography": "cryptography",
        "redis": "redis",
        "psutil": "psutil",
    }
    
    missing_required = []
    
    print("必需依赖:")
    for module, package in required.items():
        try:
            __import__(module)
            print(f"  [OK] {package}")
        except ImportError:
            print(f"  [X] {package} - 未安装")
            missing_required.append(package)
    
    print("\n可选依赖:")
    for module, package in optional.items():
        try:
            __import__(module)
            print(f"  [OK] {package}")
        except ImportError:
            print(f"  [!] {package} - 未安装")
    
    if missing_required:
        print(f"\n{Colors.YELLOW}安装缺失的依赖:{Colors.RESET}")
        print(f"  pip install {' '.join(missing_required)}")
        return False
    
    return True

def run_test_command():
    """运行测试命令"""
    print(f"\n{Colors.BOLD}运行测试命令:{Colors.RESET}")
    
    # 测试简单的帮助命令
    cmd = [sys.executable, "app/api_key_scanner_super.py", "--help"]
    print(f"执行: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path.cwd())
    
    if result.returncode == 0:
        print(f"  [OK] 帮助命令执行成功")
        return True
    else:
        print(f"  [X] 命令执行失败")
        print(f"错误输出:")
        print(result.stderr)
        return False

def suggest_fixes(issues):
    """建议修复方案"""
    print_header("建议的修复方案")
    
    if "files" in issues:
        print(f"{Colors.YELLOW}文件缺失问题:{Colors.RESET}")
        print("  1. 确保已拉取最新代码: git pull")
        print("  2. 检查文件是否在正确位置")
    
    if "imports" in issues:
        print(f"{Colors.YELLOW}导入问题:{Colors.RESET}")
        print("  1. 确保PYTHONPATH正确")
        print("  2. 检查__init__.py文件")
        print("  3. 尝试: export PYTHONPATH=$PYTHONPATH:$(pwd)")
    
    if "dependencies" in issues:
        print(f"{Colors.YELLOW}依赖问题:{Colors.RESET}")
        print("  1. 安装缺失的包: pip install -r requirements.txt")
        print("  2. 或使用: pip install google-generativeai python-dotenv requests aiohttp")
    
    if "config" in issues:
        print(f"{Colors.YELLOW}配置问题:{Colors.RESET}")
        print("  1. 检查config/api_patterns.json是否存在")
        print("  2. 检查config/queries/目录")
    
    if "runtime" in issues:
        print(f"{Colors.YELLOW}运行时问题:{Colors.RESET}")
        print("  1. 检查Python版本 (需要3.8+)")
        print("  2. 检查环境变量配置")
        print("  3. 尝试直接运行: python app/api_key_scanner.py (基础版)")
    
    if "credential_manager" in issues:
        print(f"{Colors.YELLOW}凭证管理器问题:{Colors.RESET}")
        print("  1. 检查credential_manager目录结构")
        print("  2. 确保所有__init__.py文件存在")
        print("  3. 检查ServiceType枚举是否包含所有必需的服务类型")
    
    if "github_client" in issues:
        print(f"{Colors.YELLOW}GitHub客户端问题:{Colors.RESET}")
        print("  1. 检查utils/github_client_enhanced.py文件")
        print("  2. 确保search_repositories和search_in_repository方法存在")
        print("  3. 检查异步方法实现")

def main():
    """主函数"""
    print_header("扫描器诊断工具")
    
    issues = []
    
    # 运行各项检查
    if not check_scanner_files():
        issues.append("files")
    
    if not check_dependencies():
        issues.append("dependencies")
    
    if not check_imports():
        issues.append("imports")
    
    if not check_api_config():
        issues.append("config")
    
    if not test_credential_manager():
        issues.append("credential_manager")
    
    if not test_enhanced_github_client():
        issues.append("github_client")
    
    if not test_super_scanner():
        issues.append("runtime")
    
    # 如果没有运行时错误，尝试运行测试命令
    if "runtime" not in issues:
        if not run_test_command():
            issues.append("runtime")
    
    # 显示结果
    print_header("诊断结果")
    
    if not issues:
        print(f"{Colors.GREEN}[OK] 所有检查通过！扫描器应该可以正常运行。{Colors.RESET}")
    else:
        print(f"{Colors.RED}发现以下问题:{Colors.RESET}")
        for issue in issues:
            print(f"  • {issue}")
        
        suggest_fixes(issues)
    
    return 0 if not issues else 1

if __name__ == "__main__":
    sys.exit(main())