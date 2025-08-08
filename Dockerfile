# 使用Python 3.11 slim镜像作为基础
FROM python:3.11-slim

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_NO_CACHE=1 \
    PATH="/root/.local/bin:$PATH" \
    # 应用环境变量
    DATA_PATH=/app/data \
    QUERIES_FILE=/app/queries.txt

# 安装系统依赖和UV
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh

# 设置工作目录
WORKDIR /app

# 克隆项目代码（或者复制本地代码）
# 如果使用本地代码，取消注释下面的COPY命令，注释掉git clone
# COPY . /app/

# 从GitHub克隆最新代码
RUN git clone https://github.com/james-6-23/key_scanner.git /tmp/scanner \
    && cp -r /tmp/scanner/* /app/ \
    && rm -rf /tmp/scanner

# 使用UV安装Python依赖
RUN uv pip install --system \
    google-generativeai>=0.8.5 \
    python-dotenv>=1.1.1 \
    requests>=2.32.4

# 创建必要的目录结构
RUN mkdir -p /app/data/keys /app/data/logs /app/data/cache

# 设置健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD pgrep -f "api_key_scanner" || exit 1

# 数据卷挂载点
VOLUME ["/app/data", "/app/queries.txt", "/app/.env"]

# 启动命令
CMD ["python", "app/api_key_scanner.py"]
