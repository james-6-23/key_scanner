# 📚 完整部署指南 - Docker与本地部署方案

## 🎯 部署方案对比

| 特性 | Docker一体化部署 | 本地部署+外部代理 |
|------|-----------------|-------------------|
| **部署难度** | ⭐ 简单 | ⭐⭐⭐ 中等 |
| **代理集成** | ✅ 内置WARP | 需要单独配置 |
| **资源占用** | 较高（容器开销） | 较低 |
| **隔离性** | 完全隔离 | 依赖系统环境 |
| **Token管理** | ✅ 内置智能管理 | ✅ 支持 |
| **健康监控** | ✅ 集成监控工具 | ✅ 支持 |
| **适用场景** | VPS服务器、快速部署 | 开发环境、自定义需求 |

## 🐳 方案一：Docker一体化部署（推荐）

### 架构说明

```
┌─────────────────────────────────────────┐
│      Docker Compose 编排                 │
├─────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐  │
│  │  key-scanner │───▶│  warp-proxy  │  │
│  │   主应用容器  │    │  WARP代理容器 │  │
│  └──────────────┘    └──────────────┘  │
│         ▲                    │          │
│         │                    ▼          │
│    本地配置文件          外部API服务      │
└─────────────────────────────────────────┘
```

### 快速部署步骤

```bash
# 1. 克隆项目
git clone https://github.com/james-6-23/key_scanner.git
cd key_scanner

# 2. 准备配置
cp .env.docker .env
cp queries.example queries.txt

# 3. 编辑配置文件
nano .env
# 小规模Token管理: GITHUB_TOKENS=ghp_token1,ghp_token2
# 大规模Token管理: USE_EXTERNAL_TOKEN_FILE=true
#                  GITHUB_TOKEN_FILE=github_tokens.txt

# 4. 启动服务
docker-compose up -d

# 5. 查看状态
docker-compose ps
docker-compose logs -f
```

### 代理配置选项

#### 选项1：仅内部使用（默认）
```yaml
# docker-compose.yml
services:
  warp:
    expose:
      - "1080"  # 仅容器间通信
```

#### 选项2：暴露到宿主机
```yaml
# docker-compose.yml
services:
  warp:
    ports:
      - "127.0.0.1:1080:1080"  # 宿主机可访问
```

修改后，本地其他程序也可以使用这个代理：
```bash
# 测试代理
curl -x http://127.0.0.1:1080 https://api.github.com
```

## 💻 方案二：本地部署 + 外部代理

### 部署流程

#### 步骤1：部署WARP代理容器

```bash
# 创建WARP代理配置文件
cat > docker-compose-warp.yml << 'EOF'
version: "3"

services:
  warp:
    image: caomingjun/warp
    container_name: warp
    restart: always
    ports:
      - "127.0.0.1:1080:1080"  # 映射到本地1080端口
    environment:
      - WARP_SLEEP=2
    cap_add:
      - NET_ADMIN
    sysctls:
      - net.ipv6.conf.all.disable_ipv6=0
      - net.ipv4.conf.all.src_valid_mark=1
    volumes:
      - ./warp-data:/var/lib/cloudflare-warp
EOF

# 启动WARP代理
docker-compose -f docker-compose-warp.yml up -d

# 验证代理工作
curl -x http://127.0.0.1:1080 https://www.cloudflare.com/cdn-cgi/trace
```

#### 步骤2：本地环境准备

```bash
# 1. 克隆项目
git clone https://github.com/james-6-23/key_scanner.git
cd key_scanner

# 2. 安装UV（推荐）或使用pip
# 使用UV（速度快）：
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt

# 或使用传统pip：
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 步骤3：配置环境

```bash
# 1. 复制配置文件
cp env.example .env
cp queries.example queries.txt

# 2. 编辑.env
nano .env
```

关键配置项：
```env
# GitHub Token配置（两种模式可选）
# 模式1：小规模管理
GITHUB_TOKENS=ghp_your_token_1,ghp_your_token_2

# 模式2：大规模管理
# USE_EXTERNAL_TOKEN_FILE=true
# GITHUB_TOKEN_FILE=github_tokens.txt

# 代理配置（使用步骤1中的WARP代理）
PROXY=http://127.0.0.1:1080

# Token管理配置
TOKEN_AUTO_ROTATE=true          # 自动轮换失效Token
TOKEN_HEALTH_CHECK_INTERVAL=300 # 健康检查间隔（秒）

# 其他配置保持默认即可
```

#### 步骤4：运行程序

```bash
# 运行主程序
python app/api_key_scanner.py

# 运行Token健康监控
python token_health_monitor.py github_tokens.txt

# 持续监控模式
python token_health_monitor.py github_tokens.txt --continuous
```

### Token健康监控工具

独立的健康监控工具提供：
- 🏥 **健康评分**：0-100分的综合评分
- 📊 **实时监控**：持续追踪Token状态
- 🚨 **智能告警**：自动检测异常情况
- 📈 **历史分析**：生成JSON报告和趋势

```bash
# 基础健康检查
python token_health_monitor.py github_tokens.txt

# 生成JSON报告
python token_health_monitor.py github_tokens.txt --json

# 持续监控（每5分钟检查）
python token_health_monitor.py github_tokens.txt --continuous --interval 300
```

## 🔄 两种方案的互通性

### 场景1：Docker部署的代理供本地使用

修改`docker-compose.yml`开启端口映射：
```yaml
services:
  warp:
    ports:
      - "127.0.0.1:1080:1080"  # 添加这行
```

本地程序配置：
```env
PROXY=http://127.0.0.1:1080
```

### 场景2：本地程序使用Docker内的数据

```bash
# 挂载本地目录到容器
volumes:
  - ./local-data:/app/data
```

### 场景3：混合部署

- WARP代理：Docker容器运行
- 主程序：本地Python运行
- 数据存储：共享目录

```bash
# 代理容器
docker run -d -p 127.0.0.1:1080:1080 caomingjun/warp

# 本地程序
PROXY=http://127.0.0.1:1080 python app/api_key_scanner.py
```

## 📊 性能对比

| 指标 | Docker一体化 | 本地+外部代理 |
|------|-------------|--------------|
| 启动速度 | 30秒 | 10秒 |
| 内存占用 | ~500MB | ~200MB |
| CPU占用 | 较高 | 较低 |
| 网络延迟 | 内部通信快 | 略有延迟 |

## 🔧 高级配置

### 多代理配置

```env
# 配置多个代理轮换使用
PROXY=http://127.0.0.1:1080,http://proxy2:8080,socks5://proxy3:1081
```

### 性能优化

```env
# 增加并发数
HAJIMI_MAX_WORKERS=20
HAJIMI_BATCH_SIZE=20

# 调整扫描范围
DATE_RANGE_DAYS=365  # 只扫描一年内的仓库

# Token管理优化
TOKEN_AUTO_ROTATE=true
TOKEN_MIN_RATE_LIMIT=100
TOKEN_ARCHIVE_FAILED=true
```

### Token管理配置

```env
# 大规模Token管理（推荐用于生产环境）
USE_EXTERNAL_TOKEN_FILE=true
GITHUB_TOKEN_FILE=github_tokens.txt
TOKEN_AUTO_ROTATE=true
TOKEN_HEALTH_CHECK_INTERVAL=300
TOKEN_MIN_RATE_LIMIT=100
TOKEN_ARCHIVE_FAILED=true
TOKEN_RETRY_FAILED_AFTER=3600
```

### 调试模式

```bash
# Docker调试
docker-compose logs -f scanner
docker exec -it key-scanner /bin/bash

# 本地调试
LOG_LEVEL=DEBUG python app/api_key_scanner.py
```

## 🚨 常见问题解决

### Q1: 如何确认WARP代理是否正常工作？

```bash
# 测试代理连接
curl -x http://127.0.0.1:1080 https://www.cloudflare.com/cdn-cgi/trace

# 应该看到类似输出：
# warp=on
# gateway=on
```

### Q2: Docker容器内的代理如何被外部访问？

修改`docker-compose.yml`：
```yaml
services:
  warp:
    ports:
      - "0.0.0.0:1080:1080"  # 注意：这会暴露到所有网络接口
```

⚠️ **安全警告**：不建议将代理暴露到公网，建议只绑定到127.0.0.1

### Q3: 如何在Windows上使用？

Windows用户需要注意：
1. 使用PowerShell或Git Bash
2. 路径分隔符使用反斜杠
3. 激活虚拟环境：`.venv\Scripts\activate`

### Q4: 代理连接超时怎么办？

1. 检查Docker容器状态：
```bash
docker ps
docker logs warp
```

2. 重启代理服务：
```bash
docker restart warp
```

3. 检查防火墙设置

### Q5: Token失效怎么办？

系统会自动处理失效Token：
1. **自动轮换**：失效Token移至备用池
2. **健康监控**：实时检测Token状态
3. **手动添加**：
```bash
# 添加新Token到文件
echo "ghp_new_token" >> github_tokens.txt

# 运行健康检查
python token_health_monitor.py github_tokens.txt
```

## 📈 监控和维护

### Token健康监控

```bash
# 查看Token状态仪表板
python token_health_monitor.py github_tokens.txt

# 生成健康报告
python token_health_monitor.py github_tokens.txt --json

# 查看历史报告
ls -la token_health_reports/
cat token_health_reports/token_health_report_*.json | jq .
```

### 日志查看

```bash
# Docker日志
docker-compose logs -f --tail=100

# 本地日志
tail -f data/logs/*.log
```

### 资源监控

```bash
# Docker资源使用
docker stats

# 系统资源
htop
```

### 数据备份

```bash
# 备份发现的密钥
tar -czf backup-$(date +%Y%m%d).tar.gz data/keys/

# 备份配置
cp .env .env.backup
```

### 定期维护任务

```bash
# 每日Token健康检查（crontab）
0 0 * * * cd /path/to/key_scanner && python token_health_monitor.py github_tokens.txt --json

# 每周清理旧日志
0 0 * * 0 find ./logs -type f -mtime +7 -delete

# 每月备份有效密钥
0 0 1 * * tar -czf backup-keys-$(date +%Y%m).tar.gz data/keys/
```

## 🎯 最佳实践

1. **生产环境**：使用Docker一体化部署
2. **开发测试**：使用本地部署便于调试
3. **混合场景**：代理用Docker，程序本地运行
4. **安全建议**：
   - 定期更换GitHub Token
   - 使用Token健康监控工具定期检查
   - 不要将代理暴露到公网
   - 使用强密码保护服务器
5. **Token管理**：
   - 使用外部文件管理大量Token
   - 启用自动轮换和健康检查
   - 定期运行健康监控工具
   - 保持至少10个备用Token

## 📝 总结

- **Docker一体化部署**：适合快速部署、VPS服务器、不想处理环境配置的用户
- **本地部署+外部代理**：适合开发者、需要自定义配置、资源受限的环境

两种方案可以灵活组合使用，根据实际需求选择最合适的部署方式。

---

更多详细信息请参考：
- [Docker部署详细指南](DOCKER_DEPLOY_GUIDE.md)
- [Token管理指南](docs/TOKEN_MANAGEMENT_GUIDE.md)
- [Token健康监控指南](TOKEN_HEALTH_MONITOR_GUIDE.md)
- [项目主页](README.md)
- [环境变量配置](env.example)