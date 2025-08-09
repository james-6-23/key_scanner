# 凭证管理系统快速修复指南

## 问题诊断

您遇到的问题：
1. **PyYAML依赖缺失** - `缺少依赖包: pyyaml`
2. **API不兼容** - `CredentialManager.__init__() got an unexpected keyword argument 'vault'`

## 快速修复步骤

### 1. 运行修复脚本

```bash
python fix_credential_manager.py
```

这个脚本会：
- 自动安装缺失的依赖（pyyaml, cryptography）
- 创建简化的测试脚本
- 生成最小依赖文件

### 2. 手动安装依赖（如果自动安装失败）

使用uv（推荐）：
```bash
uv pip install pyyaml
uv pip install cryptography  # 可选，但推荐
```

或使用pip：
```bash
pip install pyyaml
pip install cryptography  # 可选，但推荐
```

### 3. 运行测试

简化测试（推荐先运行）：
```bash
python test_credential_simple.py
```

完整测试套件：
```bash
python test_credential_manager.py
```

## API使用说明

### 正确的初始化方式

❌ 错误方式：
```python
vault = CredentialVault(db_path='test.db')
manager = CredentialManager(vault=vault)  # 错误！
```

✅ 正确方式：
```python
config = {
    "encryption_enabled": False,  # 可以禁用加密避免依赖
    "balancing_strategy": "round_robin",
    "health_check_interval": 0,  # 0表示禁用后台任务
    "discovery_enabled": False
}
manager = CredentialManager(config=config)
```

### 添加凭证的正确方式

✅ 正确的参数顺序：
```python
credential = manager.add_credential(
    service_type=ServiceType.GITHUB,  # 服务类型
    value="ghp_xxxxx",                # 凭证值
    metadata={"source": "manual"}     # 元数据（可选）
)
```

### ServiceType枚举值

可用的服务类型：
- `ServiceType.GITHUB` - GitHub
- `ServiceType.GEMINI` - Gemini
- `ServiceType.OPENAI` - OpenAI
- `ServiceType.CUSTOM` - 自定义

注意：没有 `ServiceType.GENERIC`，应使用 `ServiceType.CUSTOM`

## 常见问题解决

### Q1: ImportError: No module named 'yaml'

**解决方案**：
```bash
# 使用uv
uv pip install pyyaml

# 或使用pip
pip install pyyaml
```

### Q2: cryptography库警告

如果看到：`WARNING - cryptography library not available, encryption disabled`

这是正常的，系统会自动禁用加密功能。如果需要加密：
```bash
uv pip install cryptography
```

### Q3: 测试失败

如果测试仍然失败，尝试：

1. 清理旧的数据库文件：
```bash
rm -f test_*.db
rm -f *.db
```

2. 确保Python版本 >= 3.7：
```bash
python --version
```

3. 检查模块导入：
```python
python -c "from credential_manager.core.manager import CredentialManager; print('✓ 导入成功')"
```

## 最小可运行示例

```python
#!/usr/bin/env python3
from credential_manager.core.models import ServiceType
from credential_manager.core.manager import CredentialManager

# 创建管理器（禁用所有可选功能）
config = {
    "encryption_enabled": False,
    "health_check_interval": 0,
    "discovery_enabled": False
}
manager = CredentialManager(config=config)

# 添加凭证
cred = manager.add_credential(
    service_type=ServiceType.GITHUB,
    value="ghp_test1234567890",
    metadata={"test": True}
)

if cred:
    print(f"✓ 凭证添加成功: {cred.masked_value}")

# 获取凭证
optimal = manager.get_optimal_credential(ServiceType.GITHUB)
if optimal:
    print(f"✓ 获取凭证: {optimal.masked_value}")

print("✓ 测试完成!")
```

## 推送修复到Git

```bash
# 添加修复文件
git add fix_credential_manager.py test_credential_manager.py QUICK_FIX_GUIDE.md

# 提交
git commit -m "fix: 修复凭证管理系统兼容性问题"

# 推送
git push origin main
```

## 联系支持

如果问题仍未解决，请提供：
1. Python版本：`python --version`
2. 已安装的包：`pip list | grep -E "pyyaml|cryptography"`
3. 错误信息的完整输出

---

*版本: 1.0.1 | 最后更新: 2024*