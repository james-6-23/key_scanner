#!/usr/bin/env python3
"""
扫描器诊断工具 - 检查和修复常见问题
"""

import sys
import os
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
            print(f"  ✅ {scanner}")
        else:
            print(f"  ❌ {scanner} - 缺失")
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
    print("✅ common.config")
except ImportError as e:
    print(f"❌ common.config: {e}")
    errors.append(str(e))

try:
    from common.Logger import Logger
    print("✅ common.Logger")
except ImportError as e:
    print(f"❌ common.Logger: {e}")
    errors.append(str(e))

try:
    from utils.file_manager import FileManager
    print("✅ utils.file_manager")
except ImportError as e:
    print(f"❌ utils.file_manager: {e}")
    errors.append(str(e))

try:
    from utils.github_client import GitHubClient
    print("✅ utils.github_client")
except ImportError as e:
    print(f"❌ utils.github_client: {e}")
    errors.append(str(e))

try:
    from utils.parallel_validator import ParallelValidator
    print("✅ utils.parallel_validator")
except ImportError as e:
    print(f"❌ utils.parallel_validator: {e}")
    errors.append(str(e))

# 测试凭证管理器（可选）
try:
    from credential_manager import CredentialManager
    print("✅ credential_manager")
except ImportError as e:
    print(f"⚠️  credential_manager (可选): {e}")

sys.exit(0 if not errors else 1)
"""
    
    result = subprocess.run([sys.executable, "-c", test_script], 
                          capture_output=True, text=True, cwd=Path.cwd())
    print(result.stdout)
    
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
    print("✅ 成功导入api_key_scanner_super")
    
    # 检查关键类和函数
    if hasattr(scanner, 'HajimiKingSuper'):
        print("✅ 找到HajimiKingSuper类")
    else:
        print("❌ 缺少HajimiKingSuper类")
    
    if hasattr(scanner, 'validate_api_key'):
        print("✅ 找到validate_api_key函数")
    else:
        print("❌ 缺少validate_api_key函数")
    
    if hasattr(scanner, 'main'):
        print("✅ 找到main函数")
    else:
        print("❌ 缺少main函数")
        
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"❌ 其他错误: {e}")
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
        print(f"  ❌ config/api_patterns.json 不存在")
        return False
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"  ✅ API配置文件存在")
        print(f"  支持的API类型: {', '.join(config.keys())}")
        
        # 检查查询文件
        for api_type in config.keys():
            query_file = Path(f"config/queries/{api_type}.txt")
            if query_file.exists():
                print(f"  ✅ {api_type}.txt 查询文件存在")
            else:
                print(f"  ⚠️  {api_type}.txt 查询文件缺失")
        
        return True
    except Exception as e:
        print(f"  ❌ 读取配置失败: {e}")
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
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} - 未安装")
            missing_required.append(package)
    
    print("\n可选依赖:")
    for module, package in optional.items():
        try:
            __import__(module)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ⚠️  {package} - 未安装")
    
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
        print(f"  ✅ 帮助命令执行成功")
        return True
    else:
        print(f"  ❌ 命令执行失败")
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
    
    if not test_super_scanner():
        issues.append("runtime")
    
    # 如果没有运行时错误，尝试运行测试命令
    if "runtime" not in issues:
        if not run_test_command():
            issues.append("runtime")
    
    # 显示结果
    print_header("诊断结果")
    
    if not issues:
        print(f"{Colors.GREEN}✅ 所有检查通过！扫描器应该可以正常运行。{Colors.RESET}")
    else:
        print(f"{Colors.RED}发现以下问题:{Colors.RESET}")
        for issue in issues:
            print(f"  • {issue}")
        
        suggest_fixes(issues)
    
    return 0 if not issues else 1

if __name__ == "__main__":
    sys.exit(main())