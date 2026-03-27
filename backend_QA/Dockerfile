# Backend QA - FastAPI 问答服务 (端口 8000)
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
    fastapi uvicorn[standard] \
    langchain langgraph \
    pydantic pydantic-settings \
    python-dotenv python-multipart \
    redis opensearch-py \
    minio \
    aiohttp httpx \
    numpy tiktoken \
    sqlalchemy>=2.0.0 pymysql>=1.1.0 \
    python-jose[cryptography] "bcrypt>=3.2.0,<4.0.0"

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
COPY --chown=appuser:appuser backend_QA ./backend_QA

# 设置权限
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# 启动命令
CMD ["uvicorn", "backend_QA.main:app", "--host", "0.0.0.0", "--port", "8000"]
