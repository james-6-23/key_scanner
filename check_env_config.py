#!/usr/bin/env python3
"""
检查 .env 配置文件的兼容性
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

def check_config():
    """检查配置项"""
    print("=" * 60)
    print("🔍 检查 .env 配置文件")
    print("=" * 60)
    
    # 必需的配置项
    required_configs = {
        'GITHUB_TOKENS': '环境变量中的GitHub tokens（如果USE_EXTERNAL_TOKEN_FILE=false）',
        'GITHUB_TOKENS_FILE': 'GitHub tokens文件路径',
        'USE_EXTERNAL_TOKEN_FILE': '是否使用外部token文件',
        'DATA_PATH': '数据存储路径',
        'QUERIES_FILE': '查询文件路径',
    }
    
    # 重要的配置项
    important_configs = {
        'PROXY': '代理服务器配置',
        'HAJIMI_CHECK_MODEL': 'Gemini验证模型',
        'CREDENTIAL_AUTO_HARVEST': 'Token自动收集',
        'MONITORING_ENABLED': '监控仪表板',
        'DEFAULT_SCANNER_VERSION': '默认扫描器版本',
        'TARGET_API_TYPES': '目标API类型',
    }
    
    print("\n✅ 必需配置项：")
    missing_required = []
    for key, desc in required_configs.items():
        value = os.getenv(key)
        if value:
            print(f"  {key}: {value[:50]}{'...' if len(str(value)) > 50 else ''}")
        else:
            print(f"  {key}: ❌ 未设置 ({desc})")
            missing_required.append(key)
    
    print("\n📋 重要配置项：")
    for key, desc in important_configs.items():
        value = os.getenv(key)
        if value:
            print(f"  {key}: {value[:50]}{'...' if len(str(value)) > 50 else ''}")
        else:
            print(f"  {key}: ⚠️ 未设置 ({desc})")
    
    # 检查文件存在性
    print("\n📁 文件检查：")
    
    # 检查 token 文件
    use_external = os.getenv('USE_EXTERNAL_TOKEN_FILE', 'false').lower() in ('true', '1', 'yes')
    if use_external:
        token_file = os.getenv('GITHUB_TOKENS_FILE', 'github_tokens.txt')
        if Path(token_file).exists():
            with open(token_file, 'r') as f:
                token_count = sum(1 for line in f if line.strip() and not line.startswith('#'))
            print(f"  {token_file}: ✅ 存在 ({token_count} 个tokens)")
        else:
            print(f"  {token_file}: ❌ 不存在")
    
    # 检查查询文件
    queries_file = os.getenv('QUERIES_FILE', 'queries.txt')
    if Path(queries_file).exists():
        with open(queries_file, 'r') as f:
            query_count = sum(1 for line in f if line.strip() and not line.startswith('#'))
        print(f"  {queries_file}: ✅ 存在 ({query_count} 个查询)")
    else:
        print(f"  {queries_file}: ❌ 不存在")
    
    # 检查数据目录
    data_path = os.getenv('DATA_PATH', './data')
    if Path(data_path).exists():
        print(f"  {data_path}/: ✅ 存在")
    else:
        print(f"  {data_path}/: ⚠️ 不存在（将自动创建）")
    
    # 特殊配置警告
    print("\n⚠️ 特殊配置警告：")
    
    if os.getenv('CREDENTIAL_AUTO_HARVEST', 'false').lower() == 'true':
        print("  🔍 Token自动收集已启用 - 请确保合法合规使用")
    
    if os.getenv('MONITORING_ENABLED', 'false').lower() == 'true':
        port = os.getenv('MONITORING_PORT', '8080')
        print(f"  📊 监控仪表板已启用 - 将在端口 {port} 运行")
    
    if os.getenv('SKIP_SSL_VERIFY', 'false').lower() == 'true':
        print("  🔓 SSL验证已禁用 - 不建议在生产环境使用")
    
    # 模型版本检查
    model = os.getenv('HAJIMI_CHECK_MODEL', '')
    if model and 'gemini-2.5' in model:
        print(f"  📌 检测到使用 {model}，建议使用 gemini-2.0-flash-exp")
    
    # 加密密钥检查
    encryption_key = os.getenv('ENCRYPTION_KEY', '')
    if encryption_key == '$(openssl rand -base64 32)':
        print("  🔐 加密密钥需要手动生成（Windows不支持命令替换）")
        print("     运行: python -c \"import secrets; print(secrets.token_urlsafe(32))\"")
    
    print("\n" + "=" * 60)
    
    if missing_required:
        print("❌ 缺少必需的配置项，请检查 .env 文件")
        return False
    else:
        print("✅ 配置检查通过")
        return True

if __name__ == "__main__":
    if check_config():
        print("\n下一步：")
        print("1. 如果需要，更新 HAJIMI_CHECK_MODEL 为 gemini-2.0-flash-exp")
        print("2. 如果在 Windows，手动生成 ENCRYPTION_KEY")
        print("3. 运行扫描器：python app/api_key_scanner_super.py")
        sys.exit(0)
    else:
        sys.exit(1)