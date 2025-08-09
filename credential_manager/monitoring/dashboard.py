"""
凭证管理系统监控仪表板
提供实时监控和可视化界面
"""

import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import deque, defaultdict
import logging

logger = logging.getLogger(__name__)

try:
    # 尝试导入可视化库（可选）
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.figure import Figure
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    logger.warning("Matplotlib not installed, graphical features disabled")


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self, max_history: int = 1000):
        """
        初始化指标收集器
        
        Args:
            max_history: 最大历史记录数
        """
        self.max_history = max_history
        self.metrics_history = defaultdict(lambda: deque(maxlen=max_history))
        self.events = deque(maxlen=max_history)
        self._lock = threading.Lock()
        
    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """
        记录指标
        
        Args:
            name: 指标名称
            value: 指标值
            tags: 标签
        """
        with self._lock:
            timestamp = datetime.now()
            self.metrics_history[name].append({
                'timestamp': timestamp,
                'value': value,
                'tags': tags or {}
            })
            
    def record_event(self, event_type: str, description: str, severity: str = 'info'):
        """
        记录事件
        
        Args:
            event_type: 事件类型
            description: 事件描述
            severity: 严重程度 (info, warning, error, critical)
        """
        with self._lock:
            self.events.append({
                'timestamp': datetime.now(),
                'type': event_type,
                'description': description,
                'severity': severity
            })
            
    def get_metric_history(self, name: str, hours: float = 1) -> List[Dict[str, Any]]:
        """
        获取指标历史
        
        Args:
            name: 指标名称
            hours: 查看过去多少小时
            
        Returns:
            指标历史列表
        """
        with self._lock:
            if name not in self.metrics_history:
                return []
                
            cutoff_time = datetime.now() - timedelta(hours=hours)
            return [
                m for m in self.metrics_history[name]
                if m['timestamp'] >= cutoff_time
            ]
            
    def get_recent_events(self, count: int = 50) -> List[Dict[str, Any]]:
        """获取最近的事件"""
        with self._lock:
            return list(self.events)[-count:]
            
    def get_current_metrics(self) -> Dict[str, Any]:
        """获取当前指标快照"""
        with self._lock:
            current = {}
            for name, history in self.metrics_history.items():
                if history:
                    latest = history[-1]
                    current[name] = {
                        'value': latest['value'],
                        'timestamp': latest['timestamp'].isoformat()
                    }
            return current


class Dashboard:
    """监控仪表板主类"""
    
    def __init__(self, credential_manager: Any, update_interval: int = 5):
        """
        初始化仪表板
        
        Args:
            credential_manager: 凭证管理器实例
            update_interval: 更新间隔（秒）
        """
        self.credential_manager = credential_manager
        self.update_interval = update_interval
        self.metrics_collector = MetricsCollector()
        self.is_running = False
        self._update_thread: Optional[threading.Thread] = None
        
    def start(self):
        """启动监控"""
        if self.is_running:
            logger.warning("Dashboard already running")
            return
            
        self.is_running = True
        self._update_thread = threading.Thread(
            target=self._update_loop,
            daemon=True
        )
        self._update_thread.start()
        logger.info("Dashboard started")
        
    def stop(self):
        """停止监控"""
        self.is_running = False
        if self._update_thread:
            self._update_thread.join(timeout=5)
        logger.info("Dashboard stopped")
        
    def _update_loop(self):
        """更新循环"""
        while self.is_running:
            try:
                self._collect_metrics()
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                
            time.sleep(self.update_interval)
            
    def _collect_metrics(self):
        """收集指标"""
        # 获取统计信息
        stats = self.credential_manager.get_statistics()
        
        # 记录总体指标
        self.metrics_collector.record_metric(
            'total_credentials',
            stats['total_credentials']
        )
        
        self.metrics_collector.record_metric(
            'average_health_score',
            stats['average_health_score']
        )
        
        # 记录状态分布
        for status, count in stats['by_status'].items():
            self.metrics_collector.record_metric(
                f'credentials_{status}',
                count,
                tags={'status': status}
            )
            
        # 记录服务类型分布
        if 'by_service' in stats:
            for service, count in stats['by_service'].items():
                self.metrics_collector.record_metric(
                    f'service_{service}',
                    count,
                    tags={'service': service}
                )
            
        # 检查告警条件
        self._check_alerts(stats)
        
    def _check_alerts(self, stats: Dict[str, Any]):
        """检查告警条件"""
        # 健康评分过低
        if stats['average_health_score'] < 50:
            self.metrics_collector.record_event(
                'health_alert',
                f"Average health score low: {stats['average_health_score']:.1f}",
                severity='warning'
            )
            
        # 活跃凭证过少
        active_count = stats['by_status'].get('active', 0)
        if active_count < 2:
            self.metrics_collector.record_event(
                'availability_alert',
                f"Only {active_count} active credentials",
                severity='critical'
            )
            
        # 失效凭证过多
        invalid_count = stats['by_status'].get('invalid', 0)
        if invalid_count > stats['total_credentials'] * 0.3:
            self.metrics_collector.record_event(
                'invalid_alert',
                f"High number of invalid credentials: {invalid_count}",
                severity='warning'
            )
            
    def get_summary(self) -> Dict[str, Any]:
        """获取仪表板摘要"""
        current_metrics = self.metrics_collector.get_current_metrics()
        recent_events = self.metrics_collector.get_recent_events(10)
        
        # 计算趋势
        trends = {}
        for metric_name in ['total_credentials', 'average_health_score']:
            history = self.metrics_collector.get_metric_history(metric_name, hours=1)
            if len(history) >= 2:
                old_value = history[0]['value']
                new_value = history[-1]['value']
                change = ((new_value - old_value) / old_value * 100) if old_value != 0 else 0
                trends[metric_name] = {
                    'direction': 'up' if change > 0 else 'down' if change < 0 else 'stable',
                    'change_percent': abs(change)
                }
                
        return {
            'timestamp': datetime.now().isoformat(),
            'current_metrics': current_metrics,
            'trends': trends,
            'recent_events': recent_events,
            'alerts': self._get_active_alerts()
        }
        
    def _get_active_alerts(self) -> List[Dict[str, Any]]:
        """获取活跃告警"""
        recent_events = self.metrics_collector.get_recent_events(50)
        alerts = [
            e for e in recent_events
            if e['severity'] in ['warning', 'error', 'critical']
        ]
        
        # 去重，只保留每种类型的最新告警
        unique_alerts = {}
        for alert in alerts:
            alert_type = alert['type']
            if alert_type not in unique_alerts or alert['timestamp'] > unique_alerts[alert_type]['timestamp']:
                unique_alerts[alert_type] = alert
                
        return list(unique_alerts.values())
        
    def generate_report(self, output_path: str):
        """
        生成监控报告
        
        Args:
            output_path: 输出路径
        """
        report = {
            'generated_at': datetime.now().isoformat(),
            'summary': self.get_summary(),
            'metrics_history': {},
            'events': self.metrics_collector.get_recent_events(100)
        }
        
        # 添加关键指标的历史数据
        key_metrics = [
            'total_credentials',
            'average_health_score',
            'credentials_active',
            'credentials_exhausted'
        ]
        
        for metric in key_metrics:
            history = self.metrics_collector.get_metric_history(metric, hours=24)
            if history:
                report['metrics_history'][metric] = [
                    {
                        'timestamp': h['timestamp'].isoformat(),
                        'value': h['value']
                    }
                    for h in history
                ]
                
        # 保存报告
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
            
        logger.info(f"Report generated: {output_path}")
        
    def plot_metrics(self, metric_names: List[str], hours: float = 24) -> Optional[Figure]:
        """
        绘制指标图表
        
        Args:
            metric_names: 要绘制的指标名称列表
            hours: 显示过去多少小时的数据
            
        Returns:
            Matplotlib图形对象，如果matplotlib未安装则返回None
        """
        if not HAS_MATPLOTLIB:
            logger.warning("Matplotlib not available, cannot plot metrics")
            return None
            
        fig, axes = plt.subplots(len(metric_names), 1, figsize=(12, 4 * len(metric_names)))
        
        if len(metric_names) == 1:
            axes = [axes]
            
        for ax, metric_name in zip(axes, metric_names):
            history = self.metrics_collector.get_metric_history(metric_name, hours)
            
            if not history:
                ax.text(0.5, 0.5, f'No data for {metric_name}',
                       ha='center', va='center', transform=ax.transAxes)
                continue
                
            timestamps = [h['timestamp'] for h in history]
            values = [h['value'] for h in history]
            
            ax.plot(timestamps, values, marker='o', linestyle='-', markersize=3)
            ax.set_title(f'{metric_name} (Last {hours} hours)')
            ax.set_xlabel('Time')
            ax.set_ylabel('Value')
            ax.grid(True, alpha=0.3)
            
            # 格式化x轴时间标签
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=max(1, int(hours/6))))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            
        plt.tight_layout()
        return fig


class ConsoleDashboard:
    """控制台仪表板 - 文本界面"""
    
    def __init__(self, dashboard: Dashboard):
        """
        初始化控制台仪表板
        
        Args:
            dashboard: 仪表板实例
        """
        self.dashboard = dashboard
        
    def display(self):
        """显示控制台仪表板"""
        summary = self.dashboard.get_summary()
        
        # 清屏（跨平台）
        import os
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # 打印标题
        print("=" * 80)
        print(" " * 25 + "凭证管理系统监控仪表板")
        print("=" * 80)
        print(f"更新时间: {summary['timestamp']}")
        print()
        
        # 打印当前指标
        print("📊 当前指标:")
        print("-" * 40)
        
        metrics = summary['current_metrics']
        for name, data in metrics.items():
            value = data['value']
            if isinstance(value, float):
                print(f"  {name:30} {value:>10.2f}")
            else:
                print(f"  {name:30} {value:>10}")
                
        print()
        
        # 打印趋势
        if summary['trends']:
            print("📈 趋势分析:")
            print("-" * 40)
            for metric, trend in summary['trends'].items():
                direction_symbol = "↑" if trend['direction'] == 'up' else "↓" if trend['direction'] == 'down' else "→"
                print(f"  {metric:30} {direction_symbol} {trend['change_percent']:>6.1f}%")
            print()
            
        # 打印告警
        alerts = summary['alerts']
        if alerts:
            print("⚠️  活跃告警:")
            print("-" * 40)
            for alert in alerts[:5]:  # 只显示前5个
                severity_symbol = "🔴" if alert['severity'] == 'critical' else "🟡" if alert['severity'] == 'warning' else "🔵"
                print(f"  {severity_symbol} [{alert['type']}] {alert['description']}")
            print()
            
        # 打印最近事件
        print("📝 最近事件:")
        print("-" * 40)
        for event in summary['recent_events'][:5]:  # 只显示前5个
            timestamp = datetime.fromisoformat(event['timestamp']).strftime('%H:%M:%S')
            print(f"  [{timestamp}] {event['type']}: {event['description'][:50]}")
            
        print()
        print("=" * 80)
        
    def run_interactive(self, refresh_interval: int = 5):
        """
        运行交互式控制台
        
        Args:
            refresh_interval: 刷新间隔（秒）
        """
        import sys
        
        print("启动交互式监控仪表板...")
        print("按 Ctrl+C 退出")
        
        try:
            while True:
                self.display()
                time.sleep(refresh_interval)
                
        except KeyboardInterrupt:
            print("\n\n监控已停止")
            sys.exit(0)


def create_dashboard(credential_manager: Any) -> Dashboard:
    """
    创建仪表板实例
    
    Args:
        credential_manager: 凭证管理器实例
        
    Returns:
        仪表板实例
    """
    dashboard = Dashboard(credential_manager)
    dashboard.start()
    return dashboard


def start_monitoring_server(credential_manager: Any, port: int = 8080):
    """
    启动监控服务器（简化版本）
    
    Args:
        credential_manager: 凭证管理器实例
        port: 监控端口
        
    Returns:
        Dashboard实例
    """
    dashboard = create_dashboard(credential_manager)
    logger.info(f"Monitoring dashboard started (console mode)")
    
    # 创建控制台仪表板
    console = ConsoleDashboard(dashboard)
    
    # 在后台线程运行
    import threading
    monitor_thread = threading.Thread(
        target=lambda: logger.info("Monitoring running in background"),
        daemon=True
    )
    monitor_thread.start()
    
    return dashboard


# 为了兼容性，添加MonitoringDashboard别名
MonitoringDashboard = Dashboard