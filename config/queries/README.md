# 📁 API查询模板目录

## 📋 文件结构

```
config/queries/
├── README.md           # 本文档
├── gemini.txt         # Gemini API查询（默认）
├── openai.txt         # OpenAI API查询
├── anthropic.txt      # Anthropic Claude API查询
├── aws.txt            # AWS Access Keys查询
├── azure.txt          # Azure OpenAI API查询
├── cohere.txt         # Cohere API查询
└── huggingface.txt    # Hugging Face API查询
```

## 🎯 使用方法

### 1. 默认使用（扫描Gemini）

系统默认使用 `gemini.txt` 的查询：

```bash
# 复制到根目录
cp config/queries/gemini.txt queries.txt

# 运行扫描
python app/api_key_scanner_super.py
```

### 2. 扫描特定API

#### 方法A：复制对应的查询文件

```bash
# 扫描OpenAI
cp config/queries/openai.txt queries.txt
python app/api_key_scanner_super.py --api-types openai

# 扫描Anthropic
cp config/queries/anthropic.txt queries.txt
python app/api_key_scanner_super.py --api-types anthropic
```

#### 方法B：合并多个查询文件

```bash
# 同时扫描Gemini和OpenAI
cat config/queries/gemini.txt config/queries/openai.txt > queries.txt
python app/api_key_scanner_super.py --api-types gemini,openai
```

### 3. 自动选择查询文件（推荐）

创建一个脚本自动选择正确的查询文件：

```bash
#!/bin/bash
# scan_api.sh

API_TYPE=${1:-gemini}  # 默认gemini

# 复制对应的查询文件
cp config/queries/${API_TYPE}.txt queries.txt

# 运行扫描
python app/api_key_scanner_super.py --api-types $API_TYPE
```

使用：
```bash
./scan_api.sh openai    # 扫描OpenAI
./scan_api.sh anthropic  # 扫描Anthropic
./scan_api.sh            # 默认扫描Gemini
```

## 📊 查询模板内容

每个查询文件包含：

| 部分 | 说明 | 示例 |
|------|------|------|
| **基础搜索** | 最基本的密钥模式搜索 | `AIzaSy in:file` |
| **环境变量文件** | 搜索.env等配置文件 | `AIzaSy in:file filename:.env` |
| **配置文件** | JSON/YAML配置 | `AIzaSy in:file extension:json` |
| **语言特定** | 各编程语言的配置 | `AIzaSy in:file language:python` |
| **组合搜索** | 多关键词组合 | `"AIzaSy" "gemini" in:file` |
| **时间过滤** | 最近更新的仓库 | `AIzaSy in:file pushed:>2024-11-01` |
| **特殊搜索** | 公开仓库、高星项目等 | `AIzaSy in:file stars:>100` |

## 🔧 自定义查询

### 创建自定义查询文件

1. 复制模板：
```bash
cp config/queries/gemini.txt config/queries/custom.txt
```

2. 编辑查询：
```bash
vim config/queries/custom.txt
```

3. 使用自定义查询：
```bash
cp config/queries/custom.txt queries.txt
python app/api_key_scanner_super.py
```

### 添加新的API类型

1. 创建查询文件：
```bash
touch config/queries/new_api.txt
```

2. 添加查询模式：
```
# 基础搜索
your-pattern in:file

# 环境变量
YOUR_API_KEY in:file filename:.env

# 配置文件
your-pattern in:file extension:json
```

3. 更新 `config/api_patterns.json` 添加API配置

## 📈 最佳实践

### 1. 按需选择查询

- **快速扫描**：只使用基础搜索部分
- **深度扫描**：使用完整查询文件
- **精确扫描**：自定义特定查询

### 2. 优化查询顺序

将最可能找到密钥的查询放在前面：
1. 环境变量文件
2. 配置文件
3. 源代码文件

### 3. 避免重复

不要在同一次扫描中使用重复的查询，会浪费API配额。

### 4. 定期更新

根据发现的模式更新查询文件：
```bash
# 发现新的密钥位置后，添加到查询文件
echo "new-pattern in:file" >> config/queries/gemini.txt
```

## 🚀 快速命令

```bash
# 扫描Gemini（默认）
cp config/queries/gemini.txt queries.txt && python app/api_key_scanner_super.py

# 扫描OpenAI
cp config/queries/openai.txt queries.txt && python app/api_key_scanner_super.py --api-types openai

# 扫描多个API
cat config/queries/gemini.txt config/queries/openai.txt > queries.txt && \
python app/api_key_scanner_super.py --api-types gemini,openai

# 扫描所有支持的API
cat config/queries/*.txt > queries.txt && \
python app/api_key_scanner_super.py --api-types gemini,openai,anthropic,aws,azure,cohere,huggingface
```

## 📝 注意事项

1. **查询文件大小**：每个文件保持在100行以内，避免触发GitHub限流
2. **更新频率**：定期更新时间过滤条件
3. **备份**：修改前备份原始查询文件
4. **测试**：新查询先小范围测试

---

**更新日期**: 2024-01-09  
**版本**: 1.0.0