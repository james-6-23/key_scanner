# 🏥 Token Health Monitor - 使用指南

## 📖 概述

Token Health Monitor是一个全面的GitHub Token健康监控工具，提供实时验证、性能分析、健康评分和智能告警功能。

### 核心功能

- ✅ **实时验证** - 验证token有效性和认证状态
- 📊 **性能指标** - 响应时间、成功率、错误频率监控
- 🎯 **健康评分** - 基于多维度的0-100分健康评分
- 🚨 **智能告警** - 自动检测异常并生成告警
- 📈 **仪表板显示** - 彩色编码的实时状态仪表板
- 📝 **详细报告** - JSON格式的诊断报告和历史记录

## 🚀 快速开始

### 基本用法

#### 1. 准备Token文件

创建一个包含GitHub tokens的文本文件（例如：`github_tokens.txt`）：

```txt
ghp_your_token_1_here_xxxxxxxxxxxxxxxxxxxxx
ghp_your_token_2_here_xxxxxxxxxxxxxxxxxxxxx
ghp_your_token_3_here_xxxxxxxxxxxxxxxxxxxxx
# 支持注释
```

#### 2. 运行单次健康检查

```bash
python token_health_monitor.py github_tokens.txt
```

#### 3. 运行持续监控

```bash
python token_health_monitor.py github_tokens.txt --continuous
```

## 📊 仪表板说明

运行后会显示彩色的实时仪表板：

```
====================================================================================================
                        🔑 TOKEN HEALTH MONITOR DASHBOARD 🔑
====================================================================================================
📅 2024-12-08 10:30:45 | 📊 Monitoring 10 tokens
====================================================================================================

📈 SUMMARY: Active: 8 | Invalid: 1 | Rate Limited: 1
----------------------------------------------------------------------------------------------------

Token                Status       Health   Remaining   Success%   Avg RT   Errors/h   Last Success
----------------------------------------------------------------------------------------------------
ghp_abc...xyz        ✓ Active     95%      4523        98.5%      0.45s    0          2024-12-08 10:30:00
ghp_def...uvw        ⚠ Limited    45%      0           95.0%      0.89s    2          2024-12-08 10:25:00
ghp_ghi...rst        ✗ Invalid    0%       0           0.0%       -        10         Never
```

### 状态指示器

- ✅ **绿色** - 健康状态良好
- ⚠️ **黄色** - 需要注意
- 🔴 **红色** - 严重问题

### 健康评分计算

健康评分（0-100）基于以下因素：

| 因素 | 权重 | 说明 |
|------|------|------|
| 有效性 | 40% | Token是否有效 |
| 剩余调用 | 20% | API调用配额 |
| 成功率 | 20% | 请求成功率 |
| 响应时间 | 10% | 平均响应延迟 |
| 错误频率 | 10% | 最近一小时错误数 |

## 🎯 命令行参数

```bash
python token_health_monitor.py [options] <tokens_file>
```

### 必需参数

- `tokens_file` - Token文件路径

### 可选参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--output-dir` | 报告输出目录 | `./token_health_reports` |
| `--interval` | 持续模式检查间隔（秒） | `60` |
| `--alert-threshold` | 告警阈值（健康分数） | `70` |
| `--continuous` | 启用持续监控模式 | `False` |
| `--no-color` | 禁用彩色输出 | `False` |

### 使用示例

#### 自定义输出目录
```bash
python token_health_monitor.py github_tokens.txt --output-dir ./reports
```

#### 持续监控，每30秒检查一次
```bash
python token_health_monitor.py github_tokens.txt --continuous --interval 30
```

#### 设置告警阈值为80分
```bash
python token_health_monitor.py github_tokens.txt --alert-threshold 80
```

#### 无颜色输出（用于日志记录）
```bash
python token_health_monitor.py github_tokens.txt --no-color > health_check.log
```

## 📝 输出文件

### 1. 健康报告（JSON）

位置：`token_health_reports/health_report_YYYYMMDD_HHMMSS.json`

```json
{
  "timestamp": "2024-12-08T10:30:45",
  "summary": {
    "total_tokens": 10,
    "active": 8,
    "invalid": 1,
    "rate_limited": 1,
    "avg_health_score": 75.5
  },
  "tokens": [
    {
      "token": "ghp_abc...xyz",
      "status": "active",
      "health_score": 95,
      "remaining_calls": 4523,
      "success_rate": 98.5,
      "avg_response_time": 0.45,
      "alerts": [],
      "recommendations": []
    }
  ]
}
```

### 2. 历史记录

位置：`token_health_reports/token_health_history.jsonl`

每次检查追加一行JSON记录，用于趋势分析。

## 🚨 告警类型

### 严重告警（CRITICAL）

- Token无效或过期
- API调用配额少于10次
- 健康分数低于50

### 警告（WARNING）

- API调用配额少于100次
- 最近一小时错误超过5次
- 平均响应时间超过2秒
- 成功率低于80%

## 💡 建议和优化

### Token轮换建议

系统会根据以下情况自动生成轮换建议：

1. **立即替换**
   - Token无效
   - 健康分数 < 30

2. **尽快轮换**
   - 剩余调用 < 100
   - 健康分数 < 50

3. **密切监控**
   - 剩余调用 < 500
   - 错误率上升
   - Token年龄 > 90天

### 性能优化建议

1. **响应时间优化**
   - 使用代理服务器
   - 选择地理位置更近的节点

2. **配额管理**
   - 增加token数量
   - 实施请求限流

3. **错误处理**
   - 检查网络连接
   - 验证token权限

## 🔧 集成到CI/CD

### GitHub Actions示例

```yaml
name: Token Health Check

on:
  schedule:
    - cron: '0 */6 * * *'  # 每6小时运行一次
  workflow_dispatch:

jobs:
  health-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install requests
      
      - name: Run health check
        run: |
          python token_health_monitor.py github_tokens.txt
      
      - name: Upload report
        uses: actions/upload-artifact@v2
        with:
          name: health-report
          path: token_health_reports/
```

### Docker运行

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY token_health_monitor.py .
COPY requirements.txt .
RUN pip install -r requirements.txt

ENTRYPOINT ["python", "token_health_monitor.py"]
```

```bash
docker build -t token-monitor .
docker run -v $(pwd)/tokens:/app/tokens token-monitor /app/tokens/github_tokens.txt
```

## 📊 监控指标解释

### 响应时间指标

- **平均响应时间** - 所有请求的平均延迟
- **最大响应时间** - 最慢请求的延迟
- **最小响应时间** - 最快请求的延迟

### 成功率计算

```
成功率 = (成功请求数 / 总请求数) × 100%
```

### API使用率

```
使用率 = ((总配额 - 剩余配额) / 总配额) × 100%
```

### Token年龄

从首次使用到现在的天数，用于安全性评估。

## 🛠️ 故障排查

### 常见问题

#### 1. "Token file not found"
- 确认文件路径正确
- 检查文件权限

#### 2. "Connection timeout"
- 检查网络连接
- 考虑使用代理
- 增加超时时间

#### 3. "Authentication failed"
- 验证token格式（ghp_开头）
- 确认token未过期
- 检查token权限

### 调试模式

设置环境变量启用详细日志：

```bash
export LOG_LEVEL=DEBUG
python token_health_monitor.py github_tokens.txt
```

## 🔄 与主项目集成

### 1. 定期健康检查

在cron中设置定期任务：

```bash
# 每小时检查一次
0 * * * * cd /path/to/project && python token_health_monitor.py github_tokens.txt
```

### 2. 集成到主扫描器

在主程序启动前运行健康检查：

```python
import subprocess
import json

# 运行健康检查
result = subprocess.run(
    ["python", "token_health_monitor.py", "github_tokens.txt"],
    capture_output=True
)

# 读取报告
with open("token_health_reports/latest_report.json") as f:
    report = json.load(f)

# 过滤健康的tokens
healthy_tokens = [
    t for t in report["tokens"] 
    if t["health_score"] > 70
]
```

## 📈 最佳实践

1. **定期监控**
   - 生产环境每小时检查一次
   - 开发环境每天检查一次

2. **告警响应**
   - 健康分数 < 50：立即处理
   - 健康分数 < 70：24小时内处理
   - 健康分数 < 90：计划处理

3. **Token池管理**
   - 保持至少20%的备用tokens
   - 定期轮换老旧tokens
   - 记录token创建和废弃

4. **报告归档**
   - 保留至少30天的历史数据
   - 定期分析趋势
   - 识别异常模式

## 🔗 相关文档

- [Token管理指南](docs/TOKEN_MANAGEMENT_GUIDE.md)
- [项目主文档](README.md)
- [API密钥扫描器](app/api_key_scanner.py)

---

**版本**: 1.0.0 | **更新日期**: 2024-12-08 | **作者**: Key Scanner Team