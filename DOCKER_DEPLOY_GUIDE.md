# 🚀 Docker化API密钥扫描项目部署指南

## 📋 概述

本项目提供了一个简洁高效的Docker化部署方案，集成了WARP代理服务以避免GitHub和Gemini API的IP限制。整个部署只需一个命令即可完成。

### 核心特性
- ⚡ 使用UV包管理器加速Python依赖安装
- 🌐 集成WARP代理服务，自动处理IP限制
- 📦 单一docker-compose.yml实现完整部署
- 🔧 从项目根目录直接读取配置文件
- 🎯 容器间通过内部网络通信，安全高效
- 🔑 智能Token管理系统，支持自动轮换
- 📊 内置健康监控工具，实时追踪Token状态

## 🏗️ 架构设计

```
┌─────────────────────────────────────────┐
│         Docker Network (172.20.0.0/16)   │
│                                          │
│  ┌──────────────┐      ┌──────────────┐ │
│  │ key-scanner  │─────▶│  warp-proxy  │ │
│  │   (主应用)    │ 1080 │  (WARP代理)  │ │
│  └──────────────┘      └──────────────┘ │
│         ▲                      │         │
│         │                      ▼         │
│    挂载文件                GitHub/Gemini  │
│         │                     API        │
└─────────│────────────────────────────────┘
          │
    ┌─────▼─────┐
    │ 本地文件   │
    │ • .env    │
    │ • queries.txt
    └───────────┘
```

## 📦 快速开始

### 1. 准备配置文件

#### 创建 `.env` 文件
```bash
# 复制示例配置文件
cp env.example .env

# 编辑配置文件，添加你的GitHub Token
nano .env
```

**必需的配置项：**
```env
# GitHub API令牌配置（两种模式可选）
# 模式1：小规模Token管理（直接在.env中配置）
GITHUB_TOKENS=ghp_your_token_here_1,ghp_your_token_here_2

# 模式2：大规模Token管理（使用外部文件）
USE_EXTERNAL_TOKEN_FILE=true
GITHUB_TOKEN_FILE=github_tokens.txt

# 代理配置（Docker内部会自动覆盖为warp:1080）
PROXY=http://warp:1080

# Token管理配置（可选）
TOKEN_AUTO_ROTATE=true          # 自动轮换失效Token
TOKEN_HEALTH_CHECK_INTERVAL=300 # 健康检查间隔（秒）
TOKEN_MIN_RATE_LIMIT=100        # 最小剩余调用次数

# 其他配置保持默认即可
```

#### 创建 `queries.txt` 文件
```bash
# 复制示例查询文件
cp queries.example queries.txt

# 根据需要编辑查询条件
nano queries.txt
```

### 2. 启动服务

```bash
# 一键启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 3. 停止服务

```bash
# 停止所有服务
docker-compose down

# 停止并删除数据卷（谨慎使用）
docker-compose down -v
```

## 🔧 配置说明

### 环境变量配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `GITHUB_TOKENS` | GitHub API令牌，逗号分隔 | 必填 |
| `PROXY` | 代理地址（容器内自动设置） | http://warp:1080 |
| `HAJIMI_MAX_WORKERS` | 最大并行验证线程数 | 10 |
| `HAJIMI_BATCH_SIZE` | 批处理大小 | 10 |
| `HAJIMI_BATCH_INTERVAL` | 批处理间隔（秒） | 60 |
| `DATE_RANGE_DAYS` | 仓库年龄过滤（天） | 730 |
| `HAJIMI_CHECK_MODEL` | Gemini验证模型 | gemini-2.0-flash-exp |
| `USE_EXTERNAL_TOKEN_FILE` | 使用外部Token文件 | false |
| `GITHUB_TOKEN_FILE` | 外部Token文件路径 | github_tokens.txt |
| `TOKEN_AUTO_ROTATE` | 自动轮换失效Token | true |
| `TOKEN_HEALTH_CHECK_INTERVAL` | 健康检查间隔 | 300 |
| `TOKEN_MIN_RATE_LIMIT` | 最小剩余调用次数 | 100 |

### 文件挂载说明

| 本地路径 | 容器路径 | 说明 |
|----------|----------|------|
| `./queries.txt` | `/app/queries.txt` | 搜索查询配置 |
| `./.env` | `/app/.env` | 环境变量配置 |
| `./github_tokens.txt` | `/app/github_tokens.txt` | Token列表文件（可选） |
| `./logs` | `/app/data/logs` | 日志文件 |
| `./token_health_reports` | `/app/token_health_reports` | Token健康报告 |
| `scanner-data` | `/app/data` | 数据持久化卷 |

## 🌐 WARP代理说明

### 工作原理
- WARP代理容器提供SOCKS5/HTTP代理服务
- 主应用通过内部网络连接到`warp:1080`
- 所有GitHub和Gemini API请求都通过WARP代理转发
- 自动处理IP限制和速率限制问题

### 验证代理连接
```bash
# 检查WARP代理状态
docker exec key-scanner curl -x http://warp:1080 https://api.github.com

# 查看WARP代理日志
docker-compose logs warp
```

## 🔑 Token管理功能

### Token健康监控

运行独立的健康监控工具：
```bash
# 在容器内运行健康检查
docker exec key-scanner python token_health_monitor.py github_tokens.txt

# 持续监控模式
docker exec key-scanner python token_health_monitor.py github_tokens.txt --continuous

# 查看健康报告
ls -la ./token_health_reports/
```

### Token自动管理

系统支持以下自动管理功能：
- **自动轮换**：失效Token自动移至备用池
- **健康评分**：基于多维度的0-100分评分系统
- **智能调度**：优先使用健康度高的Token
- **实时监控**：持续追踪Token状态和性能

### 查看Token状态
```bash
# 查看当前活跃Token
docker exec key-scanner python -c "from utils.token_manager import TokenManager; tm = TokenManager(); print(tm.get_status())"

# 查看Token健康报告
cat ./token_health_reports/token_health_report_*.json | jq .
```

## 📊 监控和日志

### 查看实时日志
```bash
# 查看所有服务日志
docker-compose logs -f

# 只查看主应用日志
docker-compose logs -f scanner

# 只查看代理日志
docker-compose logs -f warp
```

### 健康检查
```bash
# 查看服务健康状态
docker-compose ps

# 手动健康检查
docker exec key-scanner pgrep -f api_key_scanner
```

### 日志文件位置
- 容器内：`/app/data/logs/`
- 本地映射：`./logs/`

## 🔍 故障排查

### 常见问题

#### 1. 代理连接失败
```bash
# 检查WARP服务状态
docker-compose ps warp

# 重启WARP服务
docker-compose restart warp

# 查看WARP详细日志
docker-compose logs --tail=50 warp
```

#### 2. queries.txt文件未找到
```bash
# 确认文件存在
ls -la queries.txt

# 检查文件权限
chmod 644 queries.txt

# 验证挂载
docker exec key-scanner ls -la /app/queries.txt
```

#### 3. GitHub API限流
```bash
# 检查Token配置
docker exec key-scanner env | grep GITHUB_TOKENS

# 增加更多Token
# 编辑.env文件，添加更多token
```

#### 4. Token耗尽或失效
```bash
# 添加新Token到文件
echo "ghp_new_token_here" >> github_tokens.txt

# 重新加载Token
docker-compose restart scanner

# 运行健康检查
docker exec key-scanner python token_health_monitor.py github_tokens.txt
```

## 🚀 性能优化

### 1. 调整并发数
编辑`docker-compose.yml`中的环境变量：
```yaml
environment:
  - HAJIMI_MAX_WORKERS=20  # 增加并发数
  - HAJIMI_BATCH_SIZE=20   # 增加批处理大小
```

### 2. 资源限制调整
```yaml
deploy:
  resources:
    limits:
      cpus: '4.0'    # 增加CPU限制
      memory: 4G     # 增加内存限制
```

### 3. 使用多个代理
如果有多个代理服务器，可以在`.env`中配置：
```env
PROXY=http://warp:1080,http://proxy2:8080,http://proxy3:3128
```

## 📝 维护建议

### 定期更新
```bash
# 拉取最新镜像
docker-compose pull

# 重新构建并启动
docker-compose up -d --build
```

### 数据备份
```bash
# 备份数据目录
tar -czf backup-$(date +%Y%m%d).tar.gz ./logs ./data

# 备份配置文件
cp .env .env.backup
cp queries.txt queries.txt.backup
```

### 清理旧数据
```bash
# 清理旧日志（保留最近7天）
find ./logs -type f -mtime +7 -delete

# 清理Docker未使用的资源
docker system prune -a
```

## 🔐 安全建议

1. **保护敏感信息**
   - 不要将`.env`文件提交到版本控制
   - 定期轮换GitHub Token
   - 使用强密码保护服务器

2. **网络安全**
   - WARP代理仅在内部网络暴露
   - 不要将代理端口暴露到公网
   - 使用防火墙限制访问

3. **容器安全**
   - 定期更新基础镜像
   - 使用资源限制防止资源耗尽
   - 启用健康检查监控服务状态

## 📚 相关文档

- [项目主README](README.md)
- [Token管理指南](docs/TOKEN_MANAGEMENT_GUIDE.md)
- [Token健康监控指南](TOKEN_HEALTH_MONITOR_GUIDE.md)
- [环境变量详细说明](env.example)
- [查询语法指南](queries.example)
- [并行验证指南](docs/parallel_validation_guide.md)

## 💡 提示和技巧

1. **优化查询效率**
   - 使用精确的查询条件减少无效扫描
   - 按优先级排列queries.txt中的查询
   - 定期清理已处理的查询

2. **监控资源使用**
   ```bash
   # 查看容器资源使用
   docker stats
   
   # 查看磁盘使用
   docker system df
   ```

3. **调试模式**
   ```bash
   # 以交互模式运行查看详细输出
   docker-compose up scanner
   ```

4. **Token健康监控**
   ```bash
   # 定期运行健康检查
   docker exec key-scanner python token_health_monitor.py github_tokens.txt
   
   # 设置定时任务（crontab）
   0 */6 * * * docker exec key-scanner python token_health_monitor.py github_tokens.txt --json
   ```

## 🆘 获取帮助

如遇到问题，请：
1. 查看日志文件了解错误详情
2. 检查配置文件是否正确
3. 确认网络连接正常
4. 提交Issue到项目仓库

---

**注意：** 本部署方案已经过优化，可在VPS服务器上稳定运行。建议使用至少1核2G内存的服务器配置。