# 改进版扫描器使用指南

## 📋 目录
- [问题诊断](#问题诊断)
- [改进版扫描器](#改进版扫描器)
- [快速开始](#快速开始)
- [常见问题解决](#常见问题解决)
- [最佳实践](#最佳实践)

## 问题诊断

### 运行诊断工具
首先运行诊断工具来检查系统配置：

```bash
python diagnose_issues.py
```

这个工具会检查：
- ✅ Token配置一致性
- ✅ 数据文件状态
- ✅ 查询文件配置
- ✅ Token管理器状态

## 改进版扫描器

### 主要改进
1. **实时数据保存** - 每找到有效密钥立即保存到磁盘
2. **优雅退出** - Ctrl+C 会保存当前进度后退出
3. **Token一致性** - 统一的Token读取逻辑
4. **增强的错误恢复** - 自动保存进度，可从中断处继续

### 文件说明

| 文件 | 说明 |
|------|------|
| `app/api_key_scanner_improved.py` | 改进版扫描器（推荐使用） |
| `app/api_key_scanner.py` | 原版扫描器 |
| `diagnose_issues.py` | 诊断工具 |
| `unified_launcher.sh` | Linux/Mac统一启动器 |
| `unified_launcher.bat` | Windows统一启动器 |

## 快速开始

### 1. 配置Token

#### 方式一：使用外部文件（推荐用于大量Token）
创建 `github_tokens.txt` 文件：
```txt
ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
github_pat_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# 可以添加注释
ghp_yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy
```

在 `.env` 文件中设置：
```env
USE_EXTERNAL_TOKEN_FILE=true
GITHUB_TOKENS_FILE=github_tokens.txt
```

#### 方式二：使用环境变量（适合少量Token）
在 `.env` 文件中设置：
```env
USE_EXTERNAL_TOKEN_FILE=false
GITHUB_TOKENS=ghp_xxx,ghp_yyy,ghp_zzz
```

### 2. 配置查询
复制示例文件：
```bash
cp queries.example queries.txt
```

编辑 `queries.txt` 添加你的搜索查询。

### 3. 运行改进版扫描器

#### 使用统一启动器（推荐）
Linux/Mac:
```bash
./unified_launcher.sh
# 选择 2 - Run in local environment
# 选择 2 - Run improved scanner
```

Windows:
```batch
unified_launcher.bat
REM 选择 2 - Run in local environment
REM 选择 2 - Run improved scanner
```

#### 直接运行
```bash
python app/api_key_scanner_improved.py
```

### 4. 监控进度
扫描器会显示：
- 实时进度更新
- 找到的有效密钥数量
- Token使用状态
- 文件保存位置

输出文件位置：
```
data/
├── keys_valid_20241208.txt        # 有效密钥列表
├── keys_valid_detail_20241208.log # 详细信息
├── rate_limited_20241208.txt      # 被限流的密钥
├── checkpoint.json                 # 进度检查点
└── scanned_shas.txt               # 已扫描文件
```

## 常见问题解决

### 问题1：扫描中断数据丢失
**症状**：找到23个密钥但文件为空

**原因**：强制终止程序导致缓冲区未写入

**解决方案**：
1. 使用改进版扫描器 `api_key_scanner_improved.py`
2. 使用 Ctrl+C 优雅退出而不是强制关闭
3. 改进版会实时保存每个找到的密钥

### 问题2：Token数量不一致
**症状**：健康监控显示6个Token，扫描器显示4个

**原因**：不同工具读取不同的Token源

**解决方案**：
1. 运行诊断工具检查配置：
   ```bash
   python diagnose_issues.py
   ```
2. 确保所有工具使用相同的Token配置模式
3. 检查 `.env` 中的 `USE_EXTERNAL_TOKEN_FILE` 设置

### 问题3：没有生成数据文件
**症状**：程序运行但没有输出文件

**可能原因**：
1. 没有找到有效密钥
2. 文件权限问题
3. 查询配置错误

**解决方案**：
1. 检查 `queries.txt` 是否存在且有有效查询
2. 确保 `data/` 目录有写入权限
3. 查看程序输出日志了解详情

### 问题4：Token快速耗尽
**症状**：Token剩余调用次数快速降至0

**解决方案**：
1. 使用多个Token轮换
2. 配置代理减少限流
3. 调整扫描间隔

## 最佳实践

### 1. Token管理
- 准备5-10个GitHub Token以确保稳定运行
- 定期使用健康监控工具检查Token状态：
  ```bash
  python token_health_monitor.py
  ```

### 2. 数据备份
- 定期备份 `data/` 目录
- 使用增量扫描模式避免重复工作

### 3. 性能优化
- 使用并行验证提高效率
- 配置代理避免IP限制
- 合理设置扫描间隔

### 4. 监控和维护
```bash
# 检查系统状态
python diagnose_issues.py

# 监控Token健康
python token_health_monitor.py

# 查看找到的密钥
cat data/keys_valid_*.txt | sort | uniq | wc -l
```

## 高级配置

### 环境变量说明
```env
# Token配置
USE_EXTERNAL_TOKEN_FILE=true       # 使用外部文件模式
GITHUB_TOKENS_FILE=github_tokens.txt # Token文件路径
GITHUB_TOKENS=token1,token2        # 直接配置Token（逗号分隔）

# 扫描配置
DATE_RANGE_DAYS=30                 # 扫描最近N天的仓库
MAX_WORKERS=10                      # 并行验证线程数

# 代理配置（可选）
PROXY_LIST=http://proxy1:8080,http://proxy2:8080
```

### 数据文件结构
```
data/
├── checkpoint.json                 # 扫描进度
│   └── 包含：last_scan_time, processed_queries
├── scanned_shas.txt               # 已扫描文件SHA列表
├── keys_valid_YYYYMMDD.txt        # 有效密钥（纯文本）
├── keys_valid_detail_YYYYMMDD.log # 有效密钥详情
├── rate_limited_YYYYMMDD.txt      # 被限流密钥
└── archived_tokens/                # 归档的失效Token
```

## 故障排除命令

```bash
# 1. 快速测试Token配置
python -c "from utils.github_client import GitHubClient; gc = GitHubClient.create_instance(True); print(gc.get_token_status())"

# 2. 检查数据文件
ls -la data/*.txt data/*.log

# 3. 查看最新的有效密钥
tail -n 20 data/keys_valid_*.txt

# 4. 统计扫描进度
python -c "import json; c = json.load(open('data/checkpoint.json')); print(f'Processed queries: {len(c.get(\"processed_queries\", []))}')"

# 5. 清理并重新开始（谨慎使用）
rm data/checkpoint.json data/scanned_shas.txt
```

## 联系支持

如果遇到其他问题：
1. 运行诊断工具并保存输出
2. 检查 `data/` 目录中的日志文件
3. 提供错误信息和系统配置信息

---

**提示**：始终使用改进版扫描器 `app/api_key_scanner_improved.py` 以获得最佳体验和数据安全性。