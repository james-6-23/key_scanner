# 🐳 Docker部署指南 - 超级版API密钥扫描器

## 📋 目录
- [系统架构](#系统架构)
- [快速开始](#快速开始)
- [详细配置](#详细配置)
- [部署模式](#部署模式)
- [管理命令](#管理命令)
- [故障排除](#故障排除)

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────┐
│            Docker Compose Stack              │
├─────────────────────────────────────────────┤
│                                             │
│  ┌─────────────┐  ┌──────────────────────┐ │
│  │  WARP Proxy │  │   Scanner Super      │ │
│  │   (SOCKS5)  │◄─┤  (主应用+启动器)      │ │
│  └─────────────┘  └──────────────────────┘ │
│         ▲                    │              │
│         │                    ▼              │
│  ┌─────────────┐  ┌──────────────────────┐ │
│  │    Redis    │◄─┤  Monitor Dashboard   │ │
│  │   (缓存)    │  │    (监控面板)        │ │
│  └─────────────┘  └──────────────────────┘ │
│                                             │
└─────────────────────────────────────────────┘
```

## 🚀 快速开始

### 1. 基础准备

```bash
# 克隆项目
git clone https://github.com/james-6-23/key_scanner.git
cd key_scanner

# 复制环境配置
cp env.example .env

# 编辑配置文件
nano .env
```

### 2. 一键部署

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f scanner
```

### 3. 使用启动器

```bash
# 进入交互式启动器
docker-compose exec scanner python scanner_launcher.py

# 或直接运行特定扫描
docker-compose exec scanner python app/api_key_scanner_super.py --api-types gemini,openai
```

## ⚙️ 详细配置

### 环境变量配置 (.env)

```bash
# ========== 基础配置 ==========
# 默认API类型
DEFAULT_API_TYPE=gemini

# 要扫描的API类型（逗号分隔）
SCAN_API_TYPES=gemini,openai,anthropic

# ========== 代理配置 ==========
# 使用内部WARP代理
PROXY=http://warp:1080

# 或使用外部代理
# PROXY=http://your-proxy:port

# ========== 凭证管理 ==========
# 启用凭证管理系统
USE_CREDENTIAL_MANAGER=true

# 自动收集Token（风险功能）
CREDENTIAL_AUTO_HARVEST=false

# 存储类型：redis, file, memory
CREDENTIAL_STORAGE_TYPE=redis

# ========== 负载均衡 ==========
# 策略：adaptive, weighted_round_robin, quota_aware等
LOAD_BALANCE_STRATEGY=adaptive

# ========== 监控配置 ==========
# 启用监控
ENABLE_MONITORING=true

# 监控间隔（秒）
MONITORING_INTERVAL=300

# ========== 性能优化 ==========
HAJIMI_MAX_WORKERS=10
HAJIMI_BATCH_SIZE=10
HAJIMI_BATCH_INTERVAL=60
```

### Docker Compose配置

```yaml
# docker-compose.yml 关键配置

services:
  scanner:
    # 资源限制
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
    
    # 数据卷挂载
    volumes:
      # 查询文件
      - ./queries.txt:/app/queries.txt:ro
      - ./config/queries:/app/config/queries:ro
      
      # API配置
      - ./config/api_patterns.json:/app/config/api_patterns.json:ro
      
      # 数据持久化
      - scanner-data:/app/data
      - credential-data:/app/credential_manager/storage
      
      # 日志
      - ./logs:/app/data/logs:rw
```

## 🎯 部署模式

### 模式1：完整部署（推荐）

包含所有组件：WARP代理、Redis缓存、扫描器、监控面板

```bash
docker-compose up -d
```

### 模式2：最小部署

仅运行扫描器，使用文件存储

```bash
# 修改.env
CREDENTIAL_STORAGE_TYPE=file
USE_CREDENTIAL_MANAGER=false

# 只启动扫描器
docker-compose up -d scanner
```

### 模式3：开发模式

挂载本地代码，实时更新

```bash
# 修改docker-compose.yml，添加代码挂载
volumes:
  - ./app:/app/app:ro
  - ./credential_manager:/app/credential_manager:ro
  - ./config:/app/config:ro

# 启动
docker-compose up
```

### 模式4：生产部署

使用Docker Swarm或Kubernetes

```bash
# Docker Swarm
docker stack deploy -c docker-compose.yml scanner-stack

# Kubernetes (需要先转换配置)
kompose convert
kubectl apply -f .
```

## 📝 管理命令

### 服务管理

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 重启特定服务
docker-compose restart scanner

# 查看服务状态
docker-compose ps

# 查看服务日志
docker-compose logs -f scanner
docker-compose logs --tail=100 scanner
```

### 扫描操作

```bash
# 使用启动器（交互式）
docker-compose exec scanner python scanner_launcher.py

# 快速扫描Gemini
docker-compose exec scanner python app/api_key_scanner_super.py

# 扫描多个API
docker-compose exec scanner python app/api_key_scanner_super.py \
  --api-types gemini,openai,anthropic

# 使用通用扫描器
docker-compose exec scanner python app/api_scanner_universal.py

# 查看扫描结果
docker-compose exec scanner cat data/keys/valid_keys.txt
```

### 凭证管理

```bash
# 查看凭证状态
docker-compose exec scanner python -c "
from credential_manager import CredentialManager
cm = CredentialManager()
print(cm.get_status())
"

# 手动添加凭证
docker-compose exec scanner python -c "
from credential_manager import CredentialManager
cm = CredentialManager()
cm.add_credential('gemini', 'YOUR_API_KEY')
"

# 导出凭证
docker-compose exec scanner python credential_manager/tools/export.py
```

### 监控操作

```bash
# 访问监控面板
# 浏览器打开: http://localhost:8080

# 查看监控日志
docker-compose logs -f monitor

# 查看Redis状态
docker-compose exec redis redis-cli INFO

# 查看缓存内容
docker-compose exec redis redis-cli KEYS "*"
```

### 数据管理

```bash
# 备份数据
docker run --rm -v scanner-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/scanner-backup-$(date +%Y%m%d).tar.gz /data

# 恢复数据
docker run --rm -v scanner-data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/scanner-backup-20240101.tar.gz -C /

# 清理日志
docker-compose exec scanner find /app/data/logs -name "*.log" -mtime +7 -delete

# 清理缓存
docker-compose exec redis redis-cli FLUSHALL
```

## 🔧 故障排除

### 常见问题

#### 1. 容器无法启动

```bash
# 检查日志
docker-compose logs scanner

# 检查配置文件
docker-compose config

# 验证镜像
docker-compose build --no-cache scanner
```

#### 2. 网络连接问题

```bash
# 测试WARP代理
docker-compose exec scanner curl -x socks5://warp:1080 https://api.ipify.org

# 检查网络
docker network ls
docker network inspect key_scanner_scanner-network
```

#### 3. 权限问题

```bash
# 修复文件权限
sudo chown -R $USER:$USER .
chmod 644 .env
chmod 644 queries.txt
chmod 755 logs/
```

#### 4. 内存不足

```bash
# 调整资源限制
# 编辑docker-compose.yml
deploy:
  resources:
    limits:
      memory: 1G  # 降低内存限制
```

#### 5. Redis连接失败

```bash
# 检查Redis状态
docker-compose ps redis
docker-compose logs redis

# 手动测试连接
docker-compose exec scanner python -c "
import redis
r = redis.from_url('redis://redis:6379/0')
print(r.ping())
"
```

### 调试模式

```bash
# 启用调试日志
export DEBUG=true
docker-compose up

# 进入容器调试
docker-compose exec scanner /bin/bash

# 在容器内运行Python交互式环境
docker-compose exec scanner python
```

### 性能优化

```bash
# 1. 调整并发数
HAJIMI_MAX_WORKERS=20

# 2. 增加批处理大小
HAJIMI_BATCH_SIZE=20

# 3. 使用本地代理
PROXY=http://host.docker.internal:7890

# 4. 禁用不需要的功能
ENABLE_MONITORING=false
CREDENTIAL_AUTO_HARVEST=false
```

## 📊 监控和日志

### 日志位置

```
./logs/
├── scanner.log          # 主扫描器日志
├── credential.log       # 凭证管理日志
├── monitor.log         # 监控日志
└── error.log          # 错误日志
```

### 监控指标

- **API调用统计**：成功/失败次数
- **凭证健康度**：可用/失效凭证数
- **性能指标**：响应时间、吞吐量
- **资源使用**：CPU、内存、网络

### 告警配置

```yaml
# docker-compose.yml 添加告警
services:
  scanner:
    healthcheck:
      test: ["CMD", "python", "health_check.py"]
      interval: 30s
      retries: 3
    labels:
      - "prometheus.io/scrape=true"
      - "prometheus.io/port=9090"
```

## 🔐 安全建议

1. **不要在生产环境启用** `CREDENTIAL_AUTO_HARVEST`
2. **定期更新**镜像和依赖
3. **使用密钥管理**服务（如HashiCorp Vault）
4. **限制网络访问**，使用防火墙规则
5. **加密敏感数据**，使用Docker Secrets
6. **定期备份**数据和配置
7. **监控异常行为**，设置告警

## 📚 相关文档

- [多API扫描指南](./MULTI_API_SCANNING_GUIDE.md)
- [凭证管理系统](./CREDENTIAL_MANAGER_GUIDE.md)
- [API配置说明](../config/queries/README.md)
- [项目完成总结](../PROJECT_COMPLETION_SUMMARY.md)

## 💡 提示

- 使用 `docker-compose exec` 而不是 `docker exec` 以保持环境变量
- 定期清理未使用的镜像：`docker image prune -a`
- 使用 `--scale` 参数运行多个扫描器实例
- 配置日志轮转避免磁盘空间耗尽
- 使用健康检查确保服务可用性

---

**需要帮助？** 查看[故障排除](#故障排除)或提交Issue。