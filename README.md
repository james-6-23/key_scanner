# 🔍 API密钥扫描器 - 企业级多API密钥发现工具

[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-green)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

## 📖 项目简介

API密钥扫描器是一个专业的自动化工具，用于在GitHub上发现和验证多种API密钥。支持Gemini、OpenAI、Anthropic等7种主流API，具备企业级凭证管理和智能负载均衡能力。

### ✨ 核心特性

- 🎯 **多API支持** - 支持7种主流API（Gemini、OpenAI、Anthropic、AWS、Azure、Cohere、HuggingFace）
- 🚀 **并行验证** - 多线程并发验证，大幅提升效率
- 🔑 **企业级凭证管理** - 8种负载均衡策略，自愈机制，加密存储
- 🐳 **Docker一键部署** - 完整的容器化解决方案
- 📊 **实时监控** - WebSocket监控仪表板，健康度评分
- 🔄 **智能Token管理** - 自动生命周期管理，智能轮换
- 🌐 **代理支持** - 集成WARP代理，避免IP限制

## 🚀 快速开始

### 方式一：Docker部署（推荐）

```bash
# Windows用户
docker-start.bat

# Linux/Mac用户
chmod +x docker-start.sh
./docker-start.sh
```

### 方式二：交互式启动器

```bash
python scanner_launcher.py
```

启动器提供：
- 🎮 交互式菜单
- 🔍 多API类型选择
- 📝 查询模板管理
- 🛠️ 环境自动检查

### 方式三：直接运行

```bash
# 扫描Gemini（默认）
python app/api_key_scanner_super.py

# 扫描多个API
python app/api_key_scanner_super.py --api-types gemini,openai,anthropic

# 使用通用扫描器
python app/api_scanner_universal.py
```

## 📋 配置说明

### 基础配置（.env）

```env
# GitHub Token（必需）
GITHUB_TOKENS=ghp_token1,ghp_token2

# API类型设置
DEFAULT_API_TYPE=gemini
SCAN_API_TYPES=gemini,openai,anthropic

# 代理设置（可选）
PROXY=http://warp:1080

# 凭证管理
USE_CREDENTIAL_MANAGER=true
CREDENTIAL_AUTO_HARVEST=false  # 高级功能，默认关闭
```

### 查询模板

每个API都有独立的查询模板文件：

```
config/queries/
├── gemini.txt      # Gemini API查询
├── openai.txt      # OpenAI API查询
├── anthropic.txt   # Anthropic API查询
└── ...
```

## 🏗️ 项目结构

```
key_scanner/
├── app/                        # 应用主程序
│   ├── api_key_scanner_super.py    # 超级版扫描器（推荐）
│   ├── api_scanner_universal.py    # 通用API扫描器
│   └── api_key_scanner.py         # 基础版扫描器
├── credential_manager/         # 凭证管理系统
│   ├── core/                  # 核心模块
│   ├── balancer/              # 负载均衡
│   ├── discovery/             # Token发现
│   └── monitoring/            # 监控系统
├── config/                    # 配置文件
│   ├── api_patterns.json      # API配置定义
│   └── queries/               # 查询模板
├── docker-compose.yml         # Docker编排
├── scanner_launcher.py        # 交互式启动器
└── docs/                      # 文档
```

## 🔧 高级功能

### 三个扫描器版本对比

| 版本 | 适用场景 | 主要特性 |
|------|----------|----------|
| **超级版** 🆕 | 企业级部署 | 凭证管理、自愈机制、监控仪表板、多API支持 |
| **通用版** | 多API扫描 | 配置驱动、灵活扩展、支持自定义API |
| **基础版** | 快速测试 | 简单高效、适合单一API扫描 |

### 凭证管理系统

- **8种负载均衡策略**：quota_aware、adaptive、weighted_round_robin等
- **自愈机制**：自动检测和恢复失效凭证
- **加密存储**：Fernet对称加密保护敏感数据
- **生命周期管理**：完整的凭证生命周期自动化

### Token自动收集（高级特性）

⚠️ **此功能默认关闭，需要显式启用**

```env
# 在.env中启用
CREDENTIAL_AUTO_HARVEST=true
CREDENTIAL_HARVEST_RISK_THRESHOLD=2
```

功能包括：
- 智能发现潜在tokens
- 多层风险评估
- 蜜罐检测
- 沙箱验证

## 🐳 Docker部署

### 完整部署

包含所有组件：WARP代理、Redis缓存、监控面板

```bash
docker-compose up -d
```

### 最小部署

仅核心功能，适合资源受限环境

```bash
docker-compose -f docker-compose.minimal.yml up -d
```

### 管理命令

```bash
# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f scanner

# 进入启动器
docker-compose exec scanner python scanner_launcher.py

# 停止服务
docker-compose down
```

## 📊 监控和日志

### 监控面板

访问 http://localhost:8080 查看：
- API调用统计
- 凭证健康度
- 性能指标
- 实时日志

### 日志文件

```
logs/
├── scanner.log       # 主扫描器日志
├── credential.log    # 凭证管理日志
└── error.log        # 错误日志
```

## 🔧 故障排除

### 常见问题

1. **Docker未安装**
   - Windows: [Docker Desktop](https://docs.docker.com/desktop/install/windows-install/)
   - Linux: `curl -fsSL https://get.docker.com | sh`

2. **端口被占用**
   - 修改docker-compose.yml中的端口映射

3. **内存不足**
   - 使用最小配置：`docker-compose -f docker-compose.minimal.yml up -d`

4. **Token配置问题**
   - 检查.env文件中的GITHUB_TOKENS配置
   - 确保Token有足够的API调用配额

## 📚 文档

- [Docker部署指南](docs/DOCKER_DEPLOYMENT_GUIDE.md)
- [Docker快速开始](DOCKER_QUICKSTART.md)
- [多API扫描指南](docs/MULTI_API_SCANNING_GUIDE.md)
- [项目完成总结](PROJECT_COMPLETION_SUMMARY.md)

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📝 许可证

MIT License - 查看 [LICENSE](LICENSE) 文件

## ⚠️ 免责声明

本工具仅供安全研究和教育目的使用。使用者应遵守相关法律法规，不得用于非法用途。

---

**版本**: 2.0.0  
**更新**: 2024-12