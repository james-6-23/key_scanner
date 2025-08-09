# 多阶段构建 - 超级版API密钥扫描器
FROM python:3.11-slim as builder

# 设置构建环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_NO_CACHE=1 \
    PATH="/root/.local/bin:$PATH"

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh

# 设置工作目录
WORKDIR /build

# 复制依赖文件
COPY requirements.txt* pyproject.toml* ./

# 安装Python依赖
RUN uv pip install --system \
    google-generativeai>=0.8.5 \
    python-dotenv>=1.1.1 \
    requests>=2.32.4 \
    aiohttp>=3.9.0 \
    asyncio>=3.4.3 \
    cryptography>=41.0.0 \
    pycryptodome>=3.19.0 \
    redis>=5.0.0 \
    psutil>=5.9.0 \
    colorama>=0.4.6 \
    rich>=13.7.0 \
    click>=8.1.0 \
    pyyaml>=6.0.1 \
    jsonschema>=4.20.0 \
    tenacity>=8.2.0 \
    httpx>=0.25.0 \
    openai>=1.0.0 \
    anthropic>=0.8.0 \
    cohere>=4.0.0 \
    boto3>=1.34.0

# 最终镜像
FROM python:3.11-slim

# 设置运行时环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/root/.local/bin:$PATH" \
    # 应用环境变量
    DATA_PATH=/app/data \
    QUERIES_FILE=/app/queries.txt \
    CONFIG_PATH=/app/config \
    CREDENTIAL_MANAGER_PATH=/app/credential_manager \
    # 默认配置
    CREDENTIAL_AUTO_HARVEST=false \
    USE_CREDENTIAL_MANAGER=true \
    DEFAULT_API_TYPE=gemini

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制Python包
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /root/.local /root/.local

# 设置工作目录
WORKDIR /app

# 复制应用代码
COPY . /app/

# 创建必要的目录结构
RUN mkdir -p \
    /app/data/keys \
    /app/data/logs \
    /app/data/cache \
    /app/data/credentials \
    /app/data/monitoring \
    /app/config/queries \
    /app/credential_manager/storage \
    && chmod -R 755 /app

# 设置健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import os; exit(0 if os.path.exists('/app/data/logs') else 1)"

# 数据卷挂载点
VOLUME ["/app/data", "/app/config", "/app/.env"]

# 默认启动命令 - 使用启动器
ENTRYPOINT ["python"]
CMD ["scanner_launcher.py"]
