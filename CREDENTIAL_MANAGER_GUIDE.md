# 高级凭证管理系统使用指南

## 📋 目录

1. [系统概述](#系统概述)
2. [快速开始](#快速开始)
3. [核心功能](#核心功能)
4. [集成指南](#集成指南)
5. [配置说明](#配置说明)
6. [API参考](#api参考)
7. [最佳实践](#最佳实践)
8. [故障排除](#故障排除)

## 系统概述

高级凭证管理系统（Advanced Credential Manager）是一个企业级的API凭证生命周期管理解决方案，提供以下核心能力：

### 🎯 主要特性

- **智能负载均衡**：多种策略（配额感知、加权轮询、响应时间等）
- **自动发现**：扫描文件系统、环境变量、代码中的凭证
- **自愈机制**：自动检测和修复凭证问题
- **加密存储**：使用Fernet对称加密保护凭证
- **健康监控**：实时监控凭证健康状态
- **向后兼容**：提供适配器兼容旧的TokenManager接口

### 📁 模块结构

```
credential_manager/
├── core/               # 核心功能
│   ├── models.py      # 数据模型
│   └── manager.py     # 凭证管理器
├── storage/           # 存储层
│   └── vault.py       # 加密存储
├── balancer/          # 负载均衡
│   └── strategies.py  # 均衡策略
├── healing/           # 自愈机制
│   └── health_check.py # 健康检查
├── discovery/         # 凭证发现
│   └── discovery.py   # 发现引擎
├── integration/       # 系统集成
│   └── credential_bridge.py # 桥接器
└── monitoring/        # 监控
    └── dashboard.py   # 监控仪表板
```

## 快速开始

### 1. 基本使用

```python
from credential_manager.core.models import ServiceType
from credential_manager.core.manager import CredentialManager
from credential_manager.storage.vault import CredentialVault

# 创建凭证管理器
vault = CredentialVault(db_path='credentials.db')
manager = CredentialManager(vault=vault, strategy='quota_aware')

# 添加凭证
cred_id = manager.add_credential(
    value="ghp_your_github_token_here",
    service_type=ServiceType.GITHUB
)

# 获取最优凭证
credential = manager.get_optimal_credential(ServiceType.GITHUB)
if credential:
    print(f"使用凭证: {credential.masked_value}")
    # 使用凭证进行API调用...
    
# 更新凭证状态
manager.update_credential_status(cred_id, CredentialStatus.ACTIVE)
```

### 2. 使用桥接器（推荐）

```python
from credential_manager.integration.credential_bridge import CredentialBridge

# 创建桥接器（自动发现和导入凭证）
bridge = CredentialBridge(
    auto_discover=True,
    enable_healing=True
)

# 获取凭证
cred = bridge.get_credential(service_type='github')
if cred:
    token = cred['value']
    # 使用token...
```

### 3. 兼容旧系统

```python
from credential_manager.integration.credential_bridge import GitHubTokenBridge

# 从现有的github_tokens.txt文件创建桥接器
github_bridge = GitHubTokenBridge(tokens_file='github_tokens.txt')

# 使用兼容接口
token = github_bridge.get_next_token()
github_bridge.mark_token_exhausted(token)
```

## 核心功能

### 🔄 负载均衡策略

系统提供多种负载均衡策略：

| 策略名称 | 描述 | 适用场景 |
|---------|------|---------|
| `random` | 随机选择 | 测试环境 |
| `round_robin` | 轮询 | 负载均匀分布 |
| `weighted_round_robin` | 加权轮询 | 基于健康评分 |
| `least_connections` | 最少连接 | 并发请求场景 |
| `response_time` | 响应时间 | 性能优先 |
| `quota_aware` | 配额感知（默认） | 生产环境推荐 |
| `adaptive` | 自适应 | 动态调整策略 |
| `health_based` | 基于健康状态 | 稳定性优先 |

使用示例：

```python
# 指定策略
manager = CredentialManager(vault=vault, strategy='quota_aware')

# 或在获取时指定
credential = manager.get_optimal_credential(
    service_type=ServiceType.GITHUB,
    strategy='response_time'
)
```

### 🔍 凭证发现

自动扫描和发现系统中的凭证：

```python
from credential_manager.discovery.discovery import (
    CredentialDiscoveryEngine,
    FileScanner,
    EnvironmentScanner,
    CodeScanner
)

# 创建发现引擎
discovery = CredentialDiscoveryEngine()

# 添加扫描器
discovery.add_scanner(FileScanner(['.', './config']))
discovery.add_scanner(EnvironmentScanner())
discovery.add_scanner(CodeScanner(['./src']))

# 执行发现
discovered = discovery.discover()

# 获取高置信度凭证
high_confidence = discovery.get_high_confidence_credentials(threshold=0.8)
```

### 🏥 健康检查与自愈

```python
from credential_manager.healing.health_check import HealthChecker, SelfHealingEngine

# 创建健康检查器
health_checker = HealthChecker(check_interval=60)

# 检查凭证健康
result = health_checker.check_credential(credential)
print(f"健康状态: {result.status.value}")
print(f"健康评分: {result.score}")

# 启用自愈
healing_engine = SelfHealingEngine(health_checker)
await healing_engine.diagnose_and_heal(credential, manager)
```

### 📊 监控仪表板

```python
from credential_manager.monitoring.dashboard import Dashboard, ConsoleDashboard

# 创建仪表板
dashboard = Dashboard(manager, update_interval=5)
dashboard.start()

# 获取监控摘要
summary = dashboard.get_summary()

# 生成报告
dashboard.generate_report('monitoring_report.json')

# 控制台显示
console = ConsoleDashboard(dashboard)
console.run_interactive(refresh_interval=5)
```

## 集成指南

### Docker集成

更新 `docker-compose.yml`：

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

### 与现有TokenManager集成

```python
from credential_manager.integration.credential_bridge import TokenManagerAdapter

# 创建适配器
adapter = TokenManagerAdapter(manager)

# 使用旧接口
token = adapter.get_token()
adapter.mark_token_used(token, success=True)
stats = adapter.get_token_stats()
```

### 环境变量配置

```bash
# .env 文件
CREDENTIAL_VAULT_DB=credentials.db
CREDENTIAL_STRATEGY=quota_aware
HEALTH_CHECK_INTERVAL=60
AUTO_DISCOVER=true
ENABLE_HEALING=true
AUTO_IMPORT_THRESHOLD=0.8
```

## 配置说明

### 配置文件格式

创建 `credential_config.json`：

```json
{
  "vault_db_path": "credentials.db",
  "balancing_strategy": "quota_aware",
  "health_check_interval": 60,
  "discovery_paths": [
    ".",
    "./config",
    "./secrets"
  ],
  "auto_import_threshold": 0.8,
  "encryption_key": null,
  "max_retries": 3,
  "retry_delay": 1.0,
  "quota_buffer": 0.1,
  "health_score_weights": {
    "status": 0.3,
    "quota": 0.3,
    "success_rate": 0.2,
    "response_time": 0.2
  }
}
```

### 服务类型配置

支持的服务类型：

- `GITHUB` - GitHub API
- `OPENAI` - OpenAI API
- `AWS` - AWS Services
- `AZURE` - Azure Services
- `GCP` - Google Cloud Platform
- `GENERIC` - 通用API

## API参考

### CredentialManager

```python
class CredentialManager:
    def add_credential(value: str, service_type: ServiceType, metadata: Dict = None) -> str
    def get_optimal_credential(service_type: ServiceType = None, strategy: str = None) -> Credential
    def update_credential_status(credential_id: str, status: CredentialStatus) -> bool
    def remove_credential(credential_id: str) -> bool
    def list_credentials(service_type: ServiceType = None) -> List[Credential]
    def get_statistics() -> Dict[str, Any]
    def rotate_credential(credential_id: str) -> str
```

### CredentialBridge

```python
class CredentialBridge:
    def get_credential(service_type: str = None, strategy: str = None) -> Dict
    def add_credential_from_file(file_path: str) -> int
    def export_credentials(output_path: str, include_values: bool = False)
    def get_health_report() -> Dict[str, Any]
    async def perform_healing() -> Dict[str, Any]
```

### 凭证状态

```python
class CredentialStatus(Enum):
    ACTIVE = "active"          # 正常可用
    DEGRADED = "degraded"      # 性能降级
    EXHAUSTED = "exhausted"    # 配额耗尽
    RATE_LIMITED = "rate_limited"  # 速率限制
    INVALID = "invalid"        # 无效
    REVOKED = "revoked"        # 已撤销
    EXPIRED = "expired"        # 已过期
```

## 最佳实践

### 1. 凭证轮换

```python
# 设置自动轮换
manager.set_rotation_policy(
    max_usage=1000,
    max_age_days=30,
    auto_rotate=True
)
```

### 2. 错误处理

```python
try:
    credential = manager.get_optimal_credential(ServiceType.GITHUB)
    if not credential:
        # 处理无可用凭证的情况
        raise Exception("No credentials available")
        
    # 使用凭证
    response = make_api_call(credential.value)
    
    # 更新指标
    manager.update_metrics(
        credential.id,
        success=True,
        response_time=response.elapsed.total_seconds()
    )
    
except RateLimitError:
    # 处理速率限制
    manager.update_credential_status(
        credential.id,
        CredentialStatus.RATE_LIMITED
    )
```

### 3. 安全建议

- **永不硬编码凭证**：使用环境变量或配置文件
- **定期轮换**：设置凭证过期策略
- **最小权限原则**：只授予必要的权限
- **审计日志**：记录所有凭证使用情况
- **加密存储**：始终使用加密存储凭证

### 4. 性能优化

```python
# 使用缓存
manager.enable_caching(ttl=300)

# 批量操作
credentials = [
    ("token1", ServiceType.GITHUB),
    ("token2", ServiceType.GITHUB),
]
manager.bulk_add_credentials(credentials)

# 异步操作
async def process():
    credential = await manager.get_optimal_credential_async()
    # ...
```

## 故障排除

### 常见问题

#### 1. 无法找到凭证

```python
# 检查发现路径
discovery = CredentialDiscoveryEngine()
discovery.add_scanner(FileScanner(['./']))
discovered = discovery.discover()
print(f"发现 {len(discovered)} 个凭证")
```

#### 2. 凭证健康评分低

```python
# 诊断凭证问题
health_result = health_checker.check_credential(credential)
print(f"问题: {health_result.issues}")
print(f"建议: {health_result.recommendations}")
```

#### 3. 数据库锁定

```bash
# 清理锁定的数据库
rm credentials.db-journal
```

#### 4. 加密密钥丢失

```python
# 重新生成加密密钥
from cryptography.fernet import Fernet
new_key = Fernet.generate_key()
print(f"新密钥: {new_key.decode()}")
```

### 日志配置

```python
import logging

# 启用详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('credential_manager.log'),
        logging.StreamHandler()
    ]
)
```

### 性能监控

```python
# 监控性能指标
metrics = manager.get_performance_metrics()
print(f"平均响应时间: {metrics['avg_response_time']}s")
print(f"成功率: {metrics['success_rate']*100}%")
print(f"每秒请求数: {metrics['requests_per_second']}")
```

## 迁移指南

### 从旧的TokenManager迁移

```python
from credential_manager.integration.credential_bridge import migrate_from_token_manager

# 创建桥接器
bridge = CredentialBridge()

# 迁移tokens
migrated_count = migrate_from_token_manager(
    old_token_file='github_tokens.txt',
    bridge=bridge
)

print(f"成功迁移 {migrated_count} 个tokens")
```

### 数据备份与恢复

```python
# 备份
bridge.export_credentials('backup.json', include_values=True)

# 恢复
imported = bridge.add_credential_from_file('backup.json')
print(f"恢复了 {imported} 个凭证")
```

## 示例应用

### GitHub API扫描器集成

```python
from credential_manager.integration.credential_bridge import GitHubTokenBridge

class GitHubScanner:
    def __init__(self):
        self.token_bridge = GitHubTokenBridge('github_tokens.txt')
        
    def scan_repository(self, repo_url):
        token = self.token_bridge.get_next_token()
        if not token:
            raise Exception("No tokens available")
            
        try:
            # 执行扫描
            result = self._perform_scan(repo_url, token)
            return result
            
        except RateLimitException:
            self.token_bridge.mark_token_exhausted(token)
            # 递归重试with新token
            return self.scan_repository(repo_url)
```

### 多服务凭证管理

```python
class MultiServiceClient:
    def __init__(self):
        self.bridge = CredentialBridge()
        
    def call_github_api(self):
        cred = self.bridge.get_credential('github')
        # 使用GitHub凭证
        
    def call_openai_api(self):
        cred = self.bridge.get_credential('openai')
        # 使用OpenAI凭证
        
    def call_aws_api(self):
        cred = self.bridge.get_credential('aws')
        # 使用AWS凭证
```

## 总结

高级凭证管理系统提供了一个完整的解决方案来管理API凭证的整个生命周期。通过智能负载均衡、自动发现、自愈机制和健康监控，系统能够确保凭证的高可用性和安全性。

### 下一步

1. 运行测试脚本验证安装：`python test_credential_manager.py`
2. 配置环境变量和配置文件
3. 集成到现有系统
4. 启动监控仪表板
5. 设置定期备份

### 获取帮助

- 查看源代码中的文档字符串
- 运行测试脚本了解使用方法
- 查看日志文件排查问题

---

*版本: 1.0.0 | 最后更新: 2024*