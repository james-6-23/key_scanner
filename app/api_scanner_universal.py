#!/usr/bin/env python3
"""
通用API密钥扫描器
支持多种API类型的扫描和验证
默认扫描Gemini API密钥
"""

import os
import sys
import re
import json
import asyncio
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.config import Config
from common.Logger import logger
from utils.file_manager import FileManager
from credential_manager.core.manager import get_credential_manager
from credential_manager.core.models import ServiceType

# 配置日志
# logger = Logger.get_logger("universal_api_scanner")


class UniversalAPIScanner:
    """
    通用API密钥扫描器
    支持多种API类型
    """
    
    def __init__(self, api_types: List[str] = None):
        """
        初始化扫描器
        
        Args:
            api_types: 要扫描的API类型列表，默认['gemini']
        """
        # 加载API配置
        self.api_configs = self._load_api_configs()
        
        # 设置要扫描的API类型（默认gemini）
        if api_types is None:
            api_types = ['gemini']
        elif isinstance(api_types, str):
            api_types = [api_types]
        
        self.api_types = api_types
        
        # 验证API类型
        for api_type in self.api_types:
            if api_type not in self.api_configs:
                logger.warning(f"⚠️ 不支持的API类型: {api_type}")
                self.api_types.remove(api_type)
        
        if not self.api_types:
            logger.error("❌ 没有有效的API类型")
            raise ValueError("No valid API types specified")
        
        logger.info(f"🎯 扫描目标: {', '.join(self.api_types)}")
        
        # 初始化组件
        self.config = Config()
        self.file_manager = FileManager()
        
        # 统计信息
        self.stats = {api_type: {
            'total_found': 0,
            'valid': 0,
            'invalid': 0,
            'errors': 0
        } for api_type in self.api_types}
        
        self.start_time = datetime.now()
    
    def _load_api_configs(self) -> Dict[str, Any]:
        """加载API配置"""
        config_file = Path("config/api_patterns.json")
        
        if not config_file.exists():
            logger.warning("⚠️ API配置文件不存在，使用默认配置")
            return self._get_default_configs()
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                configs = json.load(f)
                logger.info(f"✅ 加载了 {len(configs)} 个API配置")
                return configs
        except Exception as e:
            logger.error(f"❌ 加载配置文件失败: {e}")
            return self._get_default_configs()
    
    def _get_default_configs(self) -> Dict[str, Any]:
        """获取默认配置（Gemini）"""
        return {
            "gemini": {
                "name": "Google Gemini",
                "pattern": r"AIzaSy[a-zA-Z0-9_-]{33}",
                "validation_url": "https://generativelanguage.googleapis.com/v1/models",
                "header_format": "x-goog-api-key: {key}",
                "search_queries": ["AIzaSy in:file"],
                "enabled": True
            }
        }
    
    def extract_keys(self, content: str, api_type: str) -> List[str]:
        """
        从内容中提取指定类型的API密钥
        
        Args:
            content: 要扫描的内容
            api_type: API类型
            
        Returns:
            找到的密钥列表
        """
        config = self.api_configs.get(api_type)
        if not config:
            return []
        
        pattern = config.get('pattern', '')
        if not pattern:
            return []
        
        try:
            matches = re.findall(pattern, content)
            # 去重
            unique_keys = list(set(matches))
            
            if unique_keys:
                logger.debug(f"🔍 在内容中找到 {len(unique_keys)} 个 {api_type} 密钥")
            
            return unique_keys
        except Exception as e:
            logger.error(f"提取密钥时出错: {e}")
            return []
    
    def extract_all_keys(self, content: str) -> Dict[str, List[str]]:
        """
        从内容中提取所有类型的API密钥
        
        Args:
            content: 要扫描的内容
            
        Returns:
            {api_type: [keys]} 字典
        """
        all_keys = {}
        
        for api_type in self.api_types:
            keys = self.extract_keys(content, api_type)
            if keys:
                all_keys[api_type] = keys
                self.stats[api_type]['total_found'] += len(keys)
        
        return all_keys
    
    def validate_key(self, key: str, api_type: str) -> bool:
        """
        验证API密钥是否有效
        
        Args:
            key: API密钥
            api_type: API类型
            
        Returns:
            是否有效
        """
        config = self.api_configs.get(api_type)
        if not config:
            return False
        
        validation_url = config.get('validation_url')
        header_format = config.get('header_format', '')
        method = config.get('validation_method', 'GET')
        
        if not validation_url:
            logger.warning(f"⚠️ {api_type} 没有配置验证URL")
            return False
        
        try:
            # 构建请求头
            headers = {}
            if 'Authorization' in header_format:
                headers['Authorization'] = header_format.replace('{key}', key).split(': ')[1]
            else:
                # 处理其他格式的header
                if ': ' in header_format:
                    header_name, header_value = header_format.split(': ')
                    headers[header_name] = header_value.replace('{key}', key)
            
            # 发送验证请求
            if method == 'GET':
                response = requests.get(validation_url, headers=headers, timeout=10)
            elif method == 'POST':
                # 某些API需要POST请求
                response = requests.post(validation_url, headers=headers, timeout=10)
            else:
                logger.warning(f"不支持的验证方法: {method}")
                return False
            
            # 检查响应
            is_valid = response.status_code in [200, 201]
            
            if is_valid:
                self.stats[api_type]['valid'] += 1
                logger.info(f"✅ 有效的 {api_type} 密钥: {key[:10]}...")
            else:
                self.stats[api_type]['invalid'] += 1
                logger.debug(f"❌ 无效的 {api_type} 密钥: {key[:10]}...")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"验证 {api_type} 密钥时出错: {e}")
            self.stats[api_type]['errors'] += 1
            return False
    
    def validate_keys_batch(self, keys_dict: Dict[str, List[str]]) -> Dict[str, List[Tuple[str, bool]]]:
        """
        批量验证密钥
        
        Args:
            keys_dict: {api_type: [keys]} 字典
            
        Returns:
            {api_type: [(key, is_valid)]} 字典
        """
        results = {}
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            
            for api_type, keys in keys_dict.items():
                results[api_type] = []
                
                for key in keys:
                    future = executor.submit(self.validate_key, key, api_type)
                    futures.append((api_type, key, future))
            
            for api_type, key, future in futures:
                try:
                    is_valid = future.result(timeout=30)
                    results[api_type].append((key, is_valid))
                except Exception as e:
                    logger.error(f"验证超时或错误: {e}")
                    results[api_type].append((key, False))
        
        return results
    
    def get_search_queries(self) -> Dict[str, List[str]]:
        """
        获取所有API类型的搜索查询
        
        Returns:
            {api_type: [queries]} 字典
        """
        queries = {}
        
        for api_type in self.api_types:
            config = self.api_configs.get(api_type)
            if config and config.get('enabled', False):
                queries[api_type] = config.get('search_queries', [])
        
        return queries
    
    def save_results(self, results: Dict[str, List[Tuple[str, bool]]]):
        """
        保存扫描结果
        
        Args:
            results: {api_type: [(key, is_valid)]} 字典
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for api_type, key_results in results.items():
            if not key_results:
                continue
            
            # 分离有效和无效的密钥
            valid_keys = [key for key, is_valid in key_results if is_valid]
            invalid_keys = [key for key, is_valid in key_results if not is_valid]
            
            # 保存有效密钥
            if valid_keys:
                output_file = Path(f"data/keys/{api_type}_valid_{timestamp}.json")
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_file, 'w') as f:
                    json.dump({
                        'api_type': api_type,
                        'timestamp': timestamp,
                        'keys': valid_keys,
                        'count': len(valid_keys)
                    }, f, indent=2)
                
                logger.info(f"💾 保存了 {len(valid_keys)} 个有效的 {api_type} 密钥")
            
            # 保存无效密钥（用于分析）
            if invalid_keys:
                output_file = Path(f"data/keys/{api_type}_invalid_{timestamp}.json")
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_file, 'w') as f:
                    json.dump({
                        'api_type': api_type,
                        'timestamp': timestamp,
                        'keys': invalid_keys,
                        'count': len(invalid_keys)
                    }, f, indent=2)
    
    def print_statistics(self):
        """打印统计信息"""
        duration = datetime.now() - self.start_time
        
        print("\n" + "=" * 60)
        print("📊 扫描统计")
        print("=" * 60)
        print(f"⏱️  运行时间: {duration}")
        print()
        
        for api_type in self.api_types:
            stats = self.stats[api_type]
            total = stats['total_found']
            
            if total > 0:
                print(f"🔑 {api_type.upper()} ({self.api_configs[api_type]['name']}):")
                print(f"   发现: {total}")
                print(f"   ✅ 有效: {stats['valid']}")
                print(f"   ❌ 无效: {stats['invalid']}")
                print(f"   ⚠️  错误: {stats['errors']}")
                
                if stats['valid'] > 0:
                    success_rate = (stats['valid'] / total) * 100
                    print(f"   📈 成功率: {success_rate:.1f}%")
                print()
        
        print("=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='通用API密钥扫描器')
    parser.add_argument(
        '--api-types',
        type=str,
        default='gemini',
        help='要扫描的API类型，逗号分隔 (默认: gemini)'
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        default=True,
        help='是否验证找到的密钥'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config/api_patterns.json',
        help='API配置文件路径'
    )
    
    args = parser.parse_args()
    
    # 解析API类型
    api_types = [t.strip() for t in args.api_types.split(',')]
    
    print("=" * 60)
    print("🚀 通用API密钥扫描器")
    print("=" * 60)
    print(f"扫描目标: {', '.join(api_types)}")
    print("=" * 60)
    
    try:
        # 创建扫描器
        scanner = UniversalAPIScanner(api_types)
        
        # 示例：扫描测试内容
        test_content = """
        # 测试内容
        GEMINI_API_KEY=AIzaSyD1234567890abcdefghijklmnopqrstuv
        OPENAI_API_KEY=sk-1234567890abcdefghijklmnopqrstuvwxyz12345678
        """
        
        # 提取密钥
        all_keys = scanner.extract_all_keys(test_content)
        
        if all_keys:
            print(f"\n🔍 找到密钥:")
            for api_type, keys in all_keys.items():
                print(f"  {api_type}: {len(keys)} 个")
            
            if args.validate:
                print("\n⚡ 开始验证...")
                results = scanner.validate_keys_batch(all_keys)
                scanner.save_results(results)
        else:
            print("\n❌ 未找到任何密钥")
        
        # 打印统计
        scanner.print_statistics()
        
    except Exception as e:
        logger.error(f"扫描失败: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())