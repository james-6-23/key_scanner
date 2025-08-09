#!/usr/bin/env python3
"""
扫描器性能基准测试
"""

import sys
import os
import time
import json
import random
import threading
import psutil
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(title):
    """打印标题"""
    print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{title:^60}{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")

class PerformanceBenchmark:
    """性能基准测试类"""
    
    def __init__(self):
        self.results = {}
        self.start_time = None
        self.process = psutil.Process()
        
    def measure_memory(self):
        """测量内存使用"""
        return self.process.memory_info().rss / 1024 / 1024  # MB
    
    def measure_cpu(self):
        """测量CPU使用率"""
        return self.process.cpu_percent(interval=0.1)
    
    def simulate_github_search(self, query, count=100):
        """模拟GitHub搜索"""
        print(f"模拟搜索: {query}")
        results = []
        
        start = time.time()
        for i in range(count):
            # 模拟网络延迟
            time.sleep(random.uniform(0.001, 0.005))
            results.append({
                "file": f"file_{i}.py",
                "content": f"AIzaSy{random.randint(1000000, 9999999)}",
                "repo": f"user/repo_{i}"
            })
        
        elapsed = time.time() - start
        rate = count / elapsed
        
        return {
            "query": query,
            "count": count,
            "time": elapsed,
            "rate": rate,
            "results": results
        }
    
    def simulate_key_validation(self, keys, max_workers=10):
        """模拟密钥验证"""
        print(f"模拟验证 {len(keys)} 个密钥 (并发: {max_workers})")
        
        def validate_key(key):
            # 模拟验证延迟
            time.sleep(random.uniform(0.01, 0.05))
            return random.choice([True, False])
        
        start = time.time()
        valid_keys = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(validate_key, key): key for key in keys}
            
            for future in as_completed(futures):
                key = futures[future]
                if future.result():
                    valid_keys.append(key)
        
        elapsed = time.time() - start
        rate = len(keys) / elapsed
        
        return {
            "total": len(keys),
            "valid": len(valid_keys),
            "time": elapsed,
            "rate": rate,
            "workers": max_workers
        }
    
    def benchmark_search_performance(self):
        """测试搜索性能"""
        print_header("搜索性能测试")
        
        queries = [
            "AIzaSy in:file",
            "sk-proj in:file",
            "api_key in:file extension:json",
        ]
        
        results = []
        total_time = 0
        total_count = 0
        
        for query in queries:
            result = self.simulate_github_search(query, count=50)
            results.append(result)
            total_time += result["time"]
            total_count += result["count"]
            
            print(f"  ✅ {query[:30]}: {result['rate']:.1f} 文件/秒")
        
        avg_rate = total_count / total_time if total_time > 0 else 0
        
        self.results["search"] = {
            "queries": len(queries),
            "total_files": total_count,
            "total_time": total_time,
            "avg_rate": avg_rate
        }
        
        print(f"\n{Colors.GREEN}平均搜索速度: {avg_rate:.1f} 文件/秒{Colors.RESET}")
        
    def benchmark_validation_performance(self):
        """测试验证性能"""
        print_header("验证性能测试")
        
        # 生成测试密钥
        test_keys = [f"AIzaSy{i:07d}" for i in range(100)]
        
        # 测试不同并发数
        worker_counts = [5, 10, 20]
        
        for workers in worker_counts:
            result = self.simulate_key_validation(test_keys, max_workers=workers)
            print(f"  并发 {workers:2d}: {result['rate']:.1f} 密钥/秒")
            
            self.results[f"validation_{workers}"] = result
        
        # 找出最佳并发数
        best_workers = max(worker_counts, 
                          key=lambda w: self.results[f"validation_{w}"]["rate"])
        best_rate = self.results[f"validation_{best_workers}"]["rate"]
        
        print(f"\n{Colors.GREEN}最佳并发数: {best_workers} (速度: {best_rate:.1f} 密钥/秒){Colors.RESET}")
    
    def benchmark_memory_usage(self):
        """测试内存使用"""
        print_header("内存使用测试")
        
        # 初始内存
        initial_memory = self.measure_memory()
        print(f"初始内存: {initial_memory:.2f} MB")
        
        # 模拟加载大量数据
        data = []
        for i in range(1000):
            data.append({
                "key": f"key_{i}",
                "value": "x" * 1000,
                "metadata": {"index": i}
            })
        
        # 测量内存增长
        loaded_memory = self.measure_memory()
        memory_growth = loaded_memory - initial_memory
        
        print(f"加载后内存: {loaded_memory:.2f} MB")
        print(f"内存增长: {memory_growth:.2f} MB")
        
        self.results["memory"] = {
            "initial": initial_memory,
            "loaded": loaded_memory,
            "growth": memory_growth
        }
        
        # 清理
        del data
        
        # 测量清理后内存
        cleaned_memory = self.measure_memory()
        print(f"清理后内存: {cleaned_memory:.2f} MB")
        
        if memory_growth > 100:
            print(f"{Colors.YELLOW}⚠️  内存使用较高{Colors.RESET}")
        else:
            print(f"{Colors.GREEN}✅ 内存使用正常{Colors.RESET}")
    
    def benchmark_cpu_usage(self):
        """测试CPU使用"""
        print_header("CPU使用测试")
        
        # 空闲CPU
        idle_cpu = self.measure_cpu()
        print(f"空闲CPU: {idle_cpu:.1f}%")
        
        # 模拟CPU密集任务
        print("运行CPU密集任务...")
        start = time.time()
        
        # 计算密集型操作
        result = 0
        for i in range(1000000):
            result += i ** 2
        
        elapsed = time.time() - start
        active_cpu = self.measure_cpu()
        
        print(f"活动CPU: {active_cpu:.1f}%")
        print(f"计算时间: {elapsed:.2f} 秒")
        
        self.results["cpu"] = {
            "idle": idle_cpu,
            "active": active_cpu,
            "computation_time": elapsed
        }
        
        if active_cpu > 80:
            print(f"{Colors.YELLOW}⚠️  CPU使用较高{Colors.RESET}")
        else:
            print(f"{Colors.GREEN}✅ CPU使用正常{Colors.RESET}")
    
    def benchmark_concurrent_operations(self):
        """测试并发操作"""
        print_header("并发操作测试")
        
        def concurrent_task(task_id):
            """模拟并发任务"""
            time.sleep(random.uniform(0.1, 0.3))
            return f"Task {task_id} completed"
        
        # 测试不同并发级别
        concurrency_levels = [10, 50, 100]
        
        for level in concurrency_levels:
            start = time.time()
            
            with ThreadPoolExecutor(max_workers=level) as executor:
                futures = [executor.submit(concurrent_task, i) for i in range(level)]
                results = [f.result() for f in as_completed(futures)]
            
            elapsed = time.time() - start
            throughput = level / elapsed
            
            print(f"  并发 {level:3d}: {throughput:.1f} 任务/秒")
            
            self.results[f"concurrent_{level}"] = {
                "tasks": level,
                "time": elapsed,
                "throughput": throughput
            }
        
        # 找出最佳并发级别
        best_level = max(concurrency_levels,
                        key=lambda l: self.results[f"concurrent_{l}"]["throughput"])
        best_throughput = self.results[f"concurrent_{best_level}"]["throughput"]
        
        print(f"\n{Colors.GREEN}最佳并发级别: {best_level} (吞吐量: {best_throughput:.1f} 任务/秒){Colors.RESET}")
    
    def benchmark_file_operations(self):
        """测试文件操作"""
        print_header("文件操作测试")
        
        test_dir = Path("benchmark_test")
        test_dir.mkdir(exist_ok=True)
        
        # 写入测试
        print("测试文件写入...")
        write_start = time.time()
        
        for i in range(100):
            file_path = test_dir / f"test_{i}.txt"
            file_path.write_text(f"Test content {i}\n" * 100)
        
        write_time = time.time() - write_start
        write_rate = 100 / write_time
        
        print(f"  写入速度: {write_rate:.1f} 文件/秒")
        
        # 读取测试
        print("测试文件读取...")
        read_start = time.time()
        
        for file_path in test_dir.glob("*.txt"):
            content = file_path.read_text()
        
        read_time = time.time() - read_start
        read_rate = 100 / read_time
        
        print(f"  读取速度: {read_rate:.1f} 文件/秒")
        
        # 清理
        for file_path in test_dir.glob("*.txt"):
            file_path.unlink()
        test_dir.rmdir()
        
        self.results["file_ops"] = {
            "write_rate": write_rate,
            "read_rate": read_rate,
            "write_time": write_time,
            "read_time": read_time
        }
        
        print(f"{Colors.GREEN}✅ 文件操作测试完成{Colors.RESET}")
    
    def generate_report(self):
        """生成性能报告"""
        print_header("性能测试报告")
        
        # 计算总分
        scores = {
            "搜索性能": min(100, self.results.get("search", {}).get("avg_rate", 0) * 2),
            "验证性能": min(100, max(
                self.results.get("validation_5", {}).get("rate", 0),
                self.results.get("validation_10", {}).get("rate", 0),
                self.results.get("validation_20", {}).get("rate", 0)
            ) * 2),
            "内存效率": max(0, 100 - self.results.get("memory", {}).get("growth", 100)),
            "CPU效率": max(0, 100 - self.results.get("cpu", {}).get("active", 100)),
            "并发能力": min(100, max(
                self.results.get("concurrent_10", {}).get("throughput", 0),
                self.results.get("concurrent_50", {}).get("throughput", 0),
                self.results.get("concurrent_100", {}).get("throughput", 0)
            ) / 10),
            "IO性能": min(100, (
                self.results.get("file_ops", {}).get("write_rate", 0) +
                self.results.get("file_ops", {}).get("read_rate", 0)
            ) / 2)
        }
        
        total_score = sum(scores.values()) / len(scores)
        
        print(f"{Colors.BOLD}性能评分:{Colors.RESET}")
        for category, score in scores.items():
            color = Colors.GREEN if score >= 80 else Colors.YELLOW if score >= 60 else Colors.RED
            print(f"  {category}: {color}{score:.1f}/100{Colors.RESET}")
        
        print(f"\n{Colors.BOLD}总体评分: {Colors.BLUE}{total_score:.1f}/100{Colors.RESET}")
        
        # 性能等级
        if total_score >= 80:
            grade = "优秀"
            color = Colors.GREEN
        elif total_score >= 60:
            grade = "良好"
            color = Colors.YELLOW
        else:
            grade = "需要优化"
            color = Colors.RED
        
        print(f"{Colors.BOLD}性能等级: {color}{grade}{Colors.RESET}")
        
        # 保存详细报告
        report_path = Path("benchmark_report.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "scores": scores,
                "total_score": total_score,
                "grade": grade,
                "details": self.results
            }, f, indent=2)
        
        print(f"\n{Colors.BLUE}详细报告已保存到: {report_path}{Colors.RESET}")
        
        # 优化建议
        print(f"\n{Colors.BOLD}优化建议:{Colors.RESET}")
        
        if scores["搜索性能"] < 60:
            print(f"  • 增加GitHub Token数量以提高API配额")
        
        if scores["验证性能"] < 60:
            print(f"  • 增加并发工作线程数")
        
        if scores["内存效率"] < 60:
            print(f"  • 优化数据结构，减少内存占用")
        
        if scores["CPU效率"] < 60:
            print(f"  • 优化算法，减少CPU密集操作")
        
        if scores["并发能力"] < 60:
            print(f"  • 使用异步IO提高并发性能")
        
        if scores["IO性能"] < 60:
            print(f"  • 使用缓存减少文件IO操作")

def main():
    """主函数"""
    print_header("扫描器性能基准测试")
    
    print(f"{Colors.YELLOW}开始性能测试，这可能需要几分钟...{Colors.RESET}\n")
    
    benchmark = PerformanceBenchmark()
    
    try:
        # 运行各项测试
        benchmark.benchmark_search_performance()
        benchmark.benchmark_validation_performance()
        benchmark.benchmark_memory_usage()
        benchmark.benchmark_cpu_usage()
        benchmark.benchmark_concurrent_operations()
        benchmark.benchmark_file_operations()
        
        # 生成报告
        benchmark.generate_report()
        
        print(f"\n{Colors.GREEN}{Colors.BOLD}✅ 性能测试完成！{Colors.RESET}")
        return 0
        
    except Exception as e:
        print(f"\n{Colors.RED}❌ 测试失败: {str(e)}{Colors.RESET}")
        return 1

if __name__ == "__main__":
    sys.exit(main())