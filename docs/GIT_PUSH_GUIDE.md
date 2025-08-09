# 📦 Git分阶段推送指南

本文档提供了将项目更新分阶段推送到GitHub的详细步骤。

## 🎯 推送策略

将更新分为5个阶段推送，每个阶段都是独立且完整的功能模块。

## 📝 准备工作

### 1. 检查当前状态
```bash
# 查看当前分支
git branch

# 查看修改状态
git status

# 查看远程仓库
git remote -v
```

### 2. 备份当前工作
```bash
# 创建备份分支
git checkout -b backup-$(date +%Y%m%d)
git add .
git commit -m "Backup before major push"

# 切回主分支
git checkout main
```

## 🚀 分阶段推送

### 阶段1：核心功能更新
**包含内容**：超级版扫描器、通用扫描器、启动器

```bash
# 添加核心文件
git add app/api_key_scanner_super.py
git add app/api_scanner_universal.py
git add scanner_launcher.py
git add app/api_key_scanner_improved.py

# 提交
git commit -m "feat: 添加超级版扫描器和通用API扫描器

- 实现api_key_scanner_super.py - 企业级扫描器
- 实现api_scanner_universal.py - 通用多API扫描器
- 更新scanner_launcher.py - 交互式启动器
- 支持7种主流API扫描"

# 推送
git push origin main
```

### 阶段2：凭证管理系统
**包含内容**：完整的凭证管理模块

```bash
# 添加凭证管理系统
git add credential_manager/

# 提交
git commit -m "feat: 实现企业级凭证管理系统

- 核心管理模块 (core/)
- 存储层实现 (storage/)
- 负载均衡器 (balancer/) - 8种策略
- 凭证发现引擎 (discovery/)
- 自愈机制 (healing/)
- 监控系统 (monitoring/)
- 系统集成 (integration/)"

# 推送
git push origin main
```

### 阶段3：配置系统
**包含内容**：API配置、查询模板

```bash
# 添加配置文件
git add config/api_patterns.json
git add config/queries/
git add env.example
git add queries.example

# 提交
git commit -m "feat: 添加多API配置系统

- api_patterns.json - 7种API配置定义
- queries/ - 分API查询模板
- 支持Gemini、OpenAI、Anthropic等
- 环境变量示例更新"

# 推送
git push origin main
```

### 阶段4：Docker部署
**包含内容**：Docker配置和启动脚本

```bash
# 添加Docker相关文件
git add Dockerfile
git add docker-compose.yml
git add docker-compose.minimal.yml
git add docker-start.sh
git add docker-start.bat
git add DOCKER_QUICKSTART.md

# 提交
git commit -m "feat: 完整Docker部署方案

- 多阶段构建Dockerfile
- docker-compose.yml - 完整部署
- docker-compose.minimal.yml - 最小部署
- 跨平台启动脚本 (sh/bat)
- Docker快速开始指南"

# 推送
git push origin main
```

### 阶段5：文档和清理
**包含内容**：文档更新、项目清理

```bash
# 添加文档
git add README.md
git add PROJECT_COMPLETION_SUMMARY.md
git add docs/DOCKER_DEPLOYMENT_GUIDE.md
git add docs/MULTI_API_SCANNING_GUIDE.md
git add docs/GIT_PUSH_GUIDE.md

# 删除旧文件（如果还存在）
git rm -f *.sh 2>/dev/null || true
git rm -f fix_*.py 2>/dev/null || true
git rm -f test_*.py 2>/dev/null || true
git rm -f *_GUIDE.md 2>/dev/null || true
git rm -f README_*.md 2>/dev/null || true

# 提交
git commit -m "docs: 优化文档和项目结构

- 简化README.md
- 添加完整部署文档
- 清理旧脚本和临时文件
- 更新项目完成总结
- 版本升级到2.0.0"

# 推送
git push origin main
```

## 🔄 可选：一次性推送

如果您希望一次性推送所有更改：

```bash
# 添加所有更改
git add .

# 查看将要提交的文件
git status

# 提交所有更改
git commit -m "feat: v2.0.0 - 企业级多API扫描器

主要更新：
- 超级版扫描器：集成凭证管理和监控
- 通用API扫描器：支持7种主流API
- 企业级凭证管理系统
- Docker完整部署方案
- 交互式启动器
- 文档优化和项目清理

功能特性：
- 多API支持（Gemini、OpenAI、Anthropic等）
- 8种负载均衡策略
- 自愈机制
- 实时监控仪表板
- Token自动管理
- 加密存储"

# 推送到远程
git push origin main
```

## 📊 推送后验证

### 1. 检查GitHub页面
- 访问仓库主页
- 检查文件是否正确上传
- 查看commit历史

### 2. 验证Actions（如果有）
```bash
# 查看GitHub Actions状态
gh run list
gh run view
```

### 3. 创建Release（可选）
```bash
# 创建标签
git tag -a v2.0.0 -m "Release v2.0.0 - 企业级多API扫描器"

# 推送标签
git push origin v2.0.0

# 或使用GitHub CLI创建release
gh release create v2.0.0 \
  --title "v2.0.0 - 企业级多API扫描器" \
  --notes "主要更新：
- 超级版扫描器
- 多API支持
- 凭证管理系统
- Docker部署方案"
```

## ⚠️ 注意事项

1. **推送前检查**
   - 确保所有敏感信息已移除
   - 检查.gitignore是否正确配置
   - 确认没有包含API密钥或tokens

2. **大文件处理**
   - 如果有大文件，考虑使用Git LFS
   - 检查是否有不必要的二进制文件

3. **分支策略**
   - 建议在feature分支开发
   - 通过PR合并到main分支
   - 保持main分支稳定

## 🔧 问题处理

### 冲突解决
```bash
# 拉取最新代码
git pull origin main

# 如果有冲突，手动解决后
git add .
git commit -m "resolve: 解决合并冲突"
git push origin main
```

### 撤销推送
```bash
# 撤销最后一次commit（本地）
git reset --soft HEAD~1

# 强制推送（谨慎使用）
git push origin main --force
```

### 清理历史
```bash
# 如果需要清理敏感信息
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch 敏感文件" \
  --prune-empty --tag-name-filter cat -- --all
```

## 📝 推送检查清单

- [ ] 所有代码已测试
- [ ] 敏感信息已移除
- [ ] 文档已更新
- [ ] .env文件未包含
- [ ] github_tokens.txt未包含
- [ ] 旧脚本已删除
- [ ] commit信息清晰
- [ ] 版本号已更新

---

**提示**：建议在推送前先在本地测试所有功能，确保代码质量。