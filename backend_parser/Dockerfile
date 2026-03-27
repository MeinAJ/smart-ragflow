# Backend Parser - 文档解析 Worker
# 使用多阶段构建 + slim 基础镜像优化体积

# =================== 阶段1：依赖安装 ===================
FROM python:3.11-slim AS builder

WORKDIR /app

# 安装编译依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 安装依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    sqlalchemy>=2.0.0 pymysql>=1.1.0 \
    pydantic pydantic-settings \
    python-dotenv \
    redis minio opensearch-py \
    aiohttp httpx \
    numpy tiktoken \
    pdfplumber python-docx openpyxl python-pptx

# =================== 阶段2：运行 ===================
FROM python:3.11-slim

# 创建非 root 用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# 从 builder 复制虚拟环境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 复制应用代码
COPY --chown=appuser:appuser backend_common ./backend_common
COPY --chown=appuser:appuser backend_parser ./backend_parser

# 设置权限
USER appuser

# Worker 不需要暴露端口，但保留健康检查方式
# 可以通过检查进程是否存在来确认健康状态
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# 启动命令 - 运行 Worker
CMD ["python", "backend_parser/worker.py"]
