"""
Hajimi King 并行验证版本
展示如何将并行验证系统集成到主程序中
"""

import os
import sys
import random
import re
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Union, Any

# 添加父目录到 Python 路径，确保能找到 common 和 utils 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from common.Logger import logger
from common.config import Config
from utils.github_client import GitHubClient
from utils.file_manager import file_manager, Checkpoint, checkpoint
from utils.sync_utils import sync_utils
from utils.parallel_validator import ParallelKeyValidator, get_parallel_validator

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
    """
    使用并行验证处理单个GitHub搜索结果item
    
    Returns:
        tuple: (valid_keys_count, rate_limited_keys_count)
    """
    delay = random.uniform(0.5, 1.5)  # 减少延迟，因为验证是并行的
    file_url = item["html_url"]

    # 简化日志输出，只显示关键信息
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

    # 保存结果
    if valid_keys:
        file_manager.save_valid_keys(repo_name, file_path, file_url, valid_keys)
        logger.info(f"💾 Saved {len(valid_keys)} valid key(s)")
        # 添加到同步队列（不阻塞主流程）
        try:
            sync_utils.add_keys_to_queue(valid_keys)
            logger.info(f"📥 Added {len(valid_keys)} key(s) to sync queues")
        except Exception as e:
            logger.error(f"📥 Error adding keys to sync queues: {e}")

    if rate_limited_keys:
        file_manager.save_rate_limited_keys(repo_name, file_path, file_url, rate_limited_keys)
        logger.info(f"💾 Saved {len(rate_limited_keys)} rate limited key(s)")

    return len(valid_keys), len(rate_limited_keys)


def process_batch_items(items: List[Dict[str, Any]]) -> tuple:
    """
    批量处理多个items，收集所有密钥后统一验证
    
    Returns:
        tuple: (total_valid_keys, total_rate_limited_keys)
    """
    all_keys_info = []  # [(key, item_info), ...]
    
    logger.info(f"🔄 Processing batch of {len(items)} items...")
    
    # 收集所有密钥
    for item in items:
        content = github_utils.get_file_content(item)
        if not content:
            continue
        
        keys = extract_keys_from_content(content)
        
        # 过滤和去重
        filtered_keys = []
        for key in keys:
            context_index = content.find(key)
            if context_index != -1:
                snippet = content[context_index:context_index + 45]
                if "..." in snippet or "YOUR_" in snippet.upper():
                    continue
            filtered_keys.append(key)
        
        # 记录每个密钥的来源
        for key in set(filtered_keys):
            all_keys_info.append((key, {
                "repo_name": item["repository"]["full_name"],
                "file_path": item["path"],
                "file_url": item["html_url"]
            }))
    
    if not all_keys_info:
        return 0, 0
    
    # 提取唯一密钥进行验证
    unique_keys = list(set(key for key, _ in all_keys_info))
    logger.info(f"🔑 Collected {len(unique_keys)} unique keys from batch")
    
    # 批量验证
    start_time = time.time()
    results = parallel_validator.validate_batch(unique_keys)
    validation_time = time.time() - start_time
    
    logger.info(f"⚡ Batch validation completed: {len(unique_keys)} keys in {validation_time:.2f}s ({len(unique_keys)/validation_time:.1f} keys/s)")
    
    # 按来源整理结果
    source_results = {}  # {file_url: {"valid": [], "rate_limited": []}}
    
    for key, item_info in all_keys_info:
        file_url = item_info["file_url"]
        if file_url not in source_results:
            source_results[file_url] = {
                "info": item_info,
                "valid": [],
                "rate_limited": []
            }
        
        result = results.get(key)
        if result and result.status == "ok":
            source_results[file_url]["valid"].append(key)
        elif result and result.status == "rate_limited":
            source_results[file_url]["rate_limited"].append(key)
    
    # 保存结果
    total_valid = 0
    total_rate_limited = 0
    
    for file_url, data in source_results.items():
        info = data["info"]
        valid_keys = data["valid"]
        rate_limited_keys = data["rate_limited"]
        
        if valid_keys:
            file_manager.save_valid_keys(info["repo_name"], info["file_path"], file_url, valid_keys)
            total_valid += len(valid_keys)
            
        if rate_limited_keys:
            file_manager.save_rate_limited_keys(info["repo_name"], info["file_path"], file_url, rate_limited_keys)
            total_rate_limited += len(rate_limited_keys)
    
    # 批量添加到同步队列
    all_valid_keys = [key for key, _ in all_keys_info if results.get(key) and results[key].status == "ok"]
    if all_valid_keys:
        try:
            sync_utils.add_keys_to_queue(all_valid_keys)
            logger.info(f"📥 Added {len(all_valid_keys)} key(s) to sync queues")
        except Exception as e:
            logger.error(f"📥 Error adding keys to sync queues: {e}")
    
    return total_valid, total_rate_limited


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


def main():
    start_time = datetime.now()

    # 打印系统启动信息
    logger.info("=" * 60)
    logger.info("🚀 HAJIMI KING STARTING (Parallel Validation Edition)")
    logger.info("=" * 60)
    logger.info(f"⏰ Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"⚡ Parallel validation enabled with {parallel_validator.max_workers} workers")

    # 1. 检查配置
    if not Config.check():
        logger.info("❌ Config check failed. Exiting...")
        sys.exit(1)
    # 2. 检查文件管理器
    if not file_manager.check():
        logger.error("❌ FileManager check failed. Exiting...")
        sys.exit(1)

    # 2.5. 显示SyncUtils状态和队列信息
    if sync_utils.balancer_enabled:
        logger.info("🔗 SyncUtils ready for async key syncing")
        
    # 显示队列状态
    balancer_queue_count = len(checkpoint.wait_send_balancer)
    gpt_load_queue_count = len(checkpoint.wait_send_gpt_load)
    logger.info(f"📊 Queue status - Balancer: {balancer_queue_count}, GPT Load: {gpt_load_queue_count}")

    # 3. 显示系统信息
    search_queries = file_manager.get_search_queries()
    logger.info("📋 SYSTEM INFORMATION:")
    
    # 显示Token状态
    token_status = github_utils.get_token_status()
    if "total_tokens" in token_status:
        logger.info(f"🔑 GitHub tokens: {token_status['total_tokens']} configured")
        if "active_tokens" in token_status:
            logger.info(f"   Active tokens: {token_status['active_tokens']}")
            logger.info(f"   Total remaining calls: {token_status.get('total_remaining_calls', 'N/A')}")
    
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

    logger.info("✅ System ready - Starting king")
    logger.info("=" * 60)

    total_keys_found = 0
    total_rate_limited_keys = 0
    loop_count = 0
    
    # 批处理配置
    BATCH_PROCESSING_ENABLED = True
    BATCH_SIZE = 10  # 每批处理的文件数

    while True:
        try:
            loop_count += 1
            logger.info(f"🔄 Loop #{loop_count} - {datetime.now().strftime('%H:%M:%S')}")

            query_count = 0
            loop_processed_files = 0
            reset_skip_stats()

            for i, q in enumerate(search_queries, 1):
                normalized_q = normalize_query(q)
                if normalized_q in checkpoint.processed_queries:
                    logger.info(f"🔍 Skipping already processed query: [{q}],index:#{i}")
                    continue

                res = github_utils.search_for_keys(q)

                if res and "items" in res:
                    items = res["items"]
                    if items:
                        query_valid_keys = 0
                        query_rate_limited_keys = 0
                        query_processed = 0
                        
                        # 批处理模式
                        if BATCH_PROCESSING_ENABLED and len(items) > BATCH_SIZE:
                            logger.info(f"📦 Using batch processing for {len(items)} items")
                            
                            for batch_start in range(0, len(items), BATCH_SIZE):
                                batch_end = min(batch_start + BATCH_SIZE, len(items))
                                batch_items = []
                                
                                # 收集批次中的有效items
                                for item in items[batch_start:batch_end]:
                                    should_skip, skip_reason = should_skip_item(item, checkpoint)
                                    if should_skip:
                                        logger.info(f"🚫 Skipping item {item.get('path','').lower()} - reason: {skip_reason}")
                                        continue
                                    
                                    batch_items.append(item)
                                    checkpoint.add_scanned_sha(item.get("sha"))
                                
                                # 批量处理
                                if batch_items:
                                    valid_count, rate_limited_count = process_batch_items(batch_items)
                                    query_valid_keys += valid_count
                                    query_rate_limited_keys += rate_limited_count
                                    query_processed += len(batch_items)
                                    loop_processed_files += len(batch_items)
                                
                                # 保存进度
                                if batch_end % 20 == 0 or batch_end == len(items):
                                    logger.info(f"📈 Batch progress: {batch_end}/{len(items)} | valid: {query_valid_keys} | rate limited: {query_rate_limited_keys}")
                                    file_manager.save_checkpoint(checkpoint)
                                    file_manager.update_dynamic_filenames()
                        
                        else:
                            # 单文件处理模式（用于小批量）
                            for item_index, item in enumerate(items, 1):
                                # 每20个item保存checkpoint并显示进度
                                if item_index % 20 == 0:
                                    logger.info(
                                        f"📈 Progress: {item_index}/{len(items)} | query: {q} | current valid: {query_valid_keys} | current rate limited: {query_rate_limited_keys} | total valid: {total_keys_found} | total rate limited: {total_rate_limited_keys}")
                                    file_manager.save_checkpoint(checkpoint)
                                    file_manager.update_dynamic_filenames()
                                    
                                    # 显示验证性能统计
                                    if item_index % 100 == 0:
                                        print_validation_stats()

                                # 检查是否应该跳过此item
                                should_skip, skip_reason = should_skip_item(item, checkpoint)
                                if should_skip:
                                    logger.info(f"🚫 Skipping item,name: {item.get('path','').lower()},index:{item_index} - reason: {skip_reason}")
                                    continue

                                # 处理单个item（使用并行验证）
                                valid_count, rate_limited_count = process_item_parallel(item)

                                query_valid_keys += valid_count
                                query_rate_limited_keys += rate_limited_count
                                query_processed += 1

                                # 记录已扫描的SHA
                                checkpoint.add_scanned_sha(item.get("sha"))

                                loop_processed_files += 1

                        total_keys_found += query_valid_keys
                        total_rate_limited_keys += query_rate_limited_keys

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

                checkpoint.update_scan_time()
                file_manager.save_checkpoint(checkpoint)
                file_manager.update_dynamic_filenames()

                if query_count % 5 == 0:
                    logger.info(f"⏸️ Processed {query_count} queries, taking a break...")
                    time.sleep(1)

            logger.info(f"🏁 Loop #{loop_count} complete - Processed {loop_processed_files} files | Total valid: {total_keys_found} | Total rate limited: {total_rate_limited_keys}")
            
            # 显示最终验证统计
            print_validation_stats()
            
            # 显示Token状态
            if loop_count % 5 == 0:  # 每5个循环显示一次
                token_summary = github_utils.get_token_status()
                if "active_tokens" in token_summary:
                    logger.info(f"📊 Token Status - Active: {token_summary['active_tokens']}/{token_summary['total_tokens']}, Remaining calls: {token_summary.get('total_remaining_calls', 'N/A')}")

            logger.info(f"💤 Sleeping for 10 seconds...")
            time.sleep(10)

        except KeyboardInterrupt:
            logger.info("⛔ Interrupted by user")
            checkpoint.update_scan_time()
            file_manager.save_checkpoint(checkpoint)
            logger.info(f"📊 Final stats - Valid keys: {total_keys_found}, Rate limited: {total_rate_limited_keys}")
            
            # 显示最终性能统计
            print_validation_stats()
            
            logger.info("🔚 Shutting down sync utils...")
            sync_utils.shutdown()
            
            logger.info("🔚 Shutting down parallel validator...")
            parallel_validator.shutdown()
            break
        except Exception as e:
            logger.error(f"💥 Unexpected error: {e}")
            traceback.print_exc()
            logger.info("🔄 Continuing...")
            continue


if __name__ == "__main__":
    main()