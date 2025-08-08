# 🐳 Docker化API密钥扫描器 - 快速部署版

一个集成WARP代理的Docker化API密钥扫描解决方案，专为VPS服务器优化，避免GitHub和Gemini API的IP限制。

## ✨ 核心优势

- **🚀 一键部署** - 单个命令即可启动完整服务
- **⚡ UV加速** - 使用UV包管理器，依赖安装速度提升10倍
- **🌐 内置代理** - 集成WARP代理，自动处理IP限制
- **📦 简化配置** - 单一docker-compose.yml文件
- **🔧 灵活挂载** - 配置文件从根目录读取，方便修改
- **🔑 智能Token管理** - 自动轮换、健康检查、生命周期管理
- **📊 健康监控** - 内置Token健康监控工具

## 🎯 快速开始

### 方式一：自动部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/james-6-23/key_scanner.git
cd key_scanner

# 2. 准备配置文件
cp .env.docker .env
nano .env  # 添加你的GitHub Token

# 3. 运行快速启动脚本
chmod +x quick_start.sh
./quick_start.sh
```

### 方式二：手动部署

```bash
# 1. 准备配置文件
cp .env.docker .env
cp queries.example queries.txt

# 2. 编辑.env，添加GitHub Token
nano .env

# 3. 启动服务
docker-compose up -d

# 4. 查看日志
docker-compose logs -f
```

## 📋 配置要求

### 最低配置
- **系统**: Linux (Ubuntu/Debian/CentOS)
- **CPU**: 1核
- **内存**: 2GB
- **磁盘**: 10GB
- **软件**: Docker 20.10+, Docker Compose 1.29+

### 必需的配置项
```env
# Token配置（两种模式可选）
# 模式1：小规模管理（直接在.env中）
GITHUB_TOKENS=ghp_your_token_here_1,ghp_your_token_here_2

# 模式2：大规模管理（使用外部文件）
USE_EXTERNAL_TOKEN_FILE=true
GITHUB_TOKEN_FILE=github_tokens.txt

# Token管理配置（可选）
TOKEN_AUTO_ROTATE=true          # 自动轮换失效Token
TOKEN_HEALTH_CHECK_INTERVAL=300 # 健康检查间隔（秒）
```

## 🏗️ 项目结构

```
key_scanner/
├── docker-compose.yml    # Docker编排文件
├── Dockerfile           # 主应用镜像定义
├── .env.docker         # 环境变量模板
├── queries.txt         # 搜索查询配置
├── github_tokens.txt   # Token列表文件（可选）
├── quick_start.sh      # 快速启动脚本
├── token_health_monitor.py  # Token健康监控工具
└── app/               # 应用源代码
    └── api_key_scanner.py
```

## 🔧 服务架构

```yaml
services:
  warp:       # WARP代理服务 (caomingjun/warp)
    ├── 端口: 1080 (仅内部网络)
    └── 功能: 提供代理服务，避免IP限制
    
  scanner:    # 主应用服务
    ├── 依赖: warp代理
    ├── 挂载: queries.txt, .env, logs
    └── 功能: 扫描和验证API密钥
```

## 📊 常用命令

```bash
# 服务管理
docker-compose up -d        # 启动服务
docker-compose down         # 停止服务
docker-compose restart      # 重启服务
docker-compose ps          # 查看状态

# 日志查看
docker-compose logs -f              # 实时日志
docker-compose logs -f scanner      # 主应用日志
docker-compose logs -f warp        # 代理日志

# 调试命令
docker exec key-scanner env        # 查看环境变量
docker exec key-scanner ls -la /app # 查看文件
docker stats                       # 资源使用情况

# Token管理
docker exec key-scanner python token_health_monitor.py github_tokens.txt  # 健康检查
docker exec key-scanner python -c "from utils.token_manager import TokenManager; tm = TokenManager(); print(tm.get_status())"  # 查看状态
```

## 🔑 Token健康监控

```bash
# 运行健康检查
docker exec key-scanner python token_health_monitor.py github_tokens.txt

# 持续监控模式
docker exec key-scanner python token_health_monitor.py github_tokens.txt --continuous

# 生成JSON报告
docker exec key-scanner python token_health_monitor.py github_tokens.txt --json

# 查看健康报告
ls -la ./token_health_reports/
```

### 健康监控指标
- 🏥 **健康评分**: 0-100分综合评分
- 📊 **剩余调用**: API调用次数限制
- ✅ **成功率**: 历史请求成功率
- ⚡ **响应时间**: 平均响应速度
- 🚨 **错误频率**: 错误发生频率

## 🔍 验证部署

```bash
# 1. 检查服务状态
docker-compose ps

# 2. 验证代理连接
docker exec key-scanner curl -x http://warp:1080 https://api.github.com

# 3. 查看扫描日志
docker-compose logs --tail=50 scanner
```

## ⚙️ 性能优化

### 调整并发数
编辑`docker-compose.yml`:
```yaml
environment:
  - HAJIMI_MAX_WORKERS=20  # 增加并发
  - HAJIMI_BATCH_SIZE=20   # 增加批量
```

### 增加资源限制
```yaml
deploy:
  resources:
    limits:
      cpus: '4.0'
      memory: 4G
```

## 🐛 故障排查

| 问题 | 解决方案 |
|------|---------|
| 代理连接失败 | `docker-compose restart warp` |
| queries.txt未找到 | 确认文件存在: `ls -la queries.txt` |
| GitHub限流 | 添加更多Token到.env文件 |
| Token失效 | 运行健康检查: `docker exec key-scanner python token_health_monitor.py` |
| 内存不足 | 调整docker-compose.yml中的内存限制 |

## 📝 文件说明

| 文件 | 说明 |
|------|------|
| `docker-compose.yml` | Docker服务编排配置 |
| `Dockerfile` | 主应用镜像构建文件 |
| `.env.docker` | 环境变量配置模板 |
| `queries.txt` | GitHub搜索查询列表 |
| `github_tokens.txt` | Token列表文件（大规模管理） |
| `token_health_monitor.py` | Token健康监控工具 |
| `quick_start.sh` | 自动化部署脚本 |
| `DOCKER_DEPLOY_GUIDE.md` | 详细部署文档 |

## 🔄 更新升级

```bash
# 拉取最新代码
git pull

# 重建镜像
docker-compose build --no-cache

# 重启服务
docker-compose up -d
```

## 📊 监控建议

1. **日志监控**: 定期检查`./logs`目录
2. **资源监控**: 使用`docker stats`监控资源
3. **Token监控**: 定期运行`token_health_monitor.py`
4. **健康检查**: 服务自带健康检查机制
5. **数据备份**: 定期备份`./data`和`./token_health_reports`目录

## 🔐 安全提醒

- ⚠️ 不要将`.env`文件提交到Git
- 🔑 定期更换GitHub Token，使用健康监控工具检查
- 🚫 不要将代理端口暴露到公网
- 📁 设置适当的文件权限
- 🔐 使用外部文件管理大量Token时注意文件权限

## 📚 相关文档

- [详细部署指南](DOCKER_DEPLOY_GUIDE.md)
- [Token管理指南](docs/TOKEN_MANAGEMENT_GUIDE.md)
- [Token健康监控指南](TOKEN_HEALTH_MONITOR_GUIDE.md)
- [项目主文档](README.md)
- [环境变量说明](env.example)
- [查询语法示例](queries.example)

## 💡 快速提示

```bash
# 一键查看所有关键信息
docker-compose ps && docker-compose logs --tail=10

# 快速Token健康检查
docker exec key-scanner python token_health_monitor.py github_tokens.txt --json
```

## 🆘 需要帮助？

1. 查看[详细部署文档](DOCKER_DEPLOY_GUIDE.md)
2. 检查日志: `docker-compose logs -f`
3. 提交Issue到项目仓库

---

**版本**: 1.0.0 | **更新日期**: 2024-12 | **作者**: Key Scanner Team