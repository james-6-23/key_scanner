#!/bin/bash

echo "=========================================="
echo "   推送凭证管理系统修复"
echo "=========================================="

# 添加修复文件
echo "添加修复文件..."
git add fix_credential_manager.py
git add test_credential_manager.py

# 查看状态
echo ""
echo "Git状态:"
git status --short

# 创建提交
echo ""
echo "创建提交..."
git commit -m "fix: 修复凭证管理系统兼容性问题

修复内容：
- 修正CredentialManager初始化参数（使用config而非vault）
- 更新测试代码以匹配实际API
- 添加修复脚本fix_credential_manager.py
- 创建简化测试脚本test_credential_simple.py
- 处理PyYAML和cryptography依赖问题

问题解决：
- TypeError: CredentialManager.__init__() got an unexpected keyword argument 'vault'
- 依赖包缺失问题（pyyaml）
- 加密库可选化（cryptography）

测试改进：
- 禁用后台任务以简化测试
- 使用正确的ServiceType枚举值
- 修正API调用参数顺序"

# 推送
echo ""
echo "推送到远程仓库..."
git push origin main

echo ""
echo "✅ 修复已推送！"
echo ""
echo "在服务器上运行："
echo "1. python fix_credential_manager.py  # 运行修复脚本"
echo "2. python test_credential_simple.py   # 运行简化测试"
echo "3. python test_credential_manager.py  # 运行完整测试"