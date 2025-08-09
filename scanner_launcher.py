#!/usr/bin/env python3
"""
API密钥扫描器启动器
交互式选择运行不同版本的扫描器，支持多API类型
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List

# ANSI颜色代码
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_banner():
    """打印启动横幅"""
    banner = f"""
{Colors.CYAN}{'='*60}
{Colors.BOLD}🚀 API密钥扫描器 - 启动器{Colors.ENDC}
{Colors.CYAN}{'='*60}{Colors.ENDC}
    """
    print(banner)


def print_main_menu():
    """打印主菜单"""
    menu = f"""
{Colors.GREEN}请选择操作：{Colors.ENDC}

  {Colors.BOLD}1.{Colors.ENDC} 快速扫描（默认Gemini）
      {Colors.BLUE}• 使用默认配置扫描Gemini API密钥{Colors.ENDC}

  {Colors.BOLD}2.{Colors.ENDC} 选择API类型扫描 {Colors.WARNING}[新功能]{Colors.ENDC}
      {Colors.BLUE}• 选择要扫描的API类型
      • 支持多种API：OpenAI、Anthropic等{Colors.ENDC}

  {Colors.BOLD}3.{Colors.ENDC} 选择扫描器版本
      {Colors.BLUE}• 普通版/改进版/超级版{Colors.ENDC}

  {Colors.BOLD}4.{Colors.ENDC} 通用API扫描器 {Colors.WARNING}[新功能]{Colors.ENDC}
      {Colors.BLUE}• 使用通用扫描器
      • 支持自定义API模式{Colors.ENDC}

  {Colors.BOLD}5.{Colors.ENDC} 查看配置状态
      {Colors.BLUE}• 检查环境配置
      • 验证依赖安装{Colors.ENDC}

  {Colors.BOLD}6.{Colors.ENDC} 运行诊断工具
      {Colors.BLUE}• 系统诊断
      • 问题排查{Colors.ENDC}

  {Colors.BOLD}7.{Colors.ENDC} 管理查询模板 {Colors.WARNING}[新功能]{Colors.ENDC}
      {Colors.BLUE}• 查看/选择查询模板
      • 管理config/queries/目录{Colors.ENDC}

  {Colors.BOLD}0.{Colors.ENDC} 退出

{Colors.CYAN}{'='*60}{Colors.ENDC}
"""
    print(menu)


def print_scanner_menu():
    """打印扫描器版本选择菜单"""
    menu = f"""
{Colors.GREEN}请选择扫描器版本：{Colors.ENDC}

  {Colors.BOLD}1.{Colors.ENDC} 普通版扫描器 (api_key_scanner.py)
     {Colors.BLUE}• 基础功能，快速测试
     • 并行验证
     • 适合初次使用{Colors.ENDC}

  {Colors.BOLD}2.{Colors.ENDC} 改进版扫描器 (api_key_scanner_improved.py)
     {Colors.BLUE}• 数据持久化
     • 优雅退出
     • 适合生产环境{Colors.ENDC}

  {Colors.BOLD}3.{Colors.ENDC} 超级版扫描器 (api_key_scanner_super.py) {Colors.WARNING}[推荐]{Colors.ENDC}
     {Colors.BLUE}• 高级凭证管理系统
     • 8种负载均衡策略
     • 自愈机制
     • Token自动收集（可选）
     • 实时监控仪表板
     • 支持多API类型
     • 适合企业级部署{Colors.ENDC}

  {Colors.BOLD}0.{Colors.ENDC} 返回主菜单
"""
    print(menu)


def print_api_menu():
    """打印API类型选择菜单"""
    menu = f"""
{Colors.GREEN}请选择要扫描的API类型：{Colors.ENDC}

  {Colors.BOLD}1.{Colors.ENDC} Gemini (Google) {Colors.WARNING}[默认]{Colors.ENDC}
     {Colors.BLUE}• AIzaSy... 格式{Colors.ENDC}

  {Colors.BOLD}2.{Colors.ENDC} OpenAI (GPT)
     {Colors.BLUE}• sk-... 格式{Colors.ENDC}

  {Colors.BOLD}3.{Colors.ENDC} Anthropic (Claude)
     {Colors.BLUE}• sk-ant-api... 格式{Colors.ENDC}

  {Colors.BOLD}4.{Colors.ENDC} AWS Access Keys
     {Colors.BLUE}• AKIA... 格式{Colors.ENDC}

  {Colors.BOLD}5.{Colors.ENDC} Azure OpenAI
     {Colors.BLUE}• 32位十六进制格式{Colors.ENDC}

  {Colors.BOLD}6.{Colors.ENDC} Cohere
     {Colors.BLUE}• co-... 格式{Colors.ENDC}

  {Colors.BOLD}7.{Colors.ENDC} Hugging Face
     {Colors.BLUE}• hf_... 格式{Colors.ENDC}

  {Colors.BOLD}8.{Colors.ENDC} 多个API同时扫描
     {Colors.BLUE}• 选择多个API类型{Colors.ENDC}

  {Colors.BOLD}9.{Colors.ENDC} 自定义API
     {Colors.BLUE}• 使用自定义配置{Colors.ENDC}

  {Colors.BOLD}0.{Colors.ENDC} 返回主菜单
"""
    print(menu)


def get_api_types() -> dict:
    """获取API类型映射"""
    return {
        '1': 'gemini',
        '2': 'openai',
        '3': 'anthropic',
        '4': 'aws',
        '5': 'azure',
        '6': 'cohere',
        '7': 'huggingface'
    }


def check_environment() -> bool:
    """检查环境配置"""
    print(f"\n{Colors.CYAN}检查环境配置...{Colors.ENDC}")
    
    issues = []
    
    # 检查Python版本
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        issues.append(f"Python版本过低: {sys.version} (需要3.8+)")
    else:
        print(f"{Colors.GREEN}✓{Colors.ENDC} Python版本: {sys.version.split()[0]}")
    
    # 检查.env文件
    env_file = Path(".env")
    if not env_file.exists():
        issues.append(".env文件不存在")
        print(f"{Colors.FAIL}✗{Colors.ENDC} .env文件: 未找到")
    else:
        print(f"{Colors.GREEN}✓{Colors.ENDC} .env文件: 存在")
        
        # 检查必要的环境变量
        with open(env_file, 'r') as f:
            content = f.read()
            if 'GITHUB_TOKENS' not in content:
                issues.append(".env中未配置GITHUB_TOKENS")
                print(f"{Colors.WARNING}⚠{Colors.ENDC} GITHUB_TOKENS: 未配置")
            else:
                print(f"{Colors.GREEN}✓{Colors.ENDC} GITHUB_TOKENS: 已配置")
    
    # 检查queries.txt
    queries_file = Path("queries.txt")
    if not queries_file.exists():
        issues.append("queries.txt文件不存在")
        print(f"{Colors.FAIL}✗{Colors.ENDC} queries.txt: 未找到")
    else:
        print(f"{Colors.GREEN}✓{Colors.ENDC} queries.txt: 存在")
    
    # 检查config/api_patterns.json
    api_config = Path("config/api_patterns.json")
    if api_config.exists():
        print(f"{Colors.GREEN}✓{Colors.ENDC} API配置文件: 存在")
    else:
        print(f"{Colors.WARNING}⚠{Colors.ENDC} API配置文件: 未找到（多API扫描需要）")
    
    # 检查查询模板目录
    queries_dir = Path("config/queries")
    if queries_dir.exists():
        query_files = list(queries_dir.glob("*.txt"))
        print(f"{Colors.GREEN}✓{Colors.ENDC} 查询模板: {len(query_files)} 个文件")
    else:
        print(f"{Colors.WARNING}⚠{Colors.ENDC} 查询模板目录: 未找到")
    
    # 检查依赖
    try:
        import requests
        print(f"{Colors.GREEN}✓{Colors.ENDC} requests库: 已安装")
    except ImportError:
        issues.append("requests库未安装")
        print(f"{Colors.FAIL}✗{Colors.ENDC} requests库: 未安装")
    
    try:
        import cryptography
        print(f"{Colors.GREEN}✓{Colors.ENDC} cryptography库: 已安装")
    except ImportError:
        print(f"{Colors.WARNING}⚠{Colors.ENDC} cryptography库: 未安装（超级版需要）")
    
    # 显示结果
    if issues:
        print(f"\n{Colors.WARNING}发现以下问题：{Colors.ENDC}")
        for issue in issues:
            print(f"  • {issue}")
        print(f"\n{Colors.BLUE}建议解决方案：{Colors.ENDC}")
        if ".env文件不存在" in issues:
            print("  1. 复制环境变量示例: cp env.example .env")
            print("  2. 编辑.env文件，添加GitHub tokens")
        if "queries.txt文件不存在" in issues:
            print("  1. 复制查询示例: cp queries.example queries.txt")
            print("  2. 或从模板创建: cp config/queries/gemini.txt queries.txt")
        if "requests库未安装" in issues:
            print("  1. 安装依赖: pip install -r requirements.txt")
        return False
    else:
        print(f"\n{Colors.GREEN}✅ 环境配置正常！{Colors.ENDC}")
        return True


def setup_query_file(api_type: str):
    """设置查询文件"""
    query_source = Path(f"config/queries/{api_type}.txt")
    query_dest = Path("queries.txt")
    
    if query_source.exists():
        shutil.copy(query_source, query_dest)
        print(f"{Colors.GREEN}✓ 已设置{api_type}查询模板{Colors.ENDC}")
    else:
        print(f"{Colors.WARNING}⚠ {api_type}查询模板不存在，使用默认{Colors.ENDC}")
        # 尝试使用gemini作为默认
        gemini_source = Path("config/queries/gemini.txt")
        if gemini_source.exists():
            shutil.copy(gemini_source, query_dest)


def run_scanner(scanner_type: int, api_types: str = None):
    """运行指定版本的扫描器"""
    scanners = {
        1: ("app/api_key_scanner.py", "普通版"),
        2: ("app/api_key_scanner_improved.py", "改进版"),
        3: ("app/api_key_scanner_super.py", "超级版")
    }
    
    if scanner_type not in scanners:
        print(f"{Colors.FAIL}无效的选择！{Colors.ENDC}")
        return
    
    scanner_file, scanner_name = scanners[scanner_type]
    scanner_path = Path(scanner_file)
    
    if not scanner_path.exists():
        print(f"{Colors.FAIL}错误：{scanner_file} 文件不存在！{Colors.ENDC}")
        return
    
    print(f"\n{Colors.CYAN}正在启动{scanner_name}扫描器...{Colors.ENDC}")
    print(f"{Colors.BLUE}文件: {scanner_file}{Colors.ENDC}")
    if api_types:
        print(f"{Colors.BLUE}API类型: {api_types}{Colors.ENDC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.ENDC}\n")
    
    try:
        # 构建命令
        cmd = [sys.executable, scanner_file]
        if api_types and scanner_type == 3:  # 只有超级版支持--api-types
            cmd.extend(['--api-types', api_types])
        
        # 运行扫描器
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n{Colors.FAIL}扫描器运行出错: {e}{Colors.ENDC}")
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}用户中断运行{Colors.ENDC}")


def run_universal_scanner(api_types: str = None):
    """运行通用API扫描器"""
    scanner_file = "app/api_scanner_universal.py"
    scanner_path = Path(scanner_file)
    
    if not scanner_path.exists():
        print(f"{Colors.FAIL}错误：通用扫描器不存在！{Colors.ENDC}")
        return
    
    print(f"\n{Colors.CYAN}正在启动通用API扫描器...{Colors.ENDC}")
    if api_types:
        print(f"{Colors.BLUE}API类型: {api_types}{Colors.ENDC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.ENDC}\n")
    
    try:
        cmd = [sys.executable, scanner_file]
        if api_types:
            cmd.extend(['--api-types', api_types])
        
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n{Colors.FAIL}扫描器运行出错: {e}{Colors.ENDC}")
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}用户中断运行{Colors.ENDC}")


def manage_queries():
    """管理查询模板"""
    queries_dir = Path("config/queries")
    
    if not queries_dir.exists():
        print(f"{Colors.FAIL}查询模板目录不存在！{Colors.ENDC}")
        return
    
    print(f"\n{Colors.CYAN}查询模板管理{Colors.ENDC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.ENDC}")
    
    # 列出所有查询文件
    query_files = sorted(queries_dir.glob("*.txt"))
    
    if not query_files:
        print(f"{Colors.WARNING}没有找到查询模板文件{Colors.ENDC}")
        return
    
    print(f"\n{Colors.GREEN}可用的查询模板：{Colors.ENDC}")
    for i, file in enumerate(query_files, 1):
        # 获取文件大小和行数
        size = file.stat().st_size / 1024  # KB
        with open(file, 'r', encoding='utf-8') as f:
            lines = len(f.readlines())
        
        print(f"  {Colors.BOLD}{i}.{Colors.ENDC} {file.stem}")
        print(f"     {Colors.BLUE}• 文件: {file.name}")
        print(f"     • 大小: {size:.1f} KB")
        print(f"     • 行数: {lines} 行{Colors.ENDC}")
    
    print(f"\n{Colors.GREEN}选择操作：{Colors.ENDC}")
    print(f"  {Colors.BOLD}1.{Colors.ENDC} 设置为当前查询文件")
    print(f"  {Colors.BOLD}2.{Colors.ENDC} 查看文件内容")
    print(f"  {Colors.BOLD}3.{Colors.ENDC} 合并多个查询文件")
    print(f"  {Colors.BOLD}0.{Colors.ENDC} 返回")
    
    choice = input(f"\n{Colors.BOLD}请选择操作: {Colors.ENDC}").strip()
    
    if choice == '1':
        file_num = input(f"{Colors.BOLD}选择文件编号: {Colors.ENDC}").strip()
        try:
            idx = int(file_num) - 1
            if 0 <= idx < len(query_files):
                shutil.copy(query_files[idx], "queries.txt")
                print(f"{Colors.GREEN}✓ 已设置 {query_files[idx].name} 为当前查询文件{Colors.ENDC}")
        except (ValueError, IndexError):
            print(f"{Colors.FAIL}无效的选择{Colors.ENDC}")
    
    elif choice == '2':
        file_num = input(f"{Colors.BOLD}选择文件编号: {Colors.ENDC}").strip()
        try:
            idx = int(file_num) - 1
            if 0 <= idx < len(query_files):
                with open(query_files[idx], 'r', encoding='utf-8') as f:
                    content = f.read()
                print(f"\n{Colors.CYAN}文件内容 ({query_files[idx].name}):{Colors.ENDC}")
                print(content[:1000])  # 只显示前1000字符
                if len(content) > 1000:
                    print(f"{Colors.BLUE}... (文件太长，只显示前1000字符){Colors.ENDC}")
        except (ValueError, IndexError):
            print(f"{Colors.FAIL}无效的选择{Colors.ENDC}")
    
    elif choice == '3':
        file_nums = input(f"{Colors.BOLD}输入要合并的文件编号（逗号分隔）: {Colors.ENDC}").strip()
        try:
            indices = [int(n.strip()) - 1 for n in file_nums.split(',')]
            merged_content = []
            
            for idx in indices:
                if 0 <= idx < len(query_files):
                    with open(query_files[idx], 'r', encoding='utf-8') as f:
                        merged_content.append(f"# From {query_files[idx].name}\n")
                        merged_content.append(f.read())
                        merged_content.append("\n")
            
            if merged_content:
                with open("queries.txt", 'w', encoding='utf-8') as f:
                    f.writelines(merged_content)
                print(f"{Colors.GREEN}✓ 已合并查询文件到 queries.txt{Colors.ENDC}")
        except (ValueError, IndexError):
            print(f"{Colors.FAIL}无效的选择{Colors.ENDC}")


def run_diagnostics():
    """运行诊断工具"""
    diag_file = Path("diagnose_issues.py")
    
    if not diag_file.exists():
        print(f"{Colors.FAIL}诊断工具不存在！{Colors.ENDC}")
        return
    
    print(f"\n{Colors.CYAN}运行诊断工具...{Colors.ENDC}")
    
    try:
        subprocess.run([sys.executable, str(diag_file)], check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n{Colors.FAIL}诊断工具运行出错: {e}{Colors.ENDC}")
    except FileNotFoundError:
        print(f"{Colors.FAIL}找不到诊断工具文件{Colors.ENDC}")


def setup_environment():
    """快速设置环境"""
    print(f"\n{Colors.CYAN}快速环境设置向导{Colors.ENDC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.ENDC}")
    
    # 创建.env文件
    if not Path(".env").exists():
        print(f"\n{Colors.BLUE}创建.env文件...{Colors.ENDC}")
        
        # 从env.example复制
        if Path("env.example").exists():
            shutil.copy("env.example", ".env")
            print(f"{Colors.GREEN}✓ 已从env.example创建.env{Colors.ENDC}")
        else:
            # 创建基础.env
            with open(".env", "w") as f:
                f.write("""# GitHub API配置
GITHUB_TOKENS=ghp_your_token_here

# 扫描配置
DATE_RANGE_DAYS=730
HAJIMI_MAX_WORKERS=10

# API类型配置
TARGET_API_TYPES=gemini

# 高级功能（超级版）
CREDENTIAL_AUTO_HARVEST=false
MONITORING_ENABLED=false
""")
            print(f"{Colors.GREEN}✓ 已创建基础.env文件{Colors.ENDC}")
        
        print(f"{Colors.WARNING}⚠ 请编辑.env文件，添加您的GitHub token{Colors.ENDC}")
    
    # 创建queries.txt
    if not Path("queries.txt").exists():
        print(f"\n{Colors.BLUE}创建queries.txt文件...{Colors.ENDC}")
        
        # 优先从config/queries/gemini.txt复制
        if Path("config/queries/gemini.txt").exists():
            shutil.copy("config/queries/gemini.txt", "queries.txt")
            print(f"{Colors.GREEN}✓ 已从config/queries/gemini.txt创建queries.txt{Colors.ENDC}")
        elif Path("queries.example").exists():
            shutil.copy("queries.example", "queries.txt")
            print(f"{Colors.GREEN}✓ 已从queries.example创建queries.txt{Colors.ENDC}")
        else:
            # 创建基础queries
            with open("queries.txt", "w") as f:
                f.write("""AIzaSy in:file
AIzaSy in:file extension:json
AIzaSy in:file filename:.env
""")
            print(f"{Colors.GREEN}✓ 已创建基础queries.txt文件{Colors.ENDC}")
    
    # 创建必要的目录
    dirs = ["data", "data/keys", "data/logs", "logs", "config/queries"]
    for dir_name in dirs:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"{Colors.GREEN}✓ 创建目录: {dir_name}{Colors.ENDC}")
    
    print(f"\n{Colors.GREEN}环境设置完成！{Colors.ENDC}")
    print(f"{Colors.BLUE}下一步：{Colors.ENDC}")
    print("  1. 编辑.env文件，添加GitHub token")
    print("  2. 运行扫描器")


def handle_api_selection():
    """处理API类型选择"""
    print_api_menu()
    
    api_types_map = get_api_types()
    
    choice = input(f"{Colors.BOLD}请选择API类型: {Colors.ENDC}").strip()
    
    if choice == '0':
        return None
    
    elif choice in api_types_map:
        api_type = api_types_map[choice]
        setup_query_file(api_type)
        
        # 询问使用哪个扫描器
        print(f"\n{Colors.GREEN}使用哪个扫描器？{Colors.ENDC}")
        print(f"  {Colors.BOLD}1.{Colors.ENDC} 超级版扫描器（推荐）")
        print(f"  {Colors.BOLD}2.{Colors.ENDC} 通用API扫描器")
        
        scanner_choice = input(f"{Colors.BOLD}请选择: {Colors.ENDC}").strip()
        
        if scanner_choice == '1':
            run_scanner(3, api_type)  # 超级版
        elif scanner_choice == '2':
            run_universal_scanner(api_type)
    
    elif choice == '8':
        # 多个API同时扫描
        print(f"\n{Colors.GREEN}选择要扫描的API类型（逗号分隔编号）：{Colors.ENDC}")
        for num, api in api_types_map.items():
            print(f"  {num}. {api}")
        
        selections = input(f"{Colors.BOLD}请输入编号: {Colors.ENDC}").strip()
        
        selected_apis = []
        for num in selections.split(','):
            num = num.strip()
            if num in api_types_map:
                selected_apis.append(api_types_map[num])
        
        if selected_apis:
            # 合并查询文件
            merged_content = []
            for api in selected_apis:
                query_file = Path(f"config/queries/{api}.txt")
                if query_file.exists():
                    with open(query_file, 'r', encoding='utf-8') as f:
                        merged_content.append(f"# {api.upper()} Queries\n")
                        merged_content.append(f.read())
                        merged_content.append("\n")
            
            with open("queries.txt", 'w', encoding='utf-8') as f:
                f.writelines(merged_content)
            
            api_types_str = ','.join(selected_apis)
            print(f"{Colors.GREEN}✓ 准备扫描: {api_types_str}{Colors.ENDC}")
            
            run_scanner(3, api_types_str)  # 使用超级版
    
    elif choice == '9':
        # 自定义API
        print(f"{Colors.WARNING}请确保已配置 config/api_patterns.json{Colors.ENDC}")
        api_type = input(f"{Colors.BOLD}输入自定义API名称: {Colors.ENDC}").strip()
        if api_type:
            run_universal_scanner(api_type)


def handle_scanner_selection():
    """处理扫描器版本选择"""
    print_scanner_menu()
    
    choice = input(f"{Colors.BOLD}请选择扫描器版本: {Colors.ENDC}").strip()
    
    if choice == '0':
        return
    
    try:
        scanner_type = int(choice)
        if 1 <= scanner_type <= 3:
            if check_environment():
                run_scanner(scanner_type)
            else:
                if input(f"\n{Colors.WARNING}是否先设置环境？(y/n): {Colors.ENDC}").lower() == 'y':
                    setup_environment()
    except ValueError:
        print(f"{Colors.FAIL}无效的选择{Colors.ENDC}")


def main():
    """主函数"""
    print_banner()
    
    while True:
        print_main_menu()
        
        try:
            choice = input(f"{Colors.BOLD}请输入选择 (0-7): {Colors.ENDC}").strip()
            
            if choice == '0':
                print(f"\n{Colors.GREEN}感谢使用！再见！{Colors.ENDC}")
                break
            
            elif choice == '1':
                # 快速扫描Gemini
                if check_environment():
                    setup_query_file('gemini')
                    run_scanner(3, 'gemini')  # 使用超级版
                else:
                    if input(f"\n{Colors.WARNING}是否先设置环境？(y/n): {Colors.ENDC}").lower() == 'y':
                        setup_environment()
            
            elif choice == '2':
                # 选择API类型扫描
                handle_api_selection()
            
            elif choice == '3':
                # 选择扫描器版本
                handle_scanner_selection()
            
            elif choice == '4':
                # 通用API扫描器
                api_types = input(f"{Colors.BOLD}输入API类型（默认gemini）: {Colors.ENDC}").strip() or 'gemini'
                run_universal_scanner(api_types)
            
            elif choice == '5':
                # 查看配置状态
                check_environment()
                input(f"\n{Colors.BLUE}按Enter继续...{Colors.ENDC}")
            
            elif choice == '6':
                # 运行诊断工具
                run_diagnostics()
                input(f"\n{Colors.BLUE}按Enter继续...{Colors.ENDC}")
            
            elif choice == '7':
                # 管理查询模板
                manage_queries()
                input(f"\n{Colors.BLUE}按Enter继续...{Colors.ENDC}")
            
            else:
                print(f"{Colors.FAIL}无效的选择，请输入0-7之间的数字{Colors.ENDC}")
                
        except KeyboardInterrupt:
            print(f"\n\n{Colors.WARNING}用户中断{Colors