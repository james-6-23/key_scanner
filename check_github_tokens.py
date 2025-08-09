#!/usr/bin/env python3
"""
GitHub Token状态检查器
检查github_tokens.txt中所有token的状态和配额
"""

import os
import sys
import json
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

class GitHubTokenChecker:
    """GitHub Token状态检查器"""
    
    def __init__(self, token_file: str = "github_tokens.txt"):
        """
        初始化检查器
        
        Args:
            token_file: token文件路径
        """
        self.token_file = token_file
        self.tokens = []
        self.results = []
        
    def load_tokens(self) -> List[str]:
        """加载tokens"""
        if not os.path.exists(self.token_file):
            print(f"[ERROR] Token file not found: {self.token_file}")
            return []
        
        tokens = []
        with open(self.token_file, 'r') as f:
            for line in f:
                token = line.strip()
                if token and not token.startswith('#'):
                    tokens.append(token)
        
        self.tokens = tokens
        print(f"[INFO] Loaded {len(tokens)} tokens from {self.token_file}")
        return tokens
    
    def check_token(self, token: str) -> Dict:
        """
        检查单个token的状态
        
        Args:
            token: GitHub token
            
        Returns:
            token状态信息
        """
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        result = {
            'token': token[:10] + '...' + token[-4:],  # 隐藏中间部分
            'valid': False,
            'user': None,
            'scopes': [],
            'rate_limit': {
                'limit': 0,
                'remaining': 0,
                'reset': None,
                'used': 0
            },
            'search_limit': {
                'limit': 0,
                'remaining': 0,
                'reset': None,
                'used': 0
            },
            'error': None
        }
        
        try:
            # 1. 检查token有效性和用户信息
            user_response = requests.get(
                'https://api.github.com/user',
                headers=headers,
                timeout=10
            )
            
            if user_response.status_code == 200:
                result['valid'] = True
                user_data = user_response.json()
                result['user'] = user_data.get('login', 'Unknown')
                
                # 获取token权限范围
                scopes = user_response.headers.get('X-OAuth-Scopes', '')
                result['scopes'] = [s.strip() for s in scopes.split(',')] if scopes else []
            elif user_response.status_code == 401:
                result['error'] = 'Invalid token (401 Unauthorized)'
                return result
            else:
                result['error'] = f'Failed to authenticate (Status: {user_response.status_code})'
                return result
            
            # 2. 检查API速率限制
            rate_response = requests.get(
                'https://api.github.com/rate_limit',
                headers=headers,
                timeout=10
            )
            
            if rate_response.status_code == 200:
                rate_data = rate_response.json()
                
                # 核心API限制
                core = rate_data.get('rate', {})
                result['rate_limit'] = {
                    'limit': core.get('limit', 0),
                    'remaining': core.get('remaining', 0),
                    'reset': datetime.fromtimestamp(core.get('reset', 0)).strftime('%Y-%m-%d %H:%M:%S'),
                    'used': core.get('limit', 0) - core.get('remaining', 0)
                }
                
                # 搜索API限制（这是扫描器主要使用的）
                search = rate_data.get('resources', {}).get('search', {})
                result['search_limit'] = {
                    'limit': search.get('limit', 0),
                    'remaining': search.get('remaining', 0),
                    'reset': datetime.fromtimestamp(search.get('reset', 0)).strftime('%Y-%m-%d %H:%M:%S'),
                    'used': search.get('limit', 0) - search.get('remaining', 0)
                }
            
        except requests.exceptions.Timeout:
            result['error'] = 'Request timeout'
        except requests.exceptions.ConnectionError:
            result['error'] = 'Connection error'
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def check_all_tokens(self, max_workers: int = 5):
        """
        并发检查所有tokens
        
        Args:
            max_workers: 最大并发数
        """
        if not self.tokens:
            print("[WARNING] No tokens to check")
            return
        
        print(f"\n[INFO] Checking {len(self.tokens)} tokens...")
        print("=" * 80)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_token = {executor.submit(self.check_token, token): token for token in self.tokens}
            
            for i, future in enumerate(as_completed(future_to_token), 1):
                result = future.result()
                self.results.append(result)
                
                # 实时显示结果
                self._print_token_status(result, i)
        
        # 显示汇总
        self._print_summary()
    
    def _print_token_status(self, result: Dict, index: int):
        """打印单个token状态"""
        token_display = result['token']
        
        if result['valid']:
            status = "✅ VALID"
            user = result.get('user', 'Unknown')
            search_remaining = result['search_limit']['remaining']
            search_limit = result['search_limit']['limit']
            reset_time = result['search_limit']['reset']
            
            # 根据剩余配额显示不同颜色/符号
            if search_remaining == 0:
                quota_status = "❌ EXHAUSTED"
            elif search_remaining < 5:
                quota_status = "⚠️  LOW"
            else:
                quota_status = "✅ OK"
            
            print(f"\nToken #{index}: {token_display}")
            print(f"  Status: {status}")
            print(f"  User: {user}")
            print(f"  Search Quota: {search_remaining}/{search_limit} {quota_status}")
            print(f"  Reset Time: {reset_time}")
            
            if result['scopes']:
                print(f"  Scopes: {', '.join(result['scopes'][:3])}...")
        else:
            status = "❌ INVALID"
            error = result.get('error', 'Unknown error')
            print(f"\nToken #{index}: {token_display}")
            print(f"  Status: {status}")
            print(f"  Error: {error}")
    
    def _print_summary(self):
        """打印汇总信息"""
        print("\n" + "=" * 80)
        print("📊 SUMMARY")
        print("=" * 80)
        
        valid_tokens = [r for r in self.results if r['valid']]
        invalid_tokens = [r for r in self.results if not r['valid']]
        
        print(f"Total Tokens: {len(self.results)}")
        print(f"✅ Valid: {len(valid_tokens)}")
        print(f"❌ Invalid: {len(invalid_tokens)}")
        
        if valid_tokens:
            # 计算总配额
            total_search_limit = sum(r['search_limit']['limit'] for r in valid_tokens)
            total_search_remaining = sum(r['search_limit']['remaining'] for r in valid_tokens)
            total_search_used = sum(r['search_limit']['used'] for r in valid_tokens)
            
            print(f"\n🔍 Search API Quota (Main concern for scanning):")
            print(f"  Total Limit: {total_search_limit} requests/hour")
            print(f"  Total Remaining: {total_search_remaining} requests")
            print(f"  Total Used: {total_search_used} requests")
            print(f"  Usage Rate: {(total_search_used/total_search_limit*100):.1f}%")
            
            # 找出配额耗尽的tokens
            exhausted = [r for r in valid_tokens if r['search_limit']['remaining'] == 0]
            if exhausted:
                print(f"\n⚠️  {len(exhausted)} tokens have exhausted search quota:")
                for r in exhausted:
                    print(f"    - {r['token']} (resets at {r['search_limit']['reset']})")
            
            # 找出配额较低的tokens
            low_quota = [r for r in valid_tokens if 0 < r['search_limit']['remaining'] < 5]
            if low_quota:
                print(f"\n⚠️  {len(low_quota)} tokens have low search quota (<5):")
                for r in low_quota:
                    print(f"    - {r['token']} ({r['search_limit']['remaining']} remaining)")
            
            # 计算下次重置时间
            reset_times = [r['search_limit']['reset'] for r in valid_tokens if r['search_limit']['remaining'] == 0]
            if reset_times:
                earliest_reset = min(reset_times)
                print(f"\n⏰ Earliest quota reset: {earliest_reset}")
        
        # 保存详细报告
        self._save_report()
    
    def _save_report(self):
        """保存详细报告到文件"""
        report_file = Path("data/token_status_report.json")
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_tokens': len(self.results),
            'valid_count': len([r for r in self.results if r['valid']]),
            'invalid_count': len([r for r in self.results if not r['valid']]),
            'tokens': self.results
        }
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Detailed report saved to: {report_file}")
    
    def export_valid_tokens(self):
        """导出有效且有配额的tokens到新文件"""
        valid_tokens = []
        
        for i, result in enumerate(self.results):
            if result['valid'] and result['search_limit']['remaining'] > 0:
                valid_tokens.append(self.tokens[i])
        
        if valid_tokens:
            output_file = "github_tokens_active.txt"
            with open(output_file, 'w') as f:
                f.write('\n'.join(valid_tokens))
            print(f"\n✅ Exported {len(valid_tokens)} active tokens to: {output_file}")
        else:
            print("\n⚠️  No active tokens with remaining quota to export")

def main():
    """主函数"""
    print("=" * 80)
    print("🔍 GitHub Token Status Checker")
    print("=" * 80)
    
    # 检查token文件
    token_file = "github_tokens.txt"
    if not os.path.exists(token_file):
        print(f"[ERROR] {token_file} not found!")
        print("\nPlease create the file with your GitHub tokens (one per line)")
        return
    
    # 创建检查器
    checker = GitHubTokenChecker(token_file)
    
    # 加载tokens
    checker.load_tokens()
    
    if not checker.tokens:
        print("[ERROR] No tokens found in file")
        return
    
    # 检查所有tokens
    checker.check_all_tokens()
    
    # 导出有效tokens
    checker.export_valid_tokens()
    
    print("\n" + "=" * 80)
    print("✅ Check complete!")
    print("=" * 80)
    print("\nRecommendations:")
    print("1. Remove invalid tokens from github_tokens.txt")
    print("2. Wait for exhausted tokens to reset (usually 1 hour)")
    print("3. Add more tokens to increase total quota")
    print("4. Use github_tokens_active.txt for immediate scanning")

if __name__ == "__main__":
    main()