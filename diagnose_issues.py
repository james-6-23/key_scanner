#!/usr/bin/env python3
"""
诊断工具 - 检查Token配置和数据文件状态
帮助解决：
1. Token数量不一致问题
2. 数据文件未生成问题
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common.Logger import logger
from common.config import Config


def check_token_files():
    """检查Token配置文件"""
    print("\n" + "="*60)
    print("🔍 TOKEN CONFIGURATION CHECK")
    print("="*60)
    
    # 1. 检查环境变量中的Token
    env_tokens = os.getenv('GITHUB_TOKENS', '')
    env_token_count = 0
    if env_tokens:
        env_token_list = [t.strip() for t in env_tokens.split(',') if t.strip()]
        env_token_count = len(env_token_list)
        print(f"✅ Environment variable GITHUB_TOKENS: {env_token_count} tokens found")
    else:
        print("❌ Environment variable GITHUB_TOKENS: Not set or empty")
    
    # 2. 检查github_tokens.txt文件
    tokens_file = "github_tokens.txt"
    file_token_count = 0
    file_tokens = []
    
    if os.path.exists(tokens_file):
        with open(tokens_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    file_tokens.append(line)
            file_token_count = len(file_tokens)
        print(f"✅ File {tokens_file}: {file_token_count} tokens found")
        
        # 验证token格式
        valid_tokens = 0
        for token in file_tokens:
            if token.startswith('ghp_') or token.startswith('github_pat_') or len(token) == 40:
                valid_tokens += 1
            else:
                print(f"   ⚠️ Invalid token format: {token[:10]}...")
        
        if valid_tokens != file_token_count:
            print(f"   ⚠️ Only {valid_tokens}/{file_token_count} tokens have valid format")
    else:
        print(f"❌ File {tokens_file}: Not found")
        print(f"   💡 Create {tokens_file} and add your GitHub tokens (one per line)")
    
    # 3. 检查.env文件
    env_file = ".env"
    if os.path.exists(env_file):
        print(f"✅ File {env_file}: Found")
        with open(env_file, 'r') as f:
            content = f.read()
            if 'GITHUB_TOKENS=' in content:
                print(f"   ✅ GITHUB_TOKENS variable defined in .env")
            else:
                print(f"   ❌ GITHUB_TOKENS variable not found in .env")
    else:
        print(f"⚠️ File {env_file}: Not found (optional)")
    
    # 4. 检查配置中的Token模式
    print(f"\n📋 Configuration:")
    print(f"   USE_EXTERNAL_TOKEN_FILE: {Config.USE_EXTERNAL_TOKEN_FILE}")
    print(f"   GITHUB_TOKENS_FILE: {Config.GITHUB_TOKENS_FILE}")
    
    # 5. 建议
    print(f"\n💡 Recommendations:")
    if Config.USE_EXTERNAL_TOKEN_FILE:
        print(f"   You are using external file mode")
        print(f"   Make sure {Config.GITHUB_TOKENS_FILE} exists and contains valid tokens")
    else:
        print(f"   You are using environment variable mode")
        print(f"   Make sure GITHUB_TOKENS is set in .env or environment")
    
    return {
        'env_tokens': env_token_count,
        'file_tokens': file_token_count,
        'mode': 'file' if Config.USE_EXTERNAL_TOKEN_FILE else 'env'
    }


def check_data_files():
    """检查数据文件状态"""
    print("\n" + "="*60)
    print("📁 DATA FILES CHECK")
    print("="*60)
    
    data_dir = Config.DATA_PATH
    print(f"Data directory: {data_dir}")
    
    if not os.path.exists(data_dir):
        print(f"❌ Data directory does not exist!")
        return
    
    # 检查今天的数据文件
    today = datetime.now().strftime('%Y%m%d')
    
    files_to_check = [
        (f"keys_valid_{today}.txt", "Valid keys"),
        (f"rate_limited_{today}.txt", "Rate limited keys"),
        (f"keys_valid_detail_{today}.log", "Valid keys details"),
        (f"rate_limited_detail_{today}.log", "Rate limited details"),
        ("checkpoint.json", "Checkpoint"),
        ("scanned_shas.txt", "Scanned SHAs")
    ]
    
    found_files = []
    for filename, description in files_to_check:
        filepath = os.path.join(data_dir, filename)
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            found_files.append(filepath)
            
            # 读取文件内容统计
            if filename.endswith('.txt') and 'keys_valid' in filename:
                with open(filepath, 'r') as f:
                    lines = f.readlines()
                    key_count = len([l for l in lines if l.strip()])
                print(f"✅ {description}: {filename} ({size} bytes, {key_count} keys)")
            elif filename == 'checkpoint.json':
                with open(filepath, 'r') as f:
                    checkpoint = json.load(f)
                    queries = len(checkpoint.get('processed_queries', []))
                    last_scan = checkpoint.get('last_scan_time', 'Never')
                print(f"✅ {description}: {filename} ({size} bytes)")
                print(f"   Last scan: {last_scan}")
                print(f"   Processed queries: {queries}")
            elif filename == 'scanned_shas.txt':
                with open(filepath, 'r') as f:
                    lines = f.readlines()
                    sha_count = len([l for l in lines if l.strip() and not l.startswith('#')])
                print(f"✅ {description}: {filename} ({size} bytes, {sha_count} SHAs)")
            else:
                print(f"✅ {description}: {filename} ({size} bytes)")
        else:
            print(f"❌ {description}: {filename} (not found)")
    
    # 检查历史数据文件
    print(f"\n📅 Historical data files:")
    all_valid_keys = []
    all_rate_limited = []
    
    for file in os.listdir(data_dir):
        if file.startswith('keys_valid_') and file.endswith('.txt'):
            filepath = os.path.join(data_dir, file)
            with open(filepath, 'r') as f:
                keys = [l.strip() for l in f.readlines() if l.strip()]
                all_valid_keys.extend(keys)
                if keys:
                    print(f"   {file}: {len(keys)} keys")
        elif file.startswith('rate_limited_') and file.endswith('.txt'):
            filepath = os.path.join(data_dir, file)
            with open(filepath, 'r') as f:
                keys = [l.strip() for l in f.readlines() if l.strip()]
                all_rate_limited.extend(keys)
    
    print(f"\n📊 Summary:")
    print(f"   Total valid keys found (all time): {len(set(all_valid_keys))}")
    print(f"   Total rate limited keys (all time): {len(set(all_rate_limited))}")
    
    return found_files


def check_queries_file():
    """检查查询文件"""
    print("\n" + "="*60)
    print("🔍 QUERIES FILE CHECK")
    print("="*60)
    
    queries_file = Config.QUERIES_FILE
    print(f"Queries file: {queries_file}")
    
    if os.path.exists(queries_file):
        with open(queries_file, 'r') as f:
            lines = f.readlines()
            queries = [l.strip() for l in lines if l.strip() and not l.startswith('#')]
        print(f"✅ Found {len(queries)} queries")
        
        # 显示前5个查询
        print(f"\n   First few queries:")
        for i, q in enumerate(queries[:5], 1):
            print(f"   {i}. {q[:50]}..." if len(q) > 50 else f"   {i}. {q}")
    else:
        print(f"❌ Queries file not found!")
        print(f"   💡 Copy queries.example to {queries_file} to get started")
        
        # 检查示例文件
        if os.path.exists("queries.example"):
            print(f"   ✅ queries.example found - you can use it as template")
        else:
            print(f"   ❌ queries.example also not found")


def test_token_manager():
    """测试Token管理器"""
    print("\n" + "="*60)
    print("🧪 TOKEN MANAGER TEST")
    print("="*60)
    
    try:
        from utils.github_client import GitHubClient
        
        # 创建GitHub客户端实例
        github_client = GitHubClient.create_instance(use_token_manager=True)
        
        # 获取Token状态
        status = github_client.get_token_status()
        
        print(f"✅ Token Manager initialized successfully")
        print(f"   Total tokens: {status.get('total_tokens', 0)}")
        print(f"   Active tokens: {status.get('active_tokens', 0)}")
        print(f"   Total remaining calls: {status.get('total_remaining_calls', 'N/A')}")
        
        # 显示每个token的状态
        if 'tokens' in status:
            print(f"\n   Token details:")
            for token_info in status['tokens']:
                print(f"   - {token_info['token']}: {token_info['remaining']} calls remaining")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to initialize Token Manager: {e}")
        import traceback
        traceback.print_exc()
        return False


def suggest_fixes():
    """提供修复建议"""
    print("\n" + "="*60)
    print("💡 TROUBLESHOOTING GUIDE")
    print("="*60)
    
    print("""
1. 如果Token数量不一致：
   - 确保所有工具使用相同的Token源
   - 如果使用文件模式，检查 github_tokens.txt
   - 如果使用环境变量模式，检查 .env 文件中的 GITHUB_TOKENS
   
2. 如果数据文件未生成：
   - 使用改进版扫描器: python app/api_key_scanner_improved.py
   - 确保有写入权限到 data/ 目录
   - 检查是否有有效的查询在 queries.txt
   
3. 如果程序中断导致数据丢失：
   - 改进版会实时保存数据
   - 使用 Ctrl+C 优雅退出而不是强制终止
   - 检查 data/ 目录中的部分文件
   
4. 快速测试：
   python -c "from utils.github_client import GitHubClient; gc = GitHubClient.create_instance(True); print(gc.get_token_status())"
    """)


def main():
    """主函数"""
    print("="*60)
    print("🔧 KEY SCANNER DIAGNOSTIC TOOL")
    print("="*60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 检查Token配置
    token_status = check_token_files()
    
    # 2. 检查数据文件
    data_files = check_data_files()
    
    # 3. 检查查询文件
    check_queries_file()
    
    # 4. 测试Token管理器
    manager_ok = test_token_manager()
    
    # 5. 提供修复建议
    suggest_fixes()
    
    # 6. 总结
    print("\n" + "="*60)
    print("📋 DIAGNOSIS SUMMARY")
    print("="*60)
    
    issues = []
    
    if token_status['file_tokens'] == 0 and token_status['env_tokens'] == 0:
        issues.append("No tokens configured")
    
    if not data_files:
        issues.append("No data files found")
    
    if not manager_ok:
        issues.append("Token Manager initialization failed")
    
    if issues:
        print("❌ Issues found:")
        for issue in issues:
            print(f"   - {issue}")
    else:
        print("✅ Everything looks good!")
    
    print("\n💡 Next steps:")
    print("1. Fix any issues identified above")
    print("2. Run the improved scanner: python app/api_key_scanner_improved.py")
    print("3. Or use the unified launcher: ./unified_launcher.sh (Linux/Mac) or unified_launcher.bat (Windows)")


if __name__ == "__main__":
    main()