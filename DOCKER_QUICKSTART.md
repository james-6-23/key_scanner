# 🐳 Docker快速部署指南

## 🚀 30秒快速开始

### Windows用户
```bash
# 双击运行
docker-start.bat

# 或命令行
docker-start.bat start
```

### Linux/Mac用户
```bash
# 添加执行权限
chmod +x docker-start.sh

# 运行
./docker-start.sh start
```

## 📦 部署选项

### 选项1：完整部署（推荐）
包含所有功能：WARP代理、Redis缓存、监控面板

```bash
# 使用默认配置
docker-compose up -d

# 查看状态
docker-compose ps
```

### 选项2：最小部署
仅核心功能，适合资源有限的环境

```bash
# 使用最小配置
docker-compose -f docker-compose.minimal.yml up -d
```

### 选项3：开发模式
实时代码更新，适合开发调试

```bash
# 前台运行，查看实时日志
docker-compose up

# 进入容器调试
docker-compose exec scanner /bin/bash
```

## 🎮 使用方法

### 1. 交互式启动器（推荐）
```bash
# 进入菜单界面
docker-compose exec scanner python scanner_launcher.py
```

菜单选项：
- `1` - 快速扫描Gemini
- `2` - 选择API类型扫描
- `3` - 选择扫描器版本
- `7` - 管理查询模板

### 2. 命令行直接扫描

#### 扫描单个API
```bash
# 扫描Gemini（默认）
docker-compose exec scanner python app/api_key_scanner_super.py

# 扫描OpenAI
docker-compose exec scanner python app/api_key_scanner_super.py --api-types openai

# 扫描Anthropic
docker-compose exec scanner python app/api_key_scanner_super.py --api-types anthropic
```

#### 扫描多个API
```bash
# 同时扫描多个API
docker-compose exec scanner python app/api_key_scanner_super.py \
  --api-types gemini,openai,anthropic
```

#### 使用通用扫描器
```bash
# 配置驱动的扫描
docker-compose exec scanner python app/api_scanner_universal.py
```

## 📝 配置说明

### 必需文件
```
key_scanner/
├── .env                    # 环境配置（从env.example复制）
├── queries.txt            # 查询列表
├── github_tokens.txt      # GitHub令牌（可选）
└── config/
    ├── api_patterns.json  # API配置
    └── queries/           # 分API查询模板
        ├── gemini.txt
        ├── openai.txt
        └── ...
```

### 关键环境变量（.env）
```bash
# API类型设置
DEFAULT_API_TYPE=gemini
SCAN_API_TYPES=gemini,openai

# 代理设置（可选）
PROXY=http://warp:1080

# 凭证管理
USE_CREDENTIAL_MANAGER=true
CREDENTIAL_AUTO_HARVEST=false

# 性能优化
HAJIMI_MAX_WORKERS=10
```

## 🔍 查看结果

### 日志文件
```bash
# 实时查看日志
docker-compose logs -f scanner

# 查看最近100行
docker-compose logs --tail=100 scanner
```

### 扫描结果
```bash
# 进入容器查看
docker-compose exec scanner cat data/keys/valid_keys.txt

# 或直接查看本地挂载
cat ./logs/scanner.log
```

### 监控面板
```bash
# 浏览器访问（如果启用）
http://localhost:8080
```

## 🛠️ 常用命令

### 服务管理
```bash
# 启动
docker-compose up -d

# 停止
docker-compose down

# 重启
docker-compose restart

# 查看状态
docker-compose ps
```

### 数据管理
```bash
# 清理所有数据
docker-compose down -v

# 备份数据
docker run --rm -v scanner-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/backup.tar.gz /data

# 查看日志
tail -f ./logs/scanner.log
```

### 更新升级
```bash
# 拉取最新代码
git pull

# 重建镜像
docker-compose build --no-cache

# 重启服务
docker-compose up -d
```

## ❓ 常见问题

### Q: Docker未安装？
**Windows**: 下载 [Docker Desktop](https://docs.docker.com/desktop/install/windows-install/)
**Linux**: 运行 `curl -fsSL https://get.docker.com | sh`
**Mac**: 下载 [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)

### Q: 端口被占用？
编辑 `docker-compose.yml`，修改端口映射：
```yaml
ports:
  - "8081:8080"  # 改为其他端口
```

### Q: 内存不足？
使用最小配置：
```bash
docker-compose -f docker-compose.minimal.yml up -d
```

或调整资源限制：
```yaml
deploy:
  resources:
    limits:
      memory: 512M  # 降低内存限制
```

### Q: 代理连接失败？
1. 检查WARP服务：`docker-compose logs warp`
2. 使用外部代理：编辑`.env`设置 `PROXY=http://your-proxy:port`
3. 禁用代理：设置 `PROXY=`

### Q: 扫描无结果？
1. 检查queries.txt是否有内容
2. 确认API配置正确：`cat config/api_patterns.json`
3. 查看错误日志：`docker-compose logs scanner | grep ERROR`

## 📊 性能优化

### 提高扫描速度
```bash
# .env文件
HAJIMI_MAX_WORKERS=20      # 增加并发数
HAJIMI_BATCH_SIZE=20       # 增加批处理大小
```

### 减少资源占用
```bash
# 使用最小配置
docker-compose -f docker-compose.minimal.yml up -d

# 或调整.env
ENABLE_MONITORING=false
USE_CREDENTIAL_MANAGER=false
```

### 使用本地代理
```bash
# Windows
PROXY=http://host.docker.internal:7890

# Linux
PROXY=http://172.17.0.1:7890
```

## 🔐 安全建议

1. **不要**在生产环境启用 `CREDENTIAL_AUTO_HARVEST`
2. **定期**更新Docker镜像和依赖
3. **使用**强密码保护敏感文件
4. **限制**容器网络访问
5. **加密**存储的API密钥

## 📚 更多文档

- [完整Docker部署指南](docs/DOCKER_DEPLOYMENT_GUIDE.md)
- [多API扫描指南](docs/MULTI_API_SCANNING_GUIDE.md)
- [凭证管理系统](docs/CREDENTIAL_MANAGER_GUIDE.md)
- [项目完成总结](PROJECT_COMPLETION_SUMMARY.md)

## 💬 获取帮助

遇到问题？
1. 查看[故障排除](#常见问题)
2. 运行诊断：`docker-compose exec scanner python -m pytest`
3. 查看日志：`docker-compose logs`
4. 提交Issue：[GitHub Issues](https://github.com/james-6-23/key_scanner/issues)

---

**快速命令参考卡**

| 操作 | 命令 |
|------|------|
| 启动 | `docker-compose up -d` |
| 停止 | `docker-compose down` |
| 查看日志 | `docker-compose logs -f` |
| 进入启动器 | `docker-compose exec scanner python scanner_launcher.py` |
| 快速扫描 | `docker-compose exec scanner python app/api_key_scanner_super.py` |
| 查看结果 | `cat ./logs/scanner.log` |