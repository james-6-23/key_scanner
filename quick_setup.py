#!/usr/bin/env python3
"""
快速设置脚本 - 一键配置本地环境
"""

import sys
import os
import subprocess
import shutil
from pathlib import Path
import platform

class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(title):
    """打印标题"""
    print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{title:^60}{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")

def print_step(step, description):
    """打印步骤"""
    print(f"{Colors.BLUE}[步骤 {step}]{Colors.RESET} {description}")

def print_success(message):
    """打印成功消息"""
    print(f"{Colors.GREEN}✅ {message}{Colors.RESET}")

def print_error(message):
    """打印错误消息"""
    print(f"{Colors.RED}❌ {message}{Colors.RESET}")

def print_warning(message):
    """打印警告消息"""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.RESET}")

def print_info(message):
    """打印信息"""
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.RESET}")

def check_python_version():
    """检查Python版本"""
    print_step(1, "检查Python版本")
    
    version = sys.version_info
    if version.major >= 3 and version.minor >= 11:
        print_success(f"Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print_error(f"Python版本过低 (当前: {version.major}.{version.minor}, 需要: 3.11+)")
        print_info("请访问 https://www.python.org/downloads/ 下载最新版本")
        return False

def create_virtual_environment():
    """创建虚拟环境"""
    print_step(2, "创建虚拟环境")
    
    venv_path = Path("venv")
    if venv_path.exists():
        print_warning("虚拟环境已存在")
        response = input("是否重新创建? (y/N): ")
        if response.lower() != 'y':
            return True
        shutil.rmtree(venv_path)
    
    try:
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print_success("虚拟环境创建成功")
        return True
    except subprocess.CalledProcessError:
        print_error("虚拟环境创建失败")
        return False

def get_pip_command():
    """获取pip命令"""
    if platform.system() == "Windows":
        return ["venv\\Scripts\\pip.exe"]
    else:
        return ["venv/bin/pip"]

def install_dependencies():
    """安装依赖"""
    print_step(3, "安装依赖包")
    
    pip_cmd = get_pip_command()
    
    # 核心依赖
    core_packages = [
        "google-generativeai>=0.8.5",
        "python-dotenv>=1.1.1",
        "requests>=2.32.4",
        "aiohttp>=3.9.0",
        "colorama>=0.4.6",
        "rich>=13.7.0",
    ]
    
    # 可选依赖
    optional_packages = [
        "psutil>=5.9.0",
        "cryptography>=41.0.0",
    ]
    
    print("安装核心依赖...")
    for package in core_packages:
        try:
            subprocess.run(pip_cmd + ["install", package], 
                         check=True, capture_output=True, text=True)
            print(f"  ✅ {package.split('>=')[0]}")
        except subprocess.CalledProcessError as e:
            print_error(f"安装 {package} 失败")
            print(f"     {e.stderr}")
            return False
    
    print("\n安装可选依赖...")
    for package in optional_packages:
        try:
            subprocess.run(pip_cmd + ["install", package], 
                         check=True, capture_output=True, text=True)
            print(f"  ✅ {package.split('>=')[0]}")
        except subprocess.CalledProcessError:
            print_warning(f"{package.split('>=')[0]} 安装失败 (可选)")
    
    print_success("依赖安装完成")
    return True

def setup_config_files():
    """设置配置文件"""
    print_step(4, "设置配置文件")
    
    # 创建.env文件
    env_file = Path(".env")
    if not env_file.exists():
        if Path("env.example").exists():
            shutil.copy("env.example", ".env")
            print_success("创建.env文件")
        else:
            # 创建默认.env
            env_content = """# GitHub Token (必需)
GITHUB_TOKENS=ghp_your_token_here

# API类型
DEFAULT_API_TYPE=gemini

# 代理设置 (可选)
# PROXY=http://127.0.0.1:7890

# 性能设置
HAJIMI_MAX_WORKERS=10
HAJIMI_BATCH_SIZE=10

# 日志级别
LOG_LEVEL=INFO
"""
            env_file.write_text(env_content)
            print_success("创建默认.env文件")
    else:
        print_info(".env文件已存在")
    
    # 创建queries.txt
    queries_file = Path("queries.txt")
    if not queries_file.exists():
        if Path("queries.example").exists():
            shutil.copy("queries.example", "queries.txt")
            print_success("创建queries.txt文件")
        elif Path("config/queries/gemini.txt").exists():
            shutil.copy("config/queries/gemini.txt", "queries.txt")
            print_success("从gemini.txt创建queries.txt")
        else:
            # 创建默认queries
            queries_content = """AIzaSy in:file
AIzaSy in:file extension:json
AIzaSy in:file filename:.env
"api_key" in:file
"""
            queries_file.write_text(queries_content)
            print_success("创建默认queries.txt文件")
    else:
        print_info("queries.txt文件已存在")
    
    # 创建github_tokens.txt
    tokens_file = Path("github_tokens.txt")
    if not tokens_file.exists():
        tokens_file.touch()
        print_success("创建github_tokens.txt文件")
    
    return True

def create_directories():
    """创建必要的目录"""
    print_step(5, "创建目录结构")
    
    directories = [
        "data",
        "data/keys",
        "data/logs",
        "data/cache",
        "data/credentials",
    ]
    
    for dir_path in directories:
        path = Path(dir_path)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            print(f"  ✅ 创建 {dir_path}/")
        else:
            print(f"  ℹ️  {dir_path}/ 已存在")
    
    return True

def configure_github_token():
    """配置GitHub Token"""
    print_step(6, "配置GitHub Token")
    
    env_file = Path(".env")
    env_content = env_file.read_text()
    
    if "ghp_your_token_here" in env_content or "GITHUB_TOKENS=" not in env_content:
        print_warning("需要配置GitHub Token")
        print("\n获取GitHub Token的步骤:")
        print("1. 访问 https://github.com/settings/tokens")
        print("2. 点击 'Generate new token (classic)'")
        print("3. 选择权限: repo, read:org")
        print("4. 生成并复制token")
        print("")
        
        token = input("请输入您的GitHub Token (或按Enter跳过): ").strip()
        
        if token and token.startswith("ghp_"):
            # 更新.env文件
            env_content = env_content.replace("ghp_your_token_here", token)
            env_file.write_text(env_content)
            print_success("GitHub Token已配置")
            return True
        else:
            print_warning("跳过GitHub Token配置")
            print_info("稍后请编辑.env文件添加您的Token")
            return False
    else:
        print_success("GitHub Token已配置")
        return True

def test_setup():
    """测试设置"""
    print_step(7, "测试环境")
    
    # 测试导入
    try:
        # 激活虚拟环境的Python
        if platform.system() == "Windows":
            python_cmd = "venv\\Scripts\\python.exe"
        else:
            python_cmd = "venv/bin/python"
        
        # 测试导入核心模块
        test_script = """
import sys
sys.path.insert(0, '.')
try:
    import google.generativeai
    from dotenv import load_dotenv
    import requests
    print("SUCCESS")
except ImportError as e:
    print(f"FAILED: {e}")
"""
        
        result = subprocess.run([python_cmd, "-c", test_script], 
                              capture_output=True, text=True)
        
        if "SUCCESS" in result.stdout:
            print_success("环境测试通过")
            return True
        else:
            print_error("环境测试失败")
            print(result.stdout)
            return False
            
    except Exception as e:
        print_error(f"测试失败: {e}")
        return False

def show_next_steps():
    """显示下一步操作"""
    print_header("设置完成")
    
    print(f"{Colors.GREEN}{Colors.BOLD}✅ 环境设置成功！{Colors.RESET}\n")
    
    print(f"{Colors.BOLD}激活虚拟环境:{Colors.RESET}")
    if platform.system() == "Windows":
        print(f"  {Colors.BLUE}venv\\Scripts\\activate{Colors.RESET}")
    else:
        print(f"  {Colors.BLUE}source venv/bin/activate{Colors.RESET}")
    
    print(f"\n{Colors.BOLD}运行扫描器:{Colors.RESET}")
    print(f"  {Colors.BLUE}python scanner_launcher.py{Colors.RESET}")
    
    print(f"\n{Colors.BOLD}或直接运行:{Colors.RESET}")
    print(f"  {Colors.BLUE}python app/api_key_scanner_super.py{Colors.RESET}")
    
    print(f"\n{Colors.BOLD}测试环境:{Colors.RESET}")
    print(f"  {Colors.BLUE}python test_environment.py{Colors.RESET}")
    
    print(f"\n{Colors.BOLD}重要提醒:{Colors.RESET}")
    print(f"  1. 确保已在.env文件中配置GitHub Token")
    print(f"  2. 根据需要编辑queries.txt文件")
    print(f"  3. 如需代理，在.env中配置PROXY")

def main():
    """主函数"""
    print_header("快速环境设置工具")
    
    print(f"{Colors.BOLD}系统信息:{Colors.RESET}")
    print(f"  操作系统: {platform.system()} {platform.release()}")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  当前目录: {os.getcwd()}\n")
    
    # 执行设置步骤
    steps = [
        ("检查Python版本", check_python_version),
        ("创建虚拟环境", create_virtual_environment),
        ("安装依赖", install_dependencies),
        ("设置配置文件", setup_config_files),
        ("创建目录结构", create_directories),
        ("配置GitHub Token", configure_github_token),
        ("测试环境", test_setup),
    ]
    
    failed = False
    for i, (description, func) in enumerate(steps, 1):
        if not func():
            print_error(f"步骤 {i} 失败: {description}")
            failed = True
            break
    
    if not failed:
        show_next_steps()
        return 0
    else:
        print(f"\n{Colors.RED}设置未完成，请解决上述问题后重试{Colors.RESET}")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}用户中断{Colors.RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}发生错误: {e}{Colors.RESET}")
        sys.exit(1)