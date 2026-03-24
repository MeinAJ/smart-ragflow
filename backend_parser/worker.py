#!/usr/bin/env python3
"""
Parser Worker - 后台解析服务。

从数据库读取待解析任务并执行文档解析。
"""

from __future__ import annotations

import os
import sys
import time
import logging
import asyncio
from datetime import datetime
from typing import TYPE_CHECKING

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 延迟导入，避免循环依赖
if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class DatabaseClient:
    """数据库客户端。"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # 延迟导入 SQLAlchemy
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from backend_common import settings
        
        self.engine = create_engine(
            settings.DATABASE_URL,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True
        )
        self.SessionLocal = sessionmaker(
            autocommit=False, 
            autoflush=False, 
            bind=self.engine
        )
        self._initialized = True
    
    def get_session(self) -> 'Session':
        """获取数据库会话。"""
        return self.SessionLocal()


class ParseWorker:
    """
    文档解析 Worker。
    
    轮询数据库获取待解析任务并执行解析。
    """
    
    def __init__(self):
        self.db_client = DatabaseClient()
        self.running = False
        self.poll_interval = 5  # 轮询间隔（秒）
        self.parse_service = None
    
    async def initialize(self):
        """初始化服务。"""
        logger.info("Initializing ParseWorker...")
        
        # 延迟导入解析服务
        from backend_parser.services import DocumentParseService
        self.parse_service = DocumentParseService()
        await self.parse_service.initialize()
        
        logger.info("ParseWorker initialized.")
    
    async def shutdown(self):
        """关闭服务。"""
        logger.info("Shutting down ParseWorker...")
        if self.parse_service:
            await self.parse_service.close()
        logger.info("ParseWorker shut down.")
    
    def get_waiting_task(self):
        """
        获取一个待解析任务。
        
        MySQL 不支持 SKIP LOCKED，使用普通查询 + 乐观锁方式处理并发。
        
        Returns:
            ParseTask: 任务对象，如果没有则返回 None
        """
        # 延迟导入模型 - 从 backend_common 导入
        from backend_common import ParseTask
        
        db = self.db_client.get_session()
        try:
            # 先查询一个待解析任务（不加锁）
            task = db.query(ParseTask) \
                     .filter(ParseTask.status == ParseTask.STATUS_WAITING) \
                     .order_by(ParseTask.created_at) \
                     .first()
            
            if not task:
                return None
            
            # 使用乐观锁更新状态
            # 只有状态仍为 WAITING 时才更新
            from sqlalchemy import update
            result = db.execute(
                update(ParseTask)
                .where(
                    ParseTask.id == task.id,
                    ParseTask.status == ParseTask.STATUS_WAITING
                )
                .values(
                    status=ParseTask.STATUS_PARSING,
                    started_at=datetime.now()
                )
            )
            
            if result.rowcount == 0:
                # 任务已被其他 worker 获取
                db.rollback()
                return None
            
            db.commit()
            
            # 重新获取更新后的任务
            db.refresh(task)
            logger.info(f"Acquired task: {task.id}, doc: {task.doc_id}")
            return task
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to get waiting task: {e}")
            return None
        finally:
            db.close()
    
    async def update_task_status(
        self,
        task_id: str,
        status: int,
        error_message: str = None
    ):
        """
        更新任务状态。
        
        Args:
            task_id: 任务ID
            status: 新状态
            error_message: 错误信息
        """
        # 延迟导入 - 从 backend_common 导入
        from backend_common import ParseTask, Document, opensearch_store
        
        db = self.db_client.get_session()
        try:
            task = db.query(ParseTask).filter(ParseTask.id == task_id).first()
            if not task:
                return
            
            task.status = status
            if error_message:
                task.error_message = error_message
            
            if status in [ParseTask.STATUS_COMPLETED, ParseTask.STATUS_FAILED]:
                task.completed_at = datetime.now()
            
            # 同步更新文档状态
            doc = db.query(Document).filter(Document.id == task.doc_id).first()
            if doc:
                if status == ParseTask.STATUS_COMPLETED:
                    doc.parse_status = Document.STATUS_COMPLETED
                    doc.parse_message = "解析完成"
                    # 尝试获取分块数量（使用 await）
                    try:
                        chunks = await opensearch_store.search_by_doc_id(task.doc_id)
                        doc.chunk_count = len(chunks)
                    except Exception as e:
                        logger.warning(f"Failed to get chunk count: {e}")
                        
                elif status == ParseTask.STATUS_FAILED:
                    doc.parse_status = Document.STATUS_FAILED
                    doc.parse_message = error_message
                elif status == ParseTask.STATUS_PARSING:
                    doc.parse_status = Document.STATUS_PARSING
                    doc.parse_message = "正在解析..."
            
            db.commit()
            logger.info(f"Updated task {task_id} status to {status}")
            
        finally:
            db.close()
    
    async def process_task(self, task):
        """
        处理单个任务。
        
        Args:
            task: 解析任务
        """
        logger.info(f"Processing task: {task.id}, file: {task.file_name}")
        
        try:
            # 调用解析服务
            result = await self.parse_service.process(
                file_url=task.file_url,
                doc_id=task.doc_id,
                skip_embedding=False,
                skip_indexing=False,
                force_update=True
            )
            
            if result.success:
                logger.info(f"Task {task.id} completed successfully, chunks: {len(result.chunks)}")
                await self.update_task_status(
                    task_id=task.id,
                    status=self._get_task_status('completed')
                )
            else:
                error_msg = result.error_message or "解析失败"
                logger.error(f"Task {task.id} failed: {error_msg}")
                await self.update_task_status(
                    task_id=task.id,
                    status=self._get_task_status('failed'),
                    error_message=error_msg
                )
                
        except Exception as e:
            logger.exception(f"Task {task.id} error: {e}")
            await self.update_task_status(
                task_id=task.id,
                status=self._get_task_status('failed'),
                error_message=str(e)
            )
    
    def _get_task_status(self, status_name: str) -> int:
        """获取任务状态码。"""
        from backend_common import ParseTask
        status_map = {
            'pending': ParseTask.STATUS_PENDING,
            'waiting': ParseTask.STATUS_WAITING,
            'parsing': ParseTask.STATUS_PARSING,
            'failed': ParseTask.STATUS_FAILED,
            'completed': ParseTask.STATUS_COMPLETED
        }
        return status_map.get(status_name, ParseTask.STATUS_FAILED)
    
    async def run_once(self):
        """执行一次轮询和处理。"""
        task = self.get_waiting_task()
        
        if task:
            await self.process_task(task)
            return True
        
        return False
    
    async def run(self):
        """主循环。"""
        await self.initialize()
        self.running = True
        
        logger.info(f"ParseWorker started, poll_interval={self.poll_interval}s")
        
        try:
            while self.running:
                try:
                    processed = await self.run_once()
                    
                    if not processed:
                        # 没有任务，等待轮询间隔
                        await asyncio.sleep(self.poll_interval)
                    # 如果处理了任务，立即检查下一个
                    
                except Exception as e:
                    logger.exception(f"Worker error: {e}")
                    await asyncio.sleep(self.poll_interval)
                    
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            await self.shutdown()
    
    def stop(self):
        """停止 Worker。"""
        self.running = False
        logger.info("ParseWorker stopping...")


async def main():
    """主入口。"""
    worker = ParseWorker()
    
    try:
        await worker.run()
    except Exception as e:
        logger.exception(f"Worker failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
