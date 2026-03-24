"""
Backend Admin 主入口。

提供文档管理后台服务。
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend_common import settings
from backend_admin.api.documents import router as documents_router
from backend_admin.database import engine
from backend_admin.models import Base

# 配置日志
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理。
    """
    # 启动时创建数据库表
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created.")
    
    yield
    
    # 关闭时清理资源
    logger.info("Shutting down...")


# 创建 FastAPI 应用
app = FastAPI(
    title="Smart RAGFlow Admin",
    description="Smart RAGFlow 文档管理后台服务",
    version="1.0.0",
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(documents_router)


@app.get("/health")
async def health_check():
    """健康检查接口。"""
    return {"status": "ok", "service": "backend-admin"}


if __name__ == "__main__":
    import uvicorn
    
    # 注意：Python 3.12 与 uvicorn --reload 有兼容性问题
    # 开发模式建议使用命令行: uv run python -m uvicorn backend_admin.main:app --reload
    uvicorn.run(
        app,
        host=settings.ADMIN_HOST,
        port=settings.ADMIN_PORT,
        reload=False  # 禁用自动重载，使用命令行启动时再加 --reload
    )
