# 🔍 多API类型扫描功能指南

## 📋 目录

1. [功能概述](#功能概述)
2. [支持的API类型](#支持的api类型)
3. [快速开始](#快速开始)
4. [配置说明](#配置说明)
5. [使用方法](#使用方法)
6. [扩展新API](#扩展新api)
7. [最佳实践](#最佳实践)

## 功能概述

系统现在支持扫描多种API密钥类型，不仅限于Gemini。通过配置文件驱动的架构，可以轻松添加新的API类型支持。

### 核心特性

- ✅ **默认扫描Gemini** - 保持向后兼容
- ✅ **支持7种主流API** - OpenAI、Anthropic、Cohere等
- ✅ **配置驱动** - 通过JSON配置文件管理
- ✅ **并行验证** - 同时验证多种API类型
- ✅ **独立存储** - 每种API类型分别保存

## 支持的API类型

| API类型 | 服务名称 | 密钥格式 | 默认状态 |
|---------|----------|----------|----------|
| `gemini` | Google Gemini | `AIzaSy...` (39字符) | ✅ 启用 |
| `openai` | OpenAI GPT | `sk-...` (51字符) | ❌ 禁用 |
| `anthropic` | Anthropic Claude | `sk-ant-api...` (100+字符) | ❌ 禁用 |
| `cohere` | Cohere | `co-...` (42字符) | ❌ 禁用 |
| `huggingface` | Hugging Face | `hf_...` (37字符) | ❌ 禁用 |
| `aws` | AWS Access Key | `AKIA...` (20字符) | ❌ 禁用 |
| `azure` | Azure OpenAI | 32字符十六进制 | ❌ 禁用 |

## 快速开始

### 1. 默认使用（扫描Gemini）

无需任何配置，默认扫描Gemini API密钥：

```bash
# 普通版
python app/api_key_scanner.py

# 改进版
python app/api_key_scanner_improved.py

# 超级版
python app/api_key_scanner_super.py
```

### 2. 扫描其他API类型

#### 方法1：命令行参数

```bash
# 扫描OpenAI密钥
python app/api_key_scanner_super.py --api-types openai

# 扫描多种密钥
python app/api_key_scanner_super.py --api-types gemini,openai,anthropic

# 使用通用扫描器
python app/api_scanner_universal.py --api-types openai
```

#### 方法2：环境变量

编辑`.env`文件：

```env
# 设置要扫描的API类型
TARGET_API_TYPES=gemini,openai,anthropic
```

然后运行：

```bash
python app/api_key_scanner_super.py
```

## 配置说明

### API配置文件

配置文件位于：`config/api_patterns.json`

每个API类型的配置结构：

```json
{
  "api_type": {
    "name": "服务名称",
    "pattern": "正则表达式",
    "validation_url": "验证端点",
    "validation_method": "GET或POST",
    "header_format": "请求头格式",
    "search_queries": ["GitHub搜索查询"],
    "env_vars": ["环境变量名"],
    "enabled": true/false
  }
}
```

### 环境变量配置

在`.env`中配置：

```env
# 要扫描的API类型
TARGET_API_TYPES=gemini

# 启用多API扫描
MULTI_API_SCAN_ENABLED=false

# 各API的验证开关
VALIDATE_GEMINI=true
VALIDATE_OPENAI=false
VALIDATE_ANTHROPIC=false
```

## 使用方法

### 1. 使用通用扫描器（推荐）

```python
from app.api_scanner_universal import UniversalAPIScanner

# 创建扫描器（默认扫描gemini）
scanner = UniversalAPIScanner()

# 或指定多个API类型
scanner = UniversalAPIScanner(['gemini', 'openai', 'anthropic'])

# 扫描内容
content = "API_KEY=AIzaSy..."
keys = scanner.extract_all_keys(content)

# 验证密钥
for api_type, key_list in keys.items():
    for key in key_list:
        is_valid = scanner.validate_key(key, api_type)
        print(f"{api_type}: {key[:10]}... - {'✅' if is_valid else '❌'}")
```

### 2. 使用超级版扫描器

```bash
# 扫描Gemini（默认）
python app/api_key_scanner_super.py

# 扫描OpenAI
python app/api_key_scanner_super.py --api-types openai

# 扫描多种
python app/api_key_scanner_super.py --api-types gemini,openai
```

### 3. 批量扫描示例

创建`scan_all_apis.sh`：

```bash
#!/bin/bash

# 扫描所有支持的API类型
API_TYPES="gemini,openai,anthropic,cohere,huggingface"

echo "开始扫描多种API密钥..."
python app/api_key_scanner_super.py --api-types $API_TYPES

echo "扫描完成！"
```

## 扩展新API

### 步骤1：添加配置

编辑`config/api_patterns.json`，添加新API：

```json
{
  "your_api": {
    "name": "Your API Service",
    "pattern": "your-regex-pattern",
    "validation_url": "https://api.example.com/validate",
    "validation_method": "GET",
    "header_format": "Authorization: Bearer {key}",
    "search_queries": [
      "your_api_key in:file",
      "YOUR_API_KEY in:file"
    ],
    "env_vars": ["YOUR_API_KEY"],
    "enabled": true
  }
}
```

### 步骤2：添加查询

创建`queries_your_api.txt`：

```
your_api_key in:file
YOUR_API_KEY in:file
your-api-prefix in:file extension:json
```

### 步骤3：运行扫描

```bash
python app/api_key_scanner_super.py --api-types your_api
```

## 最佳实践

### 1. 性能优化

```env
# 限制同时扫描的API类型数量
TARGET_API_TYPES=gemini,openai  # 不要超过3个

# 调整并发数
HAJIMI_MAX_WORKERS=5  # 减少并发避免限流
```

### 2. 安全建议

- **不要同时扫描太多类型** - 避免触发GitHub限流
- **验证要谨慎** - 某些API验证会消耗配额
- **使用沙箱验证** - 避免影响生产环境

### 3. 存储管理

扫描结果按API类型分别存储：

```
data/keys/
├── gemini_valid_keys.json
├── openai_valid_keys.json
├── anthropic_valid_keys.json
└── [api_type]_valid_keys_[timestamp].json
```

### 4. 查询优化

为每种API创建专门的查询文件：

```
config/queries/
├── gemini.txt     # Gemini专用查询
├── openai.txt     # OpenAI专用查询
└── anthropic.txt  # Anthropic专用查询
```

## 示例输出

```
========================================================
🚀 API密钥扫描器 - 超级版
========================================================
🎯 扫描目标: gemini, openai, anthropic
========================================================

🔍 处理查询: AIzaSy in:file
📦 找到 42 个仓库

🔑 发现密钥:
  gemini: 15 个
  openai: 8 个
  anthropic: 3 个

⚡ 开始验证...
✅ 有效 gemini 密钥: AIzaSyXXX...
✅ 有效 openai 密钥: sk-XXXXX...
❌ 无效 anthropic 密钥: sk-ant-XXX...

========================================================
📊 扫描统计
========================================================
⏱️  运行时间: 0:05:23

🔑 GEMINI (Google Gemini):
   发现: 15
   ✅ 有效: 8
   ❌ 无效: 7
   📈 成功率: 53.3%

🔑 OPENAI (OpenAI GPT):
   发现: 8
   ✅ 有效: 3
   ❌ 无效: 5
   📈 成功率: 37.5%

🔑 ANTHROPIC (Anthropic Claude):
   发现: 3
   ✅ 有效: 1
   ❌ 无效: 2
   📈 成功率: 33.3%
========================================================
```

## 常见问题

### Q: 如何只扫描Gemini？
A: 不需要任何配置，这是默认行为。

### Q: 如何添加自定义API？
A: 编辑`config/api_patterns.json`添加配置即可。

### Q: 验证失败怎么办？
A: 检查API密钥格式和验证URL是否正确。

### Q: 如何提高扫描速度？
A: 减少同时扫描的API类型数量，增加GitHub tokens。

## 总结

多API扫描功能让系统更加灵活和强大：

- ✅ **向后兼容** - 默认行为不变（扫描Gemini）
- ✅ **易于扩展** - 配置文件驱动
- ✅ **并行处理** - 高效验证
- ✅ **独立管理** - 每种API分别处理

通过简单的配置，就可以扫描和管理多种API密钥类型！

---

**版本**: 1.0.0  
**更新日期**: 2024-01-09  
**作者**: Kilo Code