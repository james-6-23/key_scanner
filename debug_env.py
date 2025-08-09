#!/usr/bin/env python3
"""
调试 .env 文件加载问题
"""

import os
import sys
from pathlib import Path

print("=" * 60)
print("🔍 调试 .env 文件加载")
print("=" * 60)

# 显示当前工作目录
print(f"\n📁 当前工作目录: {os.getcwd()}")

# 列出所有文件（包括隐藏文件）
print("\n📋 当前目录下的所有文件：")
for file in Path('.').iterdir():
    if file.is_file():
        size = file.stat().st_size
        print(f"  {file.name} ({size} 字节)")

# 检查 .env 文件
env_file = Path('.env')
print(f"\n🔍 检查 .env 文件：")
print(f"  存在: {env_file.exists()}")
if env_file.exists():
    print(f"  绝对路径: {env_file.absolute()}")
    print(f"  大小: {env_file.stat().st_size} 字节")
    print(f"  可读: {os.access(env_file, os.R_OK)}")
    
    # 读取并显示内容（隐藏敏感信息）
    print("\n📄 .env 文件内容预览：")
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                line = line.rstrip()
                if not line or line.startswith('#'):
                    print(f"  {i:3d}: {line}")
                elif '=' in line:
                    key, value = line.split('=', 1)
                    # 隐藏敏感值
                    if any(s in key.upper() for s in ['TOKEN', 'KEY', 'AUTH', 'PASSWORD', 'SECRET']):
                        print(f"  {i:3d}: {key}=***")
                    else:
                        print(f"  {i:3d}: {line[:80]}{'...' if len(line) > 80 else ''}")
                else:
                    print(f"  {i:3d}: {line[:80]}{'...' if len(line) > 80 else ''}")
                
                if i >= 20:  # 只显示前20行
                    print("  ... (更多内容省略)")
                    break
    except Exception as e:
        print(f"  ❌ 读取文件时出错: {e}")

# 尝试手动加载 .env
print("\n🔧 尝试手动加载 .env 文件：")
try:
    # 手动读取并设置环境变量
    if env_file.exists():
        env_vars = {}
        with open('.env', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # 移除引号
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    env_vars[key] = value
        
        print(f"  ✅ 成功读取 {len(env_vars)} 个环境变量")
        
        # 显示关键配置
        key_configs = ['USE_EXTERNAL_TOKEN_FILE', 'GITHUB_TOKENS_FILE', 'DATA_PATH', 'QUERIES_FILE']
        print("\n📌 关键配置：")
        for key in key_configs:
            if key in env_vars:
                value = env_vars[key]
                if 'TOKEN' in key and len(value) > 20:
                    value = f"{value[:10]}...{value[-10:]}"
                print(f"  {key} = {value}")
            else:
                print(f"  {key} = ❌ 未找到")
                
except Exception as e:
    print(f"  ❌ 加载失败: {e}")

# 测试 python-dotenv
print("\n🔧 测试 python-dotenv 加载：")
try:
    from dotenv import load_dotenv, dotenv_values
    
    # 显示 dotenv 版本
    import dotenv
    print(f"  dotenv 版本: {getattr(dotenv, '__version__', 'unknown')}")
    
    # 加载 .env
    result = load_dotenv(verbose=True, override=True)
    print(f"  load_dotenv 结果: {result}")
    
    # 使用 dotenv_values 读取
    values = dotenv_values('.env')
    print(f"  dotenv_values 读取到 {len(values)} 个变量")
    
    # 检查环境变量
    print("\n📌 从 os.environ 读取的关键配置：")
    for key in ['USE_EXTERNAL_TOKEN_FILE', 'GITHUB_TOKENS_FILE', 'DATA_PATH', 'QUERIES_FILE']:
        value = os.getenv(key)
        if value:
            if 'TOKEN' in key and len(value) > 20:
                value = f"{value[:10]}...{value[-10:]}"
            print(f"  {key} = {value}")
        else:
            print(f"  {key} = ❌ 未找到")
            
except ImportError:
    print("  ❌ python-dotenv 未安装")
except Exception as e:
    print(f"  ❌ 测试失败: {e}")

print("\n" + "=" * 60)