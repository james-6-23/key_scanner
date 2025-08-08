# 🔍 API密钥扫描器 - 高效的GitHub密钥发现工具

[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-green)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

[English](README_EN.md) | 简体中文

## 📖 项目简介

API密钥扫描器是一个专门用于在GitHub上发现和验证Google API密钥（特别是Gemini API密钥）的自动化工具。通过智能搜索和并行验证机制，能够高效地发现有效的API密钥。

### ✨ 核心特性

- 🚀 **并行验证** - 多线程并发验证，大幅提升效率
- 🌐 **代理支持** - 集成WARP代理，避免IP限制
- 🐳 **Docker部署** - 一键部署，开箱即用
- ⚡ **UV加速** - 使用UV包管理器，依赖安装速度提升10倍
- 📊 **智能过滤** - 自动过滤文档、示例等无效文件
- 💾 **断点续传** - 支持增量扫描，避免重复工作
- 🔄 **外部同步** - 支持与外部服务同步发现的密钥
- 🔑 **智能Token管理** - 双模式配置，自动生命周期管理

## 🆕 最新更新

### 改进版扫描器
我们推出了改进版扫描器，解决了数据丢失和Token不一致的问题：

- **实时数据保存** - 每找到密钥立即保存到磁盘
- **优雅退出** - Ctrl+C会保存进度后安全退出
- **统一Token管理** - 所有组件使用相同的Token源
- **诊断工具** - 快速检查系统配置问题

```bash
# 运行诊断工具
python diagnose_issues.py

# 使用改进版扫描器
python app/api_key_scanner_improved.py
```

详见 [改进版扫描器指南](IMPROVED_SCANNER_GUIDE.md)

## 🚀 快速开始

### 方式一：统一启动器（最新推荐）
```bash
# Linux/Mac
./unified_launcher.sh

# Windows
unified_launcher.bat
```

启动器提供交互式菜单，可选择：
- Docker容器部署
- 本地环境运行
- 系统诊断
- 配置验证

### 方式二：Docker部署

最简单的部署方式，集成WARP代理，无需担心网络限制：

```bash
# 1. 克隆项目
git clone https://github.com/james-6-23/key_scanner.git
cd key_scanner

# 2. 准备配置文件
cp .env.docker .env
cp queries.example queries.txt

# 3. 编辑配置（添加GitHub Token）
# 编辑 .env 文件，设置 GITHUB_TOKENS=你的token

# 4. 启动服务
docker-compose up -d

# 5. 查看日志
docker-compose logs -f
```

### 方式三：本地部署

如果您已经有可用的代理服务，可以选择本地部署：

```bash
# 1. 克隆项目
git clone https://github.com/james-6-23/key_scanner.git
cd key_scanner

# 2. 安装UV（可选，但推荐）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. 创建虚拟环境并安装依赖
# 使用快速搭建脚本（推荐）
./setup_python_env.sh

# 或手动安装依赖：

# 使用UV（推荐）
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt

# 或使用传统pip
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. 配置环境变量
cp env.example .env
# 编辑 .env 文件：
# - 设置 GITHUB_TOKENS=你的token
# - 设置 PROXY=http://127.0.0.1:1080 (如果有外部代理)

# 5. 准备查询文件
cp queries.example queries.txt

# 6. 运行程序
# 激活虚拟环境（如果未激活）
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 运行主程序
python app/api_key_scanner.py

# 运行Token健康监控工具
python token_health_monitor.py github_tokens.txt
```

### 方式三：使用外部WARP代理

如果需要单独部署WARP代理供本地程序使用：

```bash
# 1. 部署WARP代理
docker run -d \
  --name warp \
  --restart always \
  -p 127.0.0.1:1080:1080 \
  -e WARP_SLEEP=2 \
  --cap-add NET_ADMIN \
  --sysctl net.ipv6.conf.all.disable_ipv6=0 \
  --sysctl net.ipv4.conf.all.src_valid_mark=1 \
  -v ./warp-data:/var/lib/cloudflare-warp \
  caomingjun/warp

# 2. 在.env中配置代理
PROXY=http://127.0.0.1:1080

# 3. 运行本地程序
python app/api_key_scanner.py
```

## 📋 配置说明

### 必需配置

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `GITHUB_TOKENS` | GitHub API令牌，支持多个 | `ghp_token1,ghp_token2` |

### Token配置模式

系统支持两种Token配置模式：

#### 模式1：小规模部署（默认）
```env
# 在.env中配置逗号分隔的tokens
GITHUB_TOKENS=ghp_token1,ghp_token2,ghp_token3
USE_EXTERNAL_TOKEN_FILE=false
```

#### 模式2：大规模部署
```env
# 使用外部文件管理大量tokens
USE_EXTERNAL_TOKEN_FILE=true
GITHUB_TOKENS_FILE=github_tokens.txt
```

创建`github_tokens.txt`：
```
ghp_production_token_1
ghp_production_token_2
ghp_production_token_3
# 支持注释
```

### 可选配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `PROXY` | 代理服务器地址 | 无 |
| `DATE_RANGE_DAYS` | 仓库更新时间过滤（天） | 730 |
| `HAJIMI_MAX_WORKERS` | 并行验证线程数 | 10 |
| `HAJIMI_BATCH_SIZE` | 批处理大小 | 10 |
| `FILE_PATH_BLACKLIST` | 文件路径黑名单 | readme,docs,test等 |
| `TOKEN_AUTO_REMOVE_EXHAUSTED` | 自动移除耗尽的tokens | true |
| `TOKEN_MIN_REMAINING_CALLS` | 最小剩余调用次数 | 10 |

### 查询配置

编辑 `queries.txt` 文件来自定义搜索查询。每行一个GitHub搜索语句：

```
AIzaSy in:file
AIzaSy in:file filename:.env
AIzaSy in:file extension:json
```

## 🏗️ 项目结构

```
key_scanner/
├── app/                    # 应用主程序
│   └── api_key_scanner.py  # 主扫描器
├── utils/                  # 工具模块
│   ├── file_manager.py     # 文件管理
│   ├── github_client.py    # GitHub API客户端
│   └── parallel_validator.py # 并行验证器
├── common/                 # 公共模块
│   ├── config.py          # 配置管理
│   └── Logger.py          # 日志系统
├── docker-compose.yml      # Docker编排文件
├── Dockerfile             # Docker镜像定义
├── queries.txt            # 搜索查询配置
├── .env                   # 环境变量配置
└── data/                  # 数据存储目录
    ├── keys/              # 发现的密钥
    └── logs/              # 运行日志
```

## 🔧 高级功能

### Token健康监控工具

系统包含独立的Token健康监控工具，提供全面的健康检查：

```bash
# 单次健康检查
python token_health_monitor.py github_tokens.txt

# 持续监控模式
python token_health_monitor.py github_tokens.txt --continuous
```

监控指标：
- 🏥 健康评分（0-100分）
- 📊 实时性能指标
- 🚨 智能告警系统
- 📈 历史趋势分析

详细使用请参考 [Token健康监控指南](TOKEN_HEALTH_MONITOR_GUIDE.md)

### 并行验证机制

系统采用多线程并行验证，显著提升验证效率：

- 自动分配验证任务到多个工作线程
- 智能代理轮换，避免单点限流
- 批量验证支持，减少网络开销

### Token生命周期管理

系统自动管理GitHub tokens的完整生命周期：

- **自动监控**：实时监控每个token的API速率限制
- **智能轮换**：自动轮换使用可用的tokens
- **自动归档**：耗尽或无效的tokens自动归档到备份文件
- **自动恢复**：限流时间过后自动恢复token使用
- **状态持久化**：token状态信息持久化保存

详细配置请参考 [Token管理指南](docs/TOKEN_MANAGEMENT_GUIDE.md)

### 增量扫描

支持断点续传和增量扫描：

- 自动记录已扫描的文件SHA
- 跳过已处理的查询
- 基于时间戳的增量更新

### 代理管理

灵活的代理配置：

- 支持HTTP/HTTPS/SOCKS5代理
- 多代理轮换
- 自动重试机制

## 🔧 故障排除

如果遇到以下问题：

### 数据未保存
- 使用改进版扫描器：`python app/api_key_scanner_improved.py`
- 使用Ctrl+C优雅退出，不要强制终止

### Token数量不一致
- 运行诊断工具：`python diagnose_issues.py`
- 检查所有组件使用相同的Token配置

### 详细故障排除
参见 [改进版扫描器指南](IMPROVED_SCANNER_GUIDE.md)

## 📊 运行效果

```
🚀 HAJIMI KING STARTING (Parallel Validation Edition)
⏰ Started at: 2024-12-07 10:00:00
⚡ Parallel validation enabled with 10 workers
✅ System ready - Starting scan

🔍 Processing query: AIzaSy in:file
🔑 Found 5 suspected key(s), starting parallel validation...
✅ VALID: AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
⚡ Parallel validation completed: 5 keys in 2.3s (2.2 keys/s)
💾 Saved 1 valid key(s)

📊 Token Status - Active: 8/10, Remaining calls: 35,420
```

### Token健康仪表板

```
🔑 TOKEN HEALTH MONITOR DASHBOARD 🔑
=====================================
Token         Status      Health  Remaining  Success%
ghp_abc...    ✓ Active    95%     4523       98.5%
ghp_def...    ⚠ Limited   45%     0          95.0%
ghp_ghi...    ✗ Invalid   0%      0          0.0%
```

## 🐛 故障排查

### 常见问题

1. **GitHub API限流**
   - 解决方案：添加更多GitHub Token到配置中

2. **代理连接失败**
   - 检查代理服务状态：`docker ps`
   - 重启代理：`docker restart warp`

3. **找不到queries.txt**
   - 确认文件存在：`ls -la queries.txt`
   - 从示例创建：`cp queries.example queries.txt`

## 📝 更新日志

- **v1.0.0** (2024-12)
  - 初始版本发布
  - 支持Docker一键部署
  - 集成WARP代理
  - 并行验证机制

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

1. Fork本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 🛠️ 工具集

本项目包含以下工具：

| 工具 | 功能 | 使用方法 |
|------|------|----------|
| **主扫描器** | API密钥扫描和验证 | `python app/api_key_scanner.py` |
| **改进版扫描器** 🆕 | 增强数据持久化版本 | `python app/api_key_scanner_improved.py` |
| **诊断工具** 🆕 | 系统配置诊断 | `python diagnose_issues.py` |
| **Token健康监控** | Token健康检查和监控 | `python token_health_monitor.py` |
| **统一启动器** 🆕 | 交互式启动菜单 | `./unified_launcher.sh` 或 `unified_launcher.bat` |
| **快速部署脚本** | Docker一键部署 | `./quick_start.sh` |
| **环境搭建脚本** | Python环境快速搭建 | `./setup_python_env.sh` |

##  许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## ⚠️ 免责声明

本工具仅供安全研究和教育目的使用。使用者应遵守相关法律法规，不得用于非法用途。作者不对使用本工具造成的任何后果负责。

## 🔗 相关链接

### 核心文档
- [改进版扫描器指南](IMPROVED_SCANNER_GUIDE.md) 🆕
- [Token管理指南](docs/TOKEN_MANAGEMENT_GUIDE.md)
- [Token健康监控指南](TOKEN_HEALTH_MONITOR_GUIDE.md)
- [详细部署文档](DOCKER_DEPLOY_GUIDE.md)
- [综合部署方案](DEPLOYMENT_GUIDE.md)

### 配置示例
- [环境变量说明](env.example)
- [Docker环境配置](.env.docker)
- [查询语法示例](queries.example)
- [Token文件示例](github_tokens.example)

### 快速参考
- [Docker快速参考](README_DOCKER.md)
- [英文文档](README_EN.md)

---

**作者**: Key Scanner Team  
**版本**: 1.0.0  
**更新**: 2024-12