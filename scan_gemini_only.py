#!/usr/bin/env python3
"""
Gemini API密钥专用扫描器
只搜索和验证Gemini密钥
"""

import os
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from common.Logger import Logger
from utils.github_client_enhanced import EnhancedGitHubClient
import re
import requests
import json

logger = Logger

class GeminiScanner:
    """专门扫描Gemini密钥的简化扫描器"""
    
    def __init__(self):
        self.github_client = EnhancedGitHubClient(use_credential_manager=False)
        self.found_keys = []
        self.valid_keys = []
        
    def extract_gemini_keys(self, content):
        """从内容中提取Gemini密钥"""
        keys = set()
        
        # Gemini密钥模式
        patterns = [
            r'AIzaSy[A-Za-z0-9_\-]{33}',  # 标准Gemini格式
            r'AIza[A-Za-z0-9_\-]{35}',     # 变体格式
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            keys.update(matches)
        
        return list(keys)
    
    def validate_gemini_key(self, key):
        """验证Gemini密钥"""
        try:
            # 使用Gemini API验证
            url = "https://generativelanguage.googleapis.com/v1beta/models?key=" + key
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"✅ Valid Gemini key: {key[:10]}...")
                return True
            elif response.status_code == 400:
                logger.info(f"❌ Invalid Gemini key: {key[:10]}...")
                return False
            else:
                logger.warning(f"⚠️ Uncertain status for key: {key[:10]}... (status: {response.status_code})")
                return False
        except Exception as e:
            logger.error(f"Error validating key: {e}")
            return False
    
    async def scan_repository(self, repo_name, query="AIzaSy"):
        """扫描单个仓库"""
        logger.info(f"🔍 Scanning repository: {repo_name}")
        
        try:
            # 搜索仓库中的文件
            files = await self.github_client.search_in_repository(
                repo_name,
                query,
                file_extensions=['.json', '.js', '.py', '.env', '.yml', '.yaml', '.md', '.txt']
            )
            
            for file_data in files:
                # 获取文件内容
                content = await self.github_client.get_file_content(
                    repo_name,
                    file_data['path']
                )
                
                if content:
                    # 提取Gemini密钥
                    keys = self.extract_gemini_keys(content)
                    
                    for key in keys:
                        key_info = {
                            'key': key,
                            'repository': repo_name,
                            'file_path': file_data['path'],
                            'file_url': file_data.get('html_url', '')
                        }
                        self.found_keys.append(key_info)
                        logger.info(f"🔑 Found potential key in {file_data['path']}")
                        
                        # 立即验证
                        if self.validate_gemini_key(key):
                            self.valid_keys.append(key_info)
                            self.save_valid_key(key_info)
                            
        except Exception as e:
            logger.error(f"Error scanning repository {repo_name}: {e}")
    
    def save_valid_key(self, key_info):
        """保存有效密钥"""
        output_file = Path("data/gemini_valid_keys.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 读取现有密钥
        existing_keys = []
        if output_file.exists():
            with open(output_file, 'r') as f:
                existing_keys = json.load(f)
        
        # 添加新密钥
        existing_keys.append(key_info)
        
        # 保存
        with open(output_file, 'w') as f:
            json.dump(existing_keys, f, indent=2)
        
        logger.info(f"💾 Saved valid key to {output_file}")
    
    async def run(self, queries=None):
        """运行扫描"""
        if queries is None:
            queries = [
                "AIzaSy in:file",
                "gemini api key in:file",
                "AIzaSy extension:json",
                "AIzaSy extension:env",
                "AIzaSy extension:md"
            ]
        
        logger.info(f"🚀 Starting Gemini key scan with {len(queries)} queries")
        
        for query in queries:
            logger.info(f"📝 Processing query: {query}")
            
            try:
                # 搜索仓库
                repositories = await self.github_client.search_repositories(
                    query,
                    max_results=10  # 限制结果数量
                )
                
                logger.info(f"📦 Found {len(repositories)} repositories")
                
                # 扫描每个仓库
                for repo in repositories:
                    await self.scan_repository(repo['full_name'], "AIzaSy")
                    
            except Exception as e:
                logger.error(f"Error processing query '{query}': {e}")
        
        # 显示统计
        logger.info("=" * 60)
        logger.info("📊 Scan Statistics")
        logger.info("=" * 60)
        logger.info(f"🔑 Total keys found: {len(self.found_keys)}")
        logger.info(f"✅ Valid keys: {len(self.valid_keys)}")
        logger.info(f"❌ Invalid keys: {len(self.found_keys) - len(self.valid_keys)}")
        
        if self.valid_keys:
            logger.info("\n✨ Valid Gemini Keys Found:")
            for key_info in self.valid_keys:
                logger.info(f"  - {key_info['key'][:20]}... from {key_info['repository']}")

async def main():
    """主函数"""
    print("=" * 60)
    print("🔍 Gemini API Key Scanner")
    print("=" * 60)
    
    scanner = GeminiScanner()
    
    # 使用有限的查询
    queries = [
        "AIzaSy in:file extension:md",  # 从Markdown文件开始
        "AIzaSy in:file extension:json"  # 然后JSON文件
    ]
    
    await scanner.run(queries)

if __name__ == "__main__":
    asyncio.run(main())
