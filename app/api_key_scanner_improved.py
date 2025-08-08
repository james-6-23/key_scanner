"""
Hajimi King 改进版 - 增强数据持久化和Token一致性
主要改进：
1. 每次找到有效密钥立即刷新文件缓冲区
2. 添加信号处理器优雅退出
3. 统一Token读取逻辑
"""

import os
import sys
import random
import re
import time
import traceback
import signal
import atexit
from datetime import datetime, timedelta
from typing import Dict, List, Union, Any

# 添加父目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from common.Logger import logger
from common.config import Config
from utils.github_client import GitHubClient
from utils.file_manager import file_manager, Checkpoint, checkpoint
from utils.sync_utils import sync_utils
from utils.parallel_validator import ParallelKeyValidator, get_parallel_validator

# 全局变量用于优雅退出
should_exit = False
total_keys_found = 0
total_rate_limited_keys = 0

def signal_handler(signum, frame):
    """信号处理器，用于优雅退出"""
    global should_exit
    logger.info("\n⛔ Received interrupt signal, saving data and exiting gracefully...")
    should_exit = True
    
    # 立即保存当前进度
    save_progress()
    
    # 给一点时间完成保存
    time.sleep(2)
    sys.exit(0)

def save_progress():
    """保存当前进度"""
    global total_keys_found, total_rate_limited_keys
    
    try:
        # 更新checkpoint
        checkpoint.update_scan_time()
        file_manager.save_checkpoint(checkpoint)
        
        # 强制刷新所有文件
        file_manager.flush_all_files()
        
        logger.info(f"💾 Progress saved - Valid keys: {total_keys_found}, Rate limited: {total_rate_limited_keys}")
        logger.info(f"📊 Checkpoint saved with {len(checkpoint.scanned_shas)} scanned files")
        
        # 显示保存的文件位置
        if file_manager.keys_valid_filename and os.path.exists(file_manager.keys_valid_filename):
            file_size = os.path.getsize(file_manager.keys_valid_filename)
            logger.info(f"📁 Valid keys file: {file_manager.keys_valid_filename} ({file_size} bytes)")
            
        if file_manager.rate_limited_filename and os.path.exists(file_manager.rate_limited_filename):
            file_size = os.path.getsize(file_manager.rate_limited_filename)
            logger.info(f"📁 Rate limited keys file: {file_manager.rate_limited_filename} ({file_size} bytes)")
            
    except Exception as e:
        logger.error(f"❌ Error saving progress: {e}")
        traceback.print_exc()

def cleanup():
    """清理函数，程序退出时调用"""
    logger.info("🔚 Performing cleanup...")
    save_progress()
    
    # 关闭同步工具
    try:
        sync_utils.shutdown()
    except:
        pass
    
    # 关闭并行验证器
    try:
        parallel_validator.shutdown()
    except:
        pass
    
    logger.info("✅ Cleanup completed")

# 注册信号处理器和退出处理器
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
atexit.register(cleanup)

# 创建GitHub工具实例（使用新的TokenManager）
github_utils = GitHubClient.create_instance(use_token_manager=True)

# 创建并行验证器实例
parallel_validator = get_parallel_validator(max_workers=10)

# 统计信息
skip_stats = {
    "time_filter": 0,
    "sha_duplicate": 0,
    "age_filter": 0,
    "doc_filter": 0
}

# 验证统计
validation_stats = {
    "serial_count": 0,
    "parallel_count": 0,
    "serial_time": 0.0,
    "parallel_time": 0.0
}


class EnhancedFileManager:
    """增强的文件管理器，确保数据实时保存"""
    
    def __init__(self, base_manager):
        self.base_manager = base_manager
        self.file_handles = {}
        
    def save_valid_keys(self, repo_name: str, file_path: str, file_url: str, valid_keys: List[str]) -> None:
        """保存有效的API密钥（增强版）"""
        if not valid_keys:
            return
            
        # 调用原始保存方法
        self.base_manager.save_valid_keys(repo_name, file_path, file_url, valid_keys)
        
        # 立即刷新文件缓冲区
        self.flush_file(self.base_manager.keys_valid_filename)
        self.flush_file(self.base_manager.detail_log_filename)
        
        logger.info(f"💾 Saved and flushed {len(valid_keys)} valid key(s) to disk")
    
    def save_rate_limited_keys(self, repo_name: str, file_path: str, file_url: str, rate_limited_keys: List[str]) -> None:
        """保存被限流的API密钥（增强版）"""
        if not rate_limited_keys:
            return
            
        # 调用原始保存方法
        self.base_manager.save_rate_limited_keys(repo_name, file_path, file_url, rate_limited_keys)
        
        # 立即刷新文件缓冲区
        self.flush_file(self.base_manager.rate_limited_filename)
        self.flush_file(self.base_manager.rate_limited_detail_filename)
        
        logger.info(f"💾 Saved and flushed {len(rate_limited_keys)} rate limited key(s) to disk")
    
    def flush_file(self, filename: str) -> None:
        """刷新特定文件的缓冲区"""
        if filename and os.path.exists(filename):
            try:
                # 打开文件并立即关闭，强制刷新
                with open(filename, 'a') as f:
                    f.flush()
                    os.fsync(f.fileno())
            except Exception as e:
                logger.error(f"Error flushing file {filename}: {e}")
    
    def flush_all_files(self) -> None:
        """刷新所有文件的缓冲区"""
        files_to_flush = [
            self.base_manager.keys_valid_filename,
            self.base_manager.detail_log_filename,
            self.base_manager.rate_limited_filename,
            self.base_manager.rate_limited_detail_filename
        ]
        
        for filename in files_to_flush:
            if filename:
                self.flush_file(filename)
    
    def __getattr__(self, name):
        """代理其他方法到原始file_manager"""
        return getattr(self.base_manager, name)


# 使用增强的文件管理器
enhanced_file_manager = EnhancedFileManager(file_manager)


def normalize_query(query: str) -> str:
    """标准化查询字符串"""
    query = " ".join(query.split())

    parts = []
    i = 0
    while i < len(query):
        if query[i] == '"':
            end_quote = query.find('"', i + 1)
            if end_quote != -1:
                parts.append(query[i:end_quote + 1])
                i = end_quote + 1
            else:
                parts.append(query[i])
                i += 1
        elif query[i] == ' ':
            i += 1
        else:
            start = i
            while i < len(query) and query[i] != ' ':
                i += 1
            parts.append(query[start:i])

    quoted_strings = []
    language_parts = []
    filename_parts = []
    path_parts = []
    other_parts = []

    for part in parts:
        if part.startswith('"') and part.endswith('"'):
            quoted_strings.append(part)
        elif part.startswith('language:'):
            language_parts.append(part)
        elif part.startswith('filename:'):
            filename_parts.append(part)
        elif part.startswith('path:'):
            path_parts.append(part)
        elif part.strip():
            other_parts.append(part)

    normalized_parts = []
    normalized_parts.extend(sorted(quoted_strings))
    normalized_parts.extend(sorted(other_parts))
    normalized_parts.extend(sorted(language_parts))
    normalized_parts.extend(sorted(filename_parts))
    normalized_parts.extend(sorted(path_parts))

    return " ".join(normalized_parts)


def extract_keys_from_content(content: str) -> List[str]:
    """从内容中提取API密钥"""
    pattern = r'(AIzaSy[A-Za-z0-9\-_]{33})'
    return re.findall(pattern, content)


def should_skip_item(item: Dict[str, Any], checkpoint: Checkpoint) -> tuple[bool, str]:
    """检查是否应该跳过处理此item"""
    # 检查增量扫描时间
    if checkpoint.last_scan_time:
        try:
            last_scan_dt = datetime.fromisoformat(checkpoint.last_scan_time)
            repo_pushed_at = item["repository"].get("pushed_at")
            if repo_pushed_at:
                repo_pushed_dt = datetime.strptime(repo_pushed_at, "%Y-%m-%dT%H:%M:%SZ")
                if repo_pushed_dt <= last_scan_dt:
                    skip_stats["time_filter"] += 1
                    return True, "time_filter"
        except Exception as e:
            pass

    # 检查SHA是否已扫描
    if item.get("sha") in checkpoint.scanned_shas:
        skip_stats["sha_duplicate"] += 1
        return True, "sha_duplicate"

    # 检查仓库年龄
    repo_pushed_at = item["repository"].get("pushed_at")
    if repo_pushed_at:
        repo_pushed_dt = datetime.strptime(repo_pushed_at, "%Y-%m-%dT%H:%M:%SZ")
        if repo_pushed_dt < datetime.utcnow() - timedelta(days=Config.DATE_RANGE_DAYS):
            skip_stats["age_filter"] += 1
            return True, "age_filter"

    # 检查文档和示例文件
    lowercase_path = item["path"].lower()
    if any(token in lowercase_path for token in Config.FILE_PATH_BLACKLIST):
        skip_stats["doc_filter"] += 1
        return True, "doc_filter"

    return False, ""


def process_item_parallel(item: Dict[str, Any]) -> tuple:
    """使用并行验证处理单个GitHub搜索结果item"""
    global should_exit, total_keys_found, total_rate_limited_keys
    
    if should_exit:
        return 0, 0
    
    delay = random.uniform(0.5, 1.5)
    file_url = item["html_url"]

    repo_name = item["repository"]["full_name"]
    file_path = item["path"]
    time.sleep(delay)

    content = github_utils.get_file_content(item)
    if not content:
        logger.warning(f"⚠️ Failed to fetch content for file: {file_url}")
        return 0, 0

    keys = extract_keys_from_content(content)

    # 过滤占位符密钥
    filtered_keys = []
    for key in keys:
        context_index = content.find(key)
        if context_index != -1:
            snippet = content[context_index:context_index + 45]
            if "..." in snippet or "YOUR_" in snippet.upper():
                continue
        filtered_keys.append(key)
    
    # 去重处理
    keys = list(set(filtered_keys))

    if not keys:
        return 0, 0

    logger.info(f"🔑 Found {len(keys)} suspected key(s), starting parallel validation...")

    # 使用并行验证
    start_time = time.time()
    results = parallel_validator.validate_batch(keys)
    validation_time = time.time() - start_time

    # 更新验证统计
    validation_stats["parallel_count"] += len(keys)
    validation_stats["parallel_time"] += validation_time

    valid_keys = []
    rate_limited_keys = []

    # 处理验证结果
    for key, result in results.items():
        if result.status == "ok":
            valid_keys.append(key)
            logger.info(f"✅ VALID: {key} (response: {result.response_time:.2f}s)")
        elif result.status == "rate_limited":
            rate_limited_keys.append(key)
            logger.warning(f"⚠️ RATE LIMITED: {key}, proxy: {result.proxy_used}")
        else:
            logger.info(f"❌ INVALID: {key}, status: {result.status}")

    # 显示并行验证性能
    if len(keys) > 1:
        logger.info(f"⚡ Parallel validation completed: {len(keys)} keys in {validation_time:.2f}s ({len(keys)/validation_time:.1f} keys/s)")

    # 使用增强的文件管理器保存结果（会立即刷新到磁盘）
    if valid_keys:
        enhanced_file_manager.save_valid_keys(repo_name, file_path, file_url, valid_keys)
        total_keys_found += len(valid_keys)
        
        # 添加到同步队列
        try:
            sync_utils.add_keys_to_queue(valid_keys)
            logger.info(f"📥 Added {len(valid_keys)} key(s) to sync queues")
        except Exception as e:
            logger.error(f"📥 Error adding keys to sync queues: {e}")

    if rate_limited_keys:
        enhanced_file_manager.save_rate_limited_keys(repo_name, file_path, file_url, rate_limited_keys)
        total_rate_limited_keys += len(rate_limited_keys)

    return len(valid_keys), len(rate_limited_keys)


def print_skip_stats():
    """打印跳过统计信息"""
    total_skipped = sum(skip_stats.values())
    if total_skipped > 0:
        logger.info(f"📊 Skipped {total_skipped} items - Time: {skip_stats['time_filter']}, Duplicate: {skip_stats['sha_duplicate']}, Age: {skip_stats['age_filter']}, Docs: {skip_stats['doc_filter']}")


def print_validation_stats():
    """打印验证性能统计"""
    stats = parallel_validator.get_stats()
    proxy_stats = parallel_validator.get_proxy_stats()
    
    logger.info("📊 Validation Performance Stats:")
    logger.info(f"   Total validated: {stats.total_validated}")
    logger.info(f"   Valid keys: {stats.valid_keys}")
    logger.info(f"   Invalid keys: {stats.invalid_keys}")
    logger.info(f"   Rate limited: {stats.rate_limited_keys}")
    logger.info(f"   Errors: {stats.errors}")
    logger.info(f"   Average response time: {stats.avg_response_time:.2f}s")
    
    if stats.total_validated > 0:
        throughput = stats.total_validated / stats.total_time if stats.total_time > 0 else 0
        logger.info(f"   Overall throughput: {throughput:.1f} keys/second")
    
    if proxy_stats:
        logger.info("🌐 Proxy Performance:")
        for proxy_url, pstats in proxy_stats.items():
            logger.info(f"   {proxy_url}: {pstats['success_rate']:.1%} success ({pstats['success']}/{pstats['total']})")


def reset_skip_stats():
    """重置跳过统计"""
    global skip_stats
    skip_stats = {"time_filter": 0, "sha_duplicate": 0, "age_filter": 0, "doc_filter": 0}


def display_token_consistency_check():
    """显示Token一致性检查"""
    logger.info("🔍 Checking Token consistency...")
    
    # 获取Token管理器状态
    token_status = github_utils.get_token_status()
    
    # 检查github_tokens.txt文件
    tokens_file = "github_tokens.txt"
    file_token_count = 0
    
    if os.path.exists(tokens_file):
        with open(tokens_file, 'r') as f:
            lines = f.readlines()
            file_token_count = len([line for line in lines if line.strip() and not line.strip().startswith('#')])
    
    logger.info(f"📊 Token Status:")
    logger.info(f"   TokenManager: {token_status.get('total_tokens', 0)} tokens")
    logger.info(f"   Active tokens: {token_status.get('active_tokens', 0)}")
    logger.info(f"   File ({tokens_file}): {file_token_count} tokens")
    
    if token_status.get('total_tokens', 0) != file_token_count:
        logger.warning(f"⚠️ Token count mismatch! Manager has {token_status.get('total_tokens', 0)}, file has {file_token_count}")
        logger.warning(f"   Please check your token configuration")
    else:
        logger.info(f"✅ Token counts are consistent")
    
    return token_status


def main():
    global should_exit, total_keys_found, total_rate_limited_keys
    
    start_time = datetime.now()

    # 打印系统启动信息
    logger.info("=" * 60)
    logger.info("🚀 HAJIMI KING STARTING (Enhanced Data Persistence Edition)")
    logger.info("=" * 60)
    logger.info(f"⏰ Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"⚡ Parallel validation enabled with {parallel_validator.max_workers} workers")
    logger.info(f"💾 Enhanced data persistence enabled - all finds saved immediately")

    # 1. 检查配置
    if not Config.check():
        logger.info("❌ Config check failed. Exiting...")
        sys.exit(1)
        
    # 2. 检查文件管理器
    if not file_manager.check():
        logger.error("❌ FileManager check failed. Exiting...")
        sys.exit(1)

    # 3. Token一致性检查
    token_status = display_token_consistency_check()

    # 4. 显示系统信息
    search_queries = file_manager.get_search_queries()
    logger.info("📋 SYSTEM INFORMATION:")
    logger.info(f"🔍 Search queries: {len(search_queries)} loaded")
    logger.info(f"📅 Date filter: {Config.DATE_RANGE_DAYS} days")
    if Config.PROXY_LIST:
        logger.info(f"🌐 Proxy: {len(Config.PROXY_LIST)} proxies configured")

    if checkpoint.last_scan_time:
        logger.info(f"💾 Checkpoint found - Incremental scan mode")
        logger.info(f"   Last scan: {checkpoint.last_scan_time}")
        logger.info(f"   Scanned files: {len(checkpoint.scanned_shas)}")
        logger.info(f"   Processed queries: {len(checkpoint.processed_queries)}")
    else:
        logger.info(f"💾 No checkpoint - Full scan mode")

    # 显示输出文件位置
    logger.info("📁 Output files:")
    logger.info(f"   Valid keys: {file_manager.keys_valid_filename}")
    logger.info(f"   Rate limited: {file_manager.rate_limited_filename}")
    logger.info(f"   Details: {file_manager.detail_log_filename}")

    logger.info("✅ System ready - Starting scan")
    logger.info("💡 Press Ctrl+C anytime to save progress and exit gracefully")
    logger.info("=" * 60)

    loop_count = 0

    while not should_exit:
        try:
            loop_count += 1
            logger.info(f"🔄 Loop #{loop_count} - {datetime.now().strftime('%H:%M:%S')}")

            query_count = 0
            loop_processed_files = 0
            reset_skip_stats()

            for i, q in enumerate(search_queries, 1):
                if should_exit:
                    break
                    
                normalized_q = normalize_query(q)
                if normalized_q in checkpoint.processed_queries:
                    logger.info(f"🔍 Skipping already processed query: [{q}], index:#{i}")
                    continue

                res = github_utils.search_for_keys(q)

                if res and "items" in res:
                    items = res["items"]
                    if items:
                        query_valid_keys = 0
                        query_rate_limited_keys = 0
                        query_processed = 0
                        
                        for item_index, item in enumerate(items, 1):
                            if should_exit:
                                break
                            
                            # 每10个item保存checkpoint
                            if item_index % 10 == 0:
                                logger.info(f"📈 Progress: {item_index}/{len(items)} | query: {q} | valid: {query_valid_keys}")
                                save_progress()
                                
                            # 检查是否应该跳过此item
                            should_skip, skip_reason = should_skip_item(item, checkpoint)
                            if should_skip:
                                logger.debug(f"🚫 Skipping item {item.get('path','').lower()}, index:{item_index} - reason: {skip_reason}")
                                continue

                            # 处理单个item
                            valid_count, rate_limited_count = process_item_parallel(item)

                            query_valid_keys += valid_count
                            query_rate_limited_keys += rate_limited_count
                            query_processed += 1

                            # 记录已扫描的SHA
                            checkpoint.add_scanned_sha(item.get("sha"))
                            loop_processed_files += 1

                        if query_processed > 0:
                            logger.info(f"✅ Query {i}/{len(search_queries)} complete - Processed: {query_processed}, Valid: +{query_valid_keys}, Rate limited: +{query_rate_limited_keys}")
                        else:
                            logger.info(f"⏭️ Query {i}/{len(search_queries)} complete - All items skipped")

                        print_skip_stats()
                    else:
                        logger.info(f"📭 Query {i}/{len(search_queries)} - No items found")
                else:
                    logger.warning(f"❌ Query {i}/{len(search_queries)} failed")

                checkpoint.add_processed_query(normalized_q)
                query_count += 1

                # 保存进度
                save_progress()

                if query_count % 5 == 0:
                    logger.info(f"⏸️ Processed {query_count} queries, taking a break...")
                    time.sleep(1)

            logger.info(f"🏁 Loop #{loop_count} complete - Processed {loop_processed_files} files | Total valid: {total_keys_found} | Total rate limited: {total_rate_limited_keys}")
            
            # 显示最终验证统计
            print_validation_stats()
            
            # 显示Token状态
            if loop_count % 5 == 0:
                token_summary = github_utils.get_token_status()
                if "active_tokens" in token_summary:
                    logger.info(f"📊 Token Status - Active: {token_summary['active_tokens']}/{token_summary['total_tokens']}, Remaining calls: {token_summary.get('total_remaining_calls', 'N/A')}")

            logger.info(f"💤 Sleeping for 10 seconds...")
            time.sleep(10)

        except KeyboardInterrupt:
            logger.info("⛔ Interrupted by user")
            should_exit = True
            break
        except Exception as e:
            logger.error(f"💥 Unexpected error: {e}")
            traceback.print_exc()
            
            # 保存当前进度
            save_progress()
            
            logger.info("🔄 Continuing after error...")
            time.sleep(5)
            continue

    # 程序结束前的最终统计
    logger.info("=" * 60)
    logger.info("📊 FINAL STATISTICS")
    logger.info(f"✅ Total valid keys found: {total_keys_found}")
    logger.info(f"⚠️ Total rate limited keys: {total_rate_limited_keys}")
    logger.info(f"📁 Scanned files: {len(checkpoint.scanned_shas)}")
    logger.info(f"🔍 Processed queries: {len(checkpoint.processed_queries)}")
    
    # 显示最终性能统计
    print_validation_stats()
    
    end_time = datetime.now()
    duration = end_time - start_time
    logger.info(f"⏱️ Total runtime: {duration}")
    logger.info("=" * 60)
    logger.info("🔚 HAJIMI KING SHUTDOWN COMPLETE")


if __name__ == "__main__":
    main()