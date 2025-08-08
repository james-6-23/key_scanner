# 🔑 GitHub Token管理系统使用指南

## 📖 概述

本项目实现了一个强大的双模式GitHub Token配置系统，支持自动管理功能：

- **小规模部署**：在`.env`文件中使用逗号分隔的tokens
- **大规模部署**：从外部txt文件读取行分隔的tokens
- **智能生命周期管理**：自动监控API速率限制、移除耗尽的tokens、归档无效tokens

## 🎯 核心特性

### 1. 双模式配置
- ✅ 自动检测配置模式
- ✅ 无缝切换between两种模式
- ✅ 向后兼容传统配置

### 2. 生命周期管理
- ✅ 实时监控API速率限制
- ✅ 自动轮换tokens
- ✅ 智能移除耗尽的tokens
- ✅ 归档无效tokens到备份文件
- ✅ 自动恢复已重置的tokens

### 3. 并发安全
- ✅ 线程安全的token访问
- ✅ 并发请求的token分配
- ✅ 状态同步和持久化

## 🚀 快速开始

### 模式1：小规模部署（1-10个tokens）

适用于个人项目或小团队使用。

#### 配置步骤

1. 编辑`.env`文件：
```env
# 使用逗号分隔的tokens
GITHUB_TOKENS=ghp_token1,ghp_token2,ghp_token3

# 禁用外部文件模式
USE_EXTERNAL_TOKEN_FILE=false

# Token管理配置
TOKEN_AUTO_REMOVE_EXHAUSTED=true
TOKEN_MIN_REMAINING_CALLS=10
```

2. 运行程序：
```bash
python app/api_key_scanner.py
```

### 模式2：大规模部署（10+个tokens）

适用于企业级部署或需要管理大量tokens的场景。

#### 配置步骤

1. 创建token文件`github_tokens.txt`：
```txt
# 生产环境tokens
ghp_production_token_1_xxxxxxxxxxxxxxxxxxxxx
ghp_production_token_2_xxxxxxxxxxxxxxxxxxxxx
ghp_production_token_3_xxxxxxxxxxxxxxxxxxxxx

# 备用tokens
ghp_backup_token_1_xxxxxxxxxxxxxxxxxxxxxxxxx
ghp_backup_token_2_xxxxxxxxxxxxxxxxxxxxxxxxx
```

2. 编辑`.env`文件：
```env
# 启用外部文件模式
USE_EXTERNAL_TOKEN_FILE=true

# 指定token文件路径
GITHUB_TOKENS_FILE=github_tokens.txt

# Token管理配置
TOKEN_AUTO_REMOVE_EXHAUSTED=true
TOKEN_MIN_REMAINING_CALLS=10
TOKEN_ARCHIVE_DIR=./data/archived_tokens
```

3. 运行程序：
```bash
python app/api_key_scanner.py
```

## ⚙️ 配置选项详解

### 基础配置

| 配置项 | 说明 | 默认值 | 示例 |
|--------|------|--------|------|
| `USE_EXTERNAL_TOKEN_FILE` | 是否使用外部文件模式 | `false` | `true` |
| `GITHUB_TOKENS` | 逗号分隔的tokens（模式1） | 无 | `ghp_xxx,ghp_yyy` |
| `GITHUB_TOKENS_FILE` | 外部token文件路径（模式2） | `github_tokens.txt` | `tokens/prod.txt` |

### 管理配置

| 配置项 | 说明 | 默认值 | 建议值 |
|--------|------|--------|--------|
| `TOKEN_AUTO_REMOVE_EXHAUSTED` | 自动移除耗尽的tokens | `true` | `true` |
| `TOKEN_MIN_REMAINING_CALLS` | 最小剩余调用次数 | `10` | `10-50` |
| `TOKEN_ARCHIVE_DIR` | 归档目录 | `./data/archived_tokens` | 保持默认 |

## 📊 Token状态监控

### 实时状态查看

程序运行时会自动显示token状态：

```
🔑 TokenManager initialized with 10 tokens
📊 Token Status - Active: 8/10, Remaining calls: 35,420
⚠️ Token ghp_xxx...xxx has low remaining calls: 45 remaining
📦 Archived token ghp_yyy...yyy (reason: exhausted)
♻️ Reactivated token ghp_zzz...zzz
```

### 状态文件

Token状态会保存到`data/archived_tokens/token_stats.json`：

```json
{
  "timestamp": "2024-12-08T10:30:00",
  "active_tokens": 8,
  "total_tokens": 10,
  "total_requests": 15234,
  "total_failures": 23,
  "tokens": [
    {
      "masked": "ghp_abc...xyz",
      "remaining": 4523,
      "requests": 477,
      "failures": 2,
      "active": true
    }
  ]
}
```

### 归档记录

无效或耗尽的tokens会归档到`data/archived_tokens/archived_tokens_YYYYMMDD.txt`：

```json
{"token": "ghp_xxx...xxx", "reason": "exhausted", "timestamp": "2024-12-08T10:30:00", "total_requests": 5000, "failed_requests": 0, "last_remaining": 0}
{"token": "ghp_yyy...yyy", "reason": "invalid", "timestamp": "2024-12-08T11:00:00", "total_requests": 10, "failed_requests": 10, "last_remaining": 4990}
```

## 🔄 Token轮换策略

### 自动轮换

系统会自动轮换使用tokens：

1. **正常轮换**：每次请求使用下一个可用token
2. **智能跳过**：跳过被限流或耗尽的tokens
3. **自动恢复**：限流时间过后自动恢复token

### 手动管理

可以通过代码动态管理tokens：

```python
from utils.token_manager import get_token_manager

# 获取token管理器
manager = get_token_manager()

# 添加新token
manager.add_token("ghp_new_token_xxxxx")

# 移除token
manager.remove_token("ghp_old_token_xxxxx", reason="revoked")

# 获取状态摘要
status = manager.get_status_summary()
print(f"Active tokens: {status['active_tokens']}/{status['total_tokens']}")
```

## 🚨 故障排查

### 常见问题

#### 1. 所有tokens都被限流

**症状**：
```
❌ All tokens are exhausted or rate limited
```

**解决方案**：
- 增加更多tokens
- 等待限流重置（通常1小时）
- 检查`TOKEN_MIN_REMAINING_CALLS`设置

#### 2. Token文件未找到

**症状**：
```
⚠️ Token file not found: github_tokens.txt
```

**解决方案**：
- 确认文件路径正确
- 检查文件权限
- 使用绝对路径

#### 3. Token格式无效

**症状**：
```
⚠️ Invalid token format: ghp_xxx...
```

**解决方案**：
- 确认token格式正确（ghp_开头）
- 检查是否有多余的空格或换行
- 验证token未过期

### 调试模式

启用详细日志：

```env
LOG_LEVEL=DEBUG
```

查看token验证：

```python
from utils.token_manager import get_token_manager

manager = get_token_manager()
is_valid = manager.validate_token_with_github("ghp_your_token")
```

## 📈 性能优化

### Token数量建议

| 使用场景 | 建议数量 | 说明 |
|----------|---------|------|
| 开发测试 | 1-3 | 基本够用 |
| 个人项目 | 3-5 | 避免限流 |
| 团队项目 | 5-10 | 稳定运行 |
| 企业部署 | 10-50 | 高并发支持 |
| 大规模扫描 | 50+ | 最大性能 |

### 配置优化

```env
# 高性能配置
TOKEN_AUTO_REMOVE_EXHAUSTED=true
TOKEN_MIN_REMAINING_CALLS=50  # 提前切换
HAJIMI_MAX_WORKERS=20  # 增加并发
```

## 🔐 安全建议

1. **Token保护**
   - 不要将token文件提交到Git
   - 使用环境变量或加密存储
   - 定期轮换tokens

2. **权限控制**
   - 只授予必要的权限（public_repo）
   - 使用细粒度的个人访问令牌
   - 监控异常使用

3. **备份策略**
   - 定期备份归档目录
   - 保留token使用历史
   - 记录失效原因

## 📊 监控指标

### 关键指标

- **Token可用率**：`active_tokens / total_tokens`
- **请求成功率**：`(total_requests - total_failures) / total_requests`
- **平均剩余调用**：`total_remaining_calls / active_tokens`

### 告警阈值

- ⚠️ 活跃tokens < 30%
- ⚠️ 请求失败率 > 10%
- ⚠️ 平均剩余调用 < 100

## 🔄 迁移指南

### 从旧版本迁移

1. **备份现有配置**
```bash
cp .env .env.backup
```

2. **更新配置文件**
```env
# 添加新配置项
USE_EXTERNAL_TOKEN_FILE=false
TOKEN_AUTO_REMOVE_EXHAUSTED=true
```

3. **测试运行**
```bash
python app/api_key_scanner.py
```

### 从其他系统迁移

1. **导出tokens**
   - 从其他系统导出token列表
   - 转换为支持的格式

2. **创建配置文件**
   - 小规模：添加到.env
   - 大规模：创建github_tokens.txt

3. **验证tokens**
```python
# 验证脚本
from utils.token_manager import TokenManager

manager = TokenManager(tokens_file="github_tokens.txt", use_external_file=True)
for token in manager.tokens:
    is_valid = manager.validate_token_with_github(token)
    print(f"Token {manager.tokens[token].masked_token}: {'✓' if is_valid else '✗'}")
```

## 📚 API参考

### TokenManager类

```python
class TokenManager:
    def __init__(self, env_tokens=None, tokens_file=None, use_external_file=False, **kwargs)
    def get_next_token() -> Optional[Tuple[str, TokenStatus]]
    def update_token_status(token: str, headers: Dict, success: bool)
    def add_token(token: str) -> bool
    def remove_token(token: str, reason: str) -> bool
    def get_status_summary() -> Dict[str, Any]
    def validate_token_with_github(token: str) -> bool
```

### TokenStatus数据类

```python
@dataclass
class TokenStatus:
    token: str
    remaining_calls: int
    reset_time: int
    last_used: float
    total_requests: int
    failed_requests: int
    is_active: bool
    masked_token: str
```

## 🎯 最佳实践

1. **准备充足的tokens**
   - 生产环境至少10个
   - 开发环境至少3个

2. **定期监控**
   - 检查归档目录
   - 分析失效原因
   - 及时补充新tokens

3. **合理配置**
   - 根据使用量调整`TOKEN_MIN_REMAINING_CALLS`
   - 启用自动管理功能
   - 设置合适的归档路径

4. **应急预案**
   - 准备备用tokens
   - 设置告警通知
   - 制定恢复流程

---

更多信息请参考：
- [项目主文档](../README.md)
- [部署指南](../DEPLOYMENT_GUIDE.md)
- [环境变量配置](../env.example)