# 🔐 高级凭证管理系统 (Advanced Credential Manager)

一个企业级的API凭证生命周期管理解决方案，为您的API密钥扫描项目提供智能、安全、高效的凭证管理能力。

## ✨ 核心特性

- 🎯 **智能负载均衡** - 8种负载均衡策略，包括配额感知、自适应等高级策略
- 🔍 **自动发现** - 自动扫描文件系统、环境变量、代码中的凭证
- 🏥 **自愈机制** - 自动检测和修复凭证问题，确保高可用性
- 🔒 **加密存储** - 使用Fernet对称加密保护敏感凭证
- 📊 **实时监控** - 提供仪表板和健康报告
- 🔄 **向后兼容** - 无缝集成现有TokenManager系统

## 🚀 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行演示

```bash
# 运行完整演示
python start_credential_manager.py --mode demo

# 运行交互式监控仪表板
python start_credential_manager.py --mode dashboard

# 运行测试套件
python start_credential_manager.py --mode test

# 清理演示数据
python start_credential_manager.py --clean
```

### 基本使用示例

```python
from credential_manager.integration.credential_bridge import CredentialBridge

# 创建桥接器（自动发现和导入凭证）
bridge = CredentialBridge(auto_discover=True, enable_healing=True)

# 获取GitHub凭证
cred = bridge.get_credential(service_type='github')
if cred:
    token = cred['value']
    # 使用token进行API调用...
```

## 📁 项目结构

```
key_scanner/
├── credential_manager/          # 凭证管理系统核心
│   ├── core/                   # 核心功能模块
│   │   ├── models.py           # 数据模型定义
│   │   └── manager.py          # 凭证管理器
│   ├── storage/                # 存储层
│   │   └── vault.py            # 加密存储实现
│   ├── balancer/               # 负载均衡
│   │   └── strategies.py       # 均衡策略实现
│   ├── healing/                # 自愈机制
│   │   └── health_check.py     # 健康检查和自愈
│   ├── discovery/              # 凭证发现
│   │   └── discovery.py        # 发现引擎
│   ├── integration/            # 系统集成
│   │   └── credential_bridge.py # 桥接器和适配器
│   └── monitoring/             # 监控
│       └── dashboard.py        # 监控仪表板
├── test_credential_manager.py  # 测试套件
├── start_credential_manager.py # 启动脚本
├── requirements.txt            # 依赖包列表
├── CREDENTIAL_MANAGER_GUIDE.md # 详细使用指南
└── README_CREDENTIAL_MANAGER.md # 本文件
```

## 🔧 主要功能模块

### 1. 凭证管理器 (CredentialManager)
- 凭证的增删改查
- 智能负载均衡选择
- 配额和状态管理
- 性能指标跟踪

### 2. 加密存储 (CredentialVault)
- SQLite数据库存储
- Fernet对称加密
- 凭证归档和历史记录
- 安全的密钥管理

### 3. 负载均衡策略 (LoadBalancingStrategy)
- Random - 随机选择
- Round Robin - 轮询
- Weighted Round Robin - 加权轮询
- Least Connections - 最少连接
- Response Time - 响应时间优先
- Quota Aware - 配额感知（推荐）
- Adaptive - 自适应策略
- Health Based - 基于健康状态

### 4. 健康检查与自愈 (HealthChecker & SelfHealingEngine)
- 定期健康检查
- 问题自动诊断
- 自动修复机制
- 健康趋势分析

### 5. 凭证发现 (CredentialDiscoveryEngine)
- 文件系统扫描
- 环境变量扫描
- 源代码扫描
- 置信度评分

### 6. 系统集成 (CredentialBridge)
- 统一接口
- 向后兼容
- 自动迁移
- 配置管理

## 🔌 与现有系统集成

### Docker集成

在 `docker-compose.yml` 中添加：

```yaml
services:
  scanner:
    environment:
      - CREDENTIAL_VAULT_DB=/data/credentials.db
      - CREDENTIAL_STRATEGY=quota_aware
      - AUTO_DISCOVER=true
      - ENABLE_HEALING=true
    volumes:
      - ./credentials.db:/data/credentials.db
      - ./credential_manager:/app/credential_manager
```

### 从旧TokenManager迁移

```python
from credential_manager.integration.credential_bridge import (
    migrate_from_token_manager,
    CredentialBridge
)

# 创建桥接器
bridge = CredentialBridge()

# 迁移现有tokens
migrated_count = migrate_from_token_manager(
    old_token_file='github_tokens.txt',
    bridge=bridge
)
print(f"成功迁移 {migrated_count} 个tokens")
```

### 使用适配器保持兼容性

```python
from credential_manager.integration.credential_bridge import TokenManagerAdapter

# 创建适配器
adapter = TokenManagerAdapter(credential_manager)

# 使用旧接口
token = adapter.get_token()
adapter.mark_token_used(token, success=True)
```

## 📊 监控和报告

### 实时监控仪表板

```python
from credential_manager.monitoring.dashboard import Dashboard, ConsoleDashboard

# 创建并启动仪表板
dashboard = Dashboard(manager)
dashboard.start()

# 运行控制台界面
console = ConsoleDashboard(dashboard)
console.run_interactive(refresh_interval=5)
```

### 生成健康报告

```python
# 获取健康报告
health_report = bridge.get_health_report()

# 生成监控报告
dashboard.generate_report('monitoring_report.json')
```

## 🛡️ 安全最佳实践

1. **永不硬编码凭证** - 使用环境变量或配置文件
2. **定期轮换** - 设置凭证过期策略
3. **最小权限原则** - 只授予必要的权限
4. **审计日志** - 记录所有凭证使用情况
5. **加密存储** - 始终使用加密存储凭证

## 📈 性能优化

- 使用缓存减少数据库访问
- 批量操作提高效率
- 异步处理提升并发性能
- 智能负载均衡优化资源利用

## 🐛 故障排除

### 常见问题

1. **无法找到凭证**
   - 检查发现路径配置
   - 确认文件权限
   - 查看日志文件

2. **凭证健康评分低**
   - 运行健康检查诊断
   - 查看问题和建议
   - 启用自愈机制

3. **数据库锁定**
   ```bash
   rm credentials.db-journal
   ```

4. **加密密钥丢失**
   ```python
   from cryptography.fernet import Fernet
   new_key = Fernet.generate_key()
   ```

## 📚 文档

- [详细使用指南](CREDENTIAL_MANAGER_GUIDE.md) - 完整的功能说明和API参考
- [高级集成文档](ADVANCED_CREDENTIAL_MANAGER_INTEGRATION.md) - 架构设计和集成方案
- [Docker故障排除](DOCKER_TROUBLESHOOTING.md) - Docker相关问题解决

## 🤝 贡献

欢迎提交Issue和Pull Request来改进系统。

## 📄 许可

本项目采用MIT许可证。

## 🎯 路线图

- [ ] Web UI界面
- [ ] REST API接口
- [ ] 更多服务类型支持
- [ ] 分布式部署支持
- [ ] 机器学习优化策略
- [ ] 更多加密算法支持

## 💡 提示

- 运行 `python start_credential_manager.py` 查看完整演示
- 使用 `--mode dashboard` 参数启动交互式监控
- 查看 `test_credential_manager.py` 了解更多使用示例

---

**版本**: 1.0.0  
**最后更新**: 2024  
**作者**: Kilo Code  

🚀 **立即开始使用高级凭证管理系统，让您的API密钥管理更智能、更安全、更高效！**