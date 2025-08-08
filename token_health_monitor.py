#!/usr/bin/env python3
"""
GitHub Token Health Monitor - 综合Token健康监控工具
实时验证、性能分析、健康评分和告警系统
"""

import os
import sys
import json
import time
import argparse
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from collections import deque
from pathlib import Path
import statistics
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common.Logger import logger
from common.config import Config

# ANSI颜色代码
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    
    @staticmethod
    def green(text): return f"{Colors.OKGREEN}{text}{Colors.ENDC}"
    
    @staticmethod
    def red(text): return f"{Colors.FAIL}{text}{Colors.ENDC}"
    
    @staticmethod
    def yellow(text): return f"{Colors.WARNING}{text}{Colors.ENDC}"
    
    @staticmethod
    def blue(text): return f"{Colors.OKBLUE}{text}{Colors.ENDC}"
    
    @staticmethod
    def cyan(text): return f"{Colors.OKCYAN}{text}{Colors.ENDC}"
    
    @staticmethod
    def bold(text): return f"{Colors.BOLD}{text}{Colors.ENDC}"


@dataclass
class TokenMetrics:
    """Token性能指标"""
    token: str
    masked_token: str = ""
    status: str = "unknown"  # active, expired, invalid, rate_limited
    is_valid: bool = False
    remaining_calls: int = 0
    rate_limit_total: int = 5000
    reset_time: int = 0
    response_times: deque = field(default_factory=lambda: deque(maxlen=100))
    error_count: int = 0
    error_count_last_hour: int = 0
    success_count: int = 0
    last_success_time: Optional[datetime] = None
    last_error_time: Optional[datetime] = None
    last_error_message: str = ""
    created_time: datetime = field(default_factory=datetime.now)
    last_check_time: Optional[datetime] = None
    health_score: float = 100.0
    alerts: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if len(self.token) > 10:
            self.masked_token = f"{self.token[:7]}...{self.token[-4:]}"
        else:
            self.masked_token = "***"
    
    @property
    def avg_response_time(self) -> float:
        """平均响应时间"""
        if self.response_times:
            return statistics.mean(self.response_times)
        return 0.0
    
    @property
    def max_response_time(self) -> float:
        """最大响应时间"""
        if self.response_times:
            return max(self.response_times)
        return 0.0
    
    @property
    def min_response_time(self) -> float:
        """最小响应时间"""
        if self.response_times:
            return min(self.response_times)
        return 0.0
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        total = self.success_count + self.error_count
        if total > 0:
            return (self.success_count / total) * 100
        return 100.0
    
    @property
    def usage_percentage(self) -> float:
        """API使用率"""
        if self.rate_limit_total > 0:
            used = self.rate_limit_total - self.remaining_calls
            return (used / self.rate_limit_total) * 100
        return 0.0
    
    @property
    def token_age_days(self) -> int:
        """Token年龄（天）"""
        return (datetime.now() - self.created_time).days
    
    def calculate_health_score(self) -> float:
        """
        计算健康评分 (0-100)
        基于多个因素：有效性、剩余调用、成功率、响应时间、错误频率
        """
        score = 0.0
        
        # 1. 有效性 (40分)
        if self.is_valid:
            score += 40
        else:
            return 0.0  # 无效token直接0分
        
        # 2. 剩余调用 (20分)
        if self.remaining_calls > 1000:
            score += 20
        elif self.remaining_calls > 500:
            score += 15
        elif self.remaining_calls > 100:
            score += 10
        elif self.remaining_calls > 10:
            score += 5
        
        # 3. 成功率 (20分)
        success_rate = self.success_rate
        if success_rate >= 95:
            score += 20
        elif success_rate >= 90:
            score += 15
        elif success_rate >= 80:
            score += 10
        elif success_rate >= 70:
            score += 5
        
        # 4. 响应时间 (10分)
        avg_time = self.avg_response_time
        if avg_time > 0:
            if avg_time < 0.5:
                score += 10
            elif avg_time < 1.0:
                score += 7
            elif avg_time < 2.0:
                score += 5
            elif avg_time < 3.0:
                score += 3
        
        # 5. 最近错误 (10分)
        if self.error_count_last_hour == 0:
            score += 10
        elif self.error_count_last_hour < 3:
            score += 7
        elif self.error_count_last_hour < 5:
            score += 5
        elif self.error_count_last_hour < 10:
            score += 2
        
        self.health_score = min(100, max(0, score))
        return self.health_score
    
    def generate_alerts(self) -> List[str]:
        """生成告警"""
        self.alerts.clear()
        
        # 严重告警
        if not self.is_valid:
            self.alerts.append("CRITICAL: Token is invalid or expired")
        
        if self.remaining_calls < 10:
            self.alerts.append("CRITICAL: Less than 10 API calls remaining")
        
        # 警告
        if self.remaining_calls < 100:
            self.alerts.append("WARNING: Low API calls remaining")
        
        if self.error_count_last_hour > 5:
            self.alerts.append(f"WARNING: High error rate ({self.error_count_last_hour} errors in last hour)")
        
        if self.avg_response_time > 2.0:
            self.alerts.append(f"WARNING: Slow response time ({self.avg_response_time:.2f}s avg)")
        
        if self.success_rate < 80:
            self.alerts.append(f"WARNING: Low success rate ({self.success_rate:.1f}%)")
        
        return self.alerts
    
    def generate_recommendations(self) -> List[str]:
        """生成建议"""
        self.recommendations.clear()
        
        if not self.is_valid:
            self.recommendations.append("Replace this token immediately")
        elif self.remaining_calls < 100:
            self.recommendations.append("Consider rotating to a fresh token soon")
        elif self.remaining_calls < 500:
            self.recommendations.append("Monitor usage closely, may need rotation")
        
        if self.error_count_last_hour > 10:
            self.recommendations.append("Investigate error causes, possible token issues")
        
        if self.avg_response_time > 3.0:
            self.recommendations.append("Consider using a different token or proxy")
        
        if self.token_age_days > 90:
            self.recommendations.append("Token is old, consider rotation for security")
        
        return self.recommendations


class TokenHealthMonitor:
    """Token健康监控器"""
    
    def __init__(self, tokens_file: str, 
                 output_dir: str = "./token_health_reports",
                 check_interval: int = 60,
                 alert_threshold: int = 70):
        """
        初始化监控器
        
        Args:
            tokens_file: Token文件路径
            output_dir: 输出目录
            check_interval: 检查间隔（秒）
            alert_threshold: 告警阈值（健康分数）
        """
        self.tokens_file = Path(tokens_file)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.check_interval = check_interval
        self.alert_threshold = alert_threshold
        
        self.metrics: Dict[str, TokenMetrics] = {}
        self.history_file = self.output_dir / "token_health_history.jsonl"
        self.report_file = self.output_dir / f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # 加载tokens
        self._load_tokens()
        
        # 加载历史数据
        self._load_history()
    
    def _load_tokens(self) -> None:
        """加载tokens"""
        if not self.tokens_file.exists():
            logger.error(f"Token file not found: {self.tokens_file}")
            sys.exit(1)
        
        tokens = []
        with open(self.tokens_file, 'r', encoding='utf-8') as f:
            for line in f:
                token = line.strip()
                if token and not token.startswith('#'):
                    tokens.append(token)
                    if token not in self.metrics:
                        self.metrics[token] = TokenMetrics(token=token)
        
        logger.info(f"Loaded {len(tokens)} tokens from {self.tokens_file}")
    
    def _load_history(self) -> None:
        """加载历史数据"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            # 恢复部分历史数据
                            token = data.get('token')
                            if token and token in self.metrics:
                                metrics = self.metrics[token]
                                metrics.error_count = data.get('error_count', 0)
                                metrics.success_count = data.get('success_count', 0)
                                if data.get('last_success_time'):
                                    metrics.last_success_time = datetime.fromisoformat(data['last_success_time'])
            except Exception as e:
                logger.warning(f"Failed to load history: {e}")
    
    def validate_token(self, token: str) -> Tuple[bool, Dict[str, Any]]:
        """
        验证单个token
        
        Returns:
            (is_valid, response_data)
        """
        metrics = self.metrics[token]
        start_time = time.time()
        
        try:
            # GitHub API验证
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # 使用rate_limit端点获取详细信息
            response = requests.get(
                "https://api.github.com/rate_limit",
                headers=headers,
                timeout=10
            )
            
            response_time = time.time() - start_time
            metrics.response_times.append(response_time)
            metrics.last_check_time = datetime.now()
            
            if response.status_code == 200:
                data = response.json()
                rate_info = data.get('rate', {})
                
                metrics.is_valid = True
                metrics.status = "active"
                metrics.remaining_calls = rate_info.get('remaining', 0)
                metrics.rate_limit_total = rate_info.get('limit', 5000)
                metrics.reset_time = rate_info.get('reset', 0)
                metrics.success_count += 1
                metrics.last_success_time = datetime.now()
                
                # 检查是否被限流
                if metrics.remaining_calls == 0:
                    metrics.status = "rate_limited"
                
                return True, data
            
            elif response.status_code == 401:
                metrics.is_valid = False
                metrics.status = "invalid"
                metrics.error_count += 1
                metrics.last_error_time = datetime.now()
                metrics.last_error_message = "Authentication failed"
                return False, {"error": "Invalid token"}
            
            else:
                metrics.error_count += 1
                metrics.last_error_time = datetime.now()
                metrics.last_error_message = f"HTTP {response.status_code}"
                return False, {"error": f"HTTP {response.status_code}"}
                
        except requests.exceptions.Timeout:
            metrics.error_count += 1
            metrics.last_error_time = datetime.now()
            metrics.last_error_message = "Timeout"
            return False, {"error": "Timeout"}
            
        except Exception as e:
            metrics.error_count += 1
            metrics.last_error_time = datetime.now()
            metrics.last_error_message = str(e)
            return False, {"error": str(e)}
    
    def validate_all_tokens(self) -> None:
        """并发验证所有tokens"""
        logger.info(f"Starting validation of {len(self.metrics)} tokens...")
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(self.validate_token, token): token
                for token in self.metrics.keys()
            }
            
            for future in as_completed(futures):
                token = futures[future]
                try:
                    is_valid, data = future.result()
                    metrics = self.metrics[token]
                    
                    # 更新最近一小时错误计数
                    if metrics.last_error_time:
                        hour_ago = datetime.now() - timedelta(hours=1)
                        if metrics.last_error_time > hour_ago:
                            metrics.error_count_last_hour = metrics.error_count
                    
                    # 计算健康分数
                    metrics.calculate_health_score()
                    
                    # 生成告警和建议
                    metrics.generate_alerts()
                    metrics.generate_recommendations()
                    
                except Exception as e:
                    logger.error(f"Error validating token: {e}")
    
    def display_dashboard(self) -> None:
        """显示仪表板"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print(Colors.bold("=" * 100))
        print(Colors.bold(Colors.cyan("                        🔑 TOKEN HEALTH MONITOR DASHBOARD 🔑")))
        print(Colors.bold("=" * 100))
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 📊 Monitoring {len(self.metrics)} tokens")
        print("=" * 100)
        
        # 统计摘要
        active_count = sum(1 for m in self.metrics.values() if m.status == "active")
        invalid_count = sum(1 for m in self.metrics.values() if m.status == "invalid")
        rate_limited_count = sum(1 for m in self.metrics.values() if m.status == "rate_limited")
        
        print(f"\n📈 SUMMARY: {Colors.green(f'Active: {active_count}')} | "
              f"{Colors.red(f'Invalid: {invalid_count}')} | "
              f"{Colors.yellow(f'Rate Limited: {rate_limited_count}')}")
        print("-" * 100)
        
        # Token详细信息表格
        print(f"\n{'Token':<20} {'Status':<12} {'Health':<8} {'Remaining':<10} "
              f"{'Success%':<10} {'Avg RT':<8} {'Errors/h':<10} {'Last Success':<20}")
        print("-" * 100)
        
        # 按健康分数排序
        sorted_metrics = sorted(self.metrics.values(), 
                               key=lambda x: x.health_score, 
                               reverse=True)
        
        for metrics in sorted_metrics:
            # 状态颜色
            if metrics.status == "active":
                status_str = Colors.green("✓ Active")
            elif metrics.status == "invalid":
                status_str = Colors.red("✗ Invalid")
            elif metrics.status == "rate_limited":
                status_str = Colors.yellow("⚠ Limited")
            else:
                status_str = "? Unknown"
            
            # 健康分数颜色
            health = metrics.health_score
            if health >= 80:
                health_str = Colors.green(f"{health:.0f}%")
            elif health >= 60:
                health_str = Colors.yellow(f"{health:.0f}%")
            else:
                health_str = Colors.red(f"{health:.0f}%")
            
            # 剩余调用颜色
            remaining = metrics.remaining_calls
            if remaining > 1000:
                remaining_str = Colors.green(str(remaining))
            elif remaining > 100:
                remaining_str = Colors.yellow(str(remaining))
            else:
                remaining_str = Colors.red(str(remaining))
            
            # 成功率颜色
            success_rate = metrics.success_rate
            if success_rate >= 95:
                success_str = Colors.green(f"{success_rate:.1f}%")
            elif success_rate >= 80:
                success_str = Colors.yellow(f"{success_rate:.1f}%")
            else:
                success_str = Colors.red(f"{success_rate:.1f}%")
            
            # 响应时间
            avg_rt = metrics.avg_response_time
            if avg_rt < 1.0:
                rt_str = Colors.green(f"{avg_rt:.2f}s")
            elif avg_rt < 2.0:
                rt_str = Colors.yellow(f"{avg_rt:.2f}s")
            else:
                rt_str = Colors.red(f"{avg_rt:.2f}s")
            
            # 错误计数
            errors = metrics.error_count_last_hour
            if errors == 0:
                error_str = Colors.green("0")
            elif errors < 5:
                error_str = Colors.yellow(str(errors))
            else:
                error_str = Colors.red(str(errors))
            
            # 最后成功时间
            if metrics.last_success_time:
                last_success = metrics.last_success_time.strftime("%Y-%m-%d %H:%M:%S")
            else:
                last_success = "Never"
            
            print(f"{metrics.masked_token:<20} {status_str:<20} {health_str:<15} {remaining_str:<15} "
                  f"{success_str:<15} {rt_str:<12} {error_str:<15} {last_success:<20}")
            
            # 显示告警
            if metrics.alerts:
                for alert in metrics.alerts:
                    if "CRITICAL" in alert:
                        print(f"  └─ {Colors.red('🚨 ' + alert)}")
                    else:
                        print(f"  └─ {Colors.yellow('⚠️  ' + alert)}")
        
        print("=" * 100)
        
        # 显示建议
        critical_tokens = [m for m in sorted_metrics if m.health_score < self.alert_threshold]
        if critical_tokens:
            print(Colors.bold("\n🔔 RECOMMENDATIONS:"))
            for metrics in critical_tokens[:5]:  # 显示前5个需要关注的
                print(f"\n{Colors.yellow(metrics.masked_token)}:")
                for rec in metrics.recommendations:
                    print(f"  • {rec}")
    
    def save_report(self) -> None:
        """保存JSON报告"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tokens": len(self.metrics),
                "active": sum(1 for m in self.metrics.values() if m.status == "active"),
                "invalid": sum(1 for m in self.metrics.values() if m.status == "invalid"),
                "rate_limited": sum(1 for m in self.metrics.values() if m.status == "rate_limited"),
                "avg_health_score": statistics.mean(m.health_score for m in self.metrics.values()) if self.metrics else 0
            },
            "tokens": []
        }
        
        for token, metrics in self.metrics.items():
            token_data = {
                "token": metrics.masked_token,
                "status": metrics.status,
                "health_score": metrics.health_score,
                "is_valid": metrics.is_valid,
                "remaining_calls": metrics.remaining_calls,
                "rate_limit_total": metrics.rate_limit_total,
                "usage_percentage": metrics.usage_percentage,
                "success_rate": metrics.success_rate,
                "avg_response_time": metrics.avg_response_time,
                "max_response_time": metrics.max_response_time,
                "min_response_time": metrics.min_response_time,
                "error_count": metrics.error_count,
                "error_count_last_hour": metrics.error_count_last_hour,
                "success_count": metrics.success_count,
                "last_success_time": metrics.last_success_time.isoformat() if metrics.last_success_time else None,
                "last_error_time": metrics.last_error_time.isoformat() if metrics.last_error_time else None,
                "last_error_message": metrics.last_error_message,
                "token_age_days": metrics.token_age_days,
                "alerts": metrics.alerts,
                "recommendations": metrics.recommendations
            }
            report["tokens"].append(token_data)
        
        # 保存报告
        with open(self.report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Report saved to {self.report_file}")
        
        # 追加到历史文件
        with open(self.history_file, 'a', encoding='utf-8') as f:
            for token, metrics in self.metrics.items():
                history_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "token": token,
                    "health_score": metrics.health_score,
                    "remaining_calls": metrics.remaining_calls,
                    "error_count": metrics.error_count,
                    "success_count": metrics.success_count,
                    "last_success_time": metrics.last_success_time.isoformat() if metrics.last_success_time else None
                }
                f.write(json.dumps(history_entry) + '\n')
    
    def run_continuous_monitoring(self) -> None:
        """运行持续监控"""
        logger.info("Starting continuous monitoring...")
        
        try:
            while True:
                # 验证所有tokens
                self.validate_all_tokens()
                
                # 显示仪表板
                self.display_dashboard()
                
                # 保存报告
                self.save_report()
                
                # 检查告警
                self._check_alerts()
                
                # 等待下次检查
                print(f"\n⏰ Next check in {self.check_interval} seconds... (Press Ctrl+C to stop)")
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            print("\n\n👋 Monitoring stopped by user")
            self.save_report()
            sys.exit(0)
    
    def _check_alerts(self) -> None:
        """检查并发送告警"""
        critical_tokens = []
        warning_tokens = []
        
        for metrics in self.metrics.values():
            if metrics.health_score < 50:
                critical_tokens.append(metrics)
            elif metrics.health_score < self.alert_threshold:
                warning_tokens.append(metrics)
        
        if critical_tokens:
            print(Colors.bold(Colors.red(f"\n🚨 CRITICAL ALERT: {len(critical_tokens)} tokens need immediate attention!")))
            
        if warning_tokens:
            print(Colors.bold(Colors.yellow(f"\n⚠️  WARNING: {len(warning_tokens)} tokens need attention")))
    
    def run_single_check(self) -> None:
        """运行单次检查"""
        # 验证所有tokens
        self.validate_all_tokens()
        
        # 显示仪表板
        self.display_dashboard()
        
        # 保存报告
        self.save_report()
        
        # 检查告警
        self._check_alerts()
        
        print(f"\n✅ Health check completed. Report saved to {self.report_file}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="GitHub Token Health Monitor - Comprehensive token health monitoring tool"
    )
    parser.add_argument(
        "tokens_file",
        help="Path to tokens file (one token per line)"
    )
    parser.add_argument(
        "--output-dir",
        default="./token_health_reports",
        help="Output directory for reports (default: ./token_health_reports)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Check interval in seconds for continuous mode (default: 60)"
    )
    parser.add_argument(
        "--alert-threshold",
        type=int,
        default=70,
        help="Health score threshold for alerts (default: 70)"
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run in continuous monitoring mode"
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output"
    )
    
    args = parser.parse_args()
    
    # 禁用颜色（如果需要）
    if args.no_color:
        Colors.HEADER = Colors.OKBLUE = Colors.OKCYAN = Colors.OKGREEN = ''
        Colors.WARNING = Colors.FAIL = Colors.ENDC = Colors.BOLD = Colors.UNDERLINE = ''
    
    # 创建监控器
    monitor = TokenHealthMonitor(
        tokens_file=args.tokens_file,
        output_dir=args.output_dir,
        check_interval=args.interval,
        alert_threshold=args.alert_threshold
    )
    
    # 运行监控
    if args.continuous:
        monitor.run_continuous_monitoring()
    else:
        monitor.run_single_check()


if __name__ == "__main__":
    main()