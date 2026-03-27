"""
FastAPI 应用主入口模块。

此模块初始化 FastAPI 应用并注册所有路由。
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from backend_QA.api import chat, download, history, auth

# 加载 .env 文件（通过环境变量标记避免 Uvicorn reload 模式下重复打印）
env_path = Path(__file__).parent.parent / ".env"
_env_loaded_flag = "_RAGFLOW_ENV_LOADED"

if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
    if not os.environ.get(_env_loaded_flag):
        os.environ[_env_loaded_flag] = "1"
        print(f"✓ 已加载环境变量: {env_path}")
else:
    # 尝试从当前工作目录加载
    load_dotenv(override=True)
    if not os.environ.get(_env_loaded_flag):
        os.environ[_env_loaded_flag] = "1"
        print("✓ 尝试从当前目录加载 .env")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = FastAPI(
    title="Smart RAGFlow API",
    description="智能问答系统 API - 基于 RAG 的流式问答服务",
    version="0.1.0",
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(download.router)
app.include_router(history.router)


@app.get("/")
async def root() -> dict:
    """
    根路由，用于健康检查。

    Returns:
        dict: 返回服务状态信息
    """
    return {"status": "ok", "service": "Smart RAGFlow API"}


@app.get("/health")
async def health_check() -> dict:
    """
    健康检查端点。

    Returns:
        dict: 返回服务健康状态
    """
    return {"status": "ok", "version": "0.1.0"}


if __name__ == "__main__":
    uvicorn.run(
        "backend_QA.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
