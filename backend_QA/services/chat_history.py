"""
对话历史服务模块。

管理对话历史的存储、检索和上下文管理。
"""

import json
import logging
from typing import List, Dict, Any, Optional
import tiktoken

from backend_common import ChatHistory, UserSession, DatabaseClient, redis_client

logger = logging.getLogger(__name__)

# 数据库客户端
db_client = DatabaseClient()

# Redis key 前缀
REDIS_CHAT_HISTORY_PREFIX = "chat_history:"

# Token 限制配置
MAX_CONTEXT_TOKENS = 4000  # 上下文最大 token 数
SUMMARY_TRIGGER_TOKENS = 6000  # 触发 summary 的阈值
SUMMARY_MAX_TOKENS = 1000  # Summary 最大 token 数


class ChatHistoryService:
    """对话历史服务类。"""
    
    def __init__(self):
        self.encoder = tiktoken.encoding_for_model("gpt-3.5-turbo")
    
    def _get_redis_key(self, user_id: int, session_id: str) -> str:
        """获取 Redis key。"""
        return f"{REDIS_CHAT_HISTORY_PREFIX}{user_id}:{session_id}"
    
    def count_tokens(self, text: str) -> int:
        """计算文本的 token 数量。"""
        return len(self.encoder.encode(text))
    
    def count_messages_tokens(self, messages: List[Dict[str, str]]) -> int:
        """计算消息列表的 token 数量。"""
        total = 0
        for msg in messages:
            total += 4  # 每条消息的格式开销
            total += self.count_tokens(msg.get("content", ""))
        return total
    
    async def get_history_from_redis(self, user_id: int, session_id: str, limit: int = 20) -> List[Dict[str, str]]:
        """从 Redis 获取对话历史。"""
        try:
            redis_key = self._get_redis_key(user_id, session_id)
            history_json = await redis_client.client.lrange(redis_key, 0, limit - 1)
            
            messages = []
            for item in reversed(history_json):
                try:
                    data = json.loads(item)
                    # 新格式：直接存储消息列表
                    if "messages" in data:
                        messages.extend(data["messages"])
                    # 旧格式：问答对
                    else:
                        messages.extend([
                            {"role": "user", "content": data.get("question", "")},
                            {"role": "assistant", "content": data.get("answer", "")}
                        ])
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in Redis history: {item}")
                    continue
            
            logger.info(f"Retrieved {len(messages)} messages from Redis for user {user_id}, session {session_id}")
            return messages
            
        except Exception as e:
            logger.error(f"Error getting history from Redis: {str(e)}")
            return []
    
    async def save_to_redis(self, user_id: int, session_id: str, user_message: str, assistant_message: str, 
                           model: str = "", tokens_used: int = 0):
        """保存对话到 Redis。"""
        try:
            redis_key = self._get_redis_key(user_id, session_id)
            data = {
                "messages": [
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": assistant_message}
                ],
                "model": model,
                "tokens_used": tokens_used,
            }
            await redis_client.client.lpush(redis_key, json.dumps(data, ensure_ascii=False))
            await redis_client.client.expire(redis_key, 30 * 24 * 3600)
            
            logger.info(f"Saved chat to Redis for user {user_id}, session {session_id}")
            
        except Exception as e:
            logger.error(f"Error saving to Redis: {str(e)}")
    
    def save_message_to_mysql(self, user_id: int, session_id: str, role: str, content: str,
                             model: str = "", tokens_used: int = 0) -> Optional[int]:
        """同步保存单条消息到 MySQL。"""
        db = db_client.get_session()
        try:
            chat_record = ChatHistory(
                user_id=user_id,
                session_id=session_id,
                role=role,
                content=content,
                model=model,
                tokens_used=tokens_used
            )
            db.add(chat_record)
            db.commit()
            db.refresh(chat_record)
            
            logger.info(f"Saved message to MySQL: id={chat_record.id}, user={user_id}, session={session_id}, role={role}")
            return chat_record.id
            
        except Exception as e:
            logger.error(f"Error saving to MySQL: {str(e)}")
            db.rollback()
            return None
        finally:
            db.close()
    
    def save_chat_to_mysql(self, user_id: int, session_id: str, user_message: str, assistant_message: str,
                          model: str = "", tokens_used: int = 0) -> tuple:
        """同步保存问答对到 MySQL，分别存储用户消息和AI消息。"""
        user_id_db = self.save_message_to_mysql(
            user_id=user_id,
            session_id=session_id,
            role=ChatHistory.ROLE_USER,
            content=user_message,
            model=model,
            tokens_used=tokens_used // 2 if tokens_used else 0
        )
        
        assistant_id_db = self.save_message_to_mysql(
            user_id=user_id,
            session_id=session_id,
            role=ChatHistory.ROLE_ASSISTANT,
            content=assistant_message,
            model=model,
            tokens_used=tokens_used // 2 if tokens_used else 0
        )
        
        return user_id_db, assistant_id_db
    
    async def save_chat(self, user_id: int, session_id: str, user_message: str, assistant_message: str,
                       model: str = "", tokens_used: int = 0):
        """保存对话到 MySQL 和 Redis。"""
        import asyncio
        from functools import partial
        loop = asyncio.get_event_loop()
        
        # 确保会话存在，使用用户的第一条消息作为会话名称
        get_or_create = partial(self.get_or_create_session, user_id, session_id, None, user_message)
        await loop.run_in_executor(None, get_or_create)
        
        # 保存到 MySQL
        await loop.run_in_executor(
            None, 
            self.save_chat_to_mysql, 
            user_id, session_id, user_message, assistant_message, model, tokens_used
        )
        
        # 更新会话消息计数
        await loop.run_in_executor(
            None,
            self.update_session_message_count,
            user_id, session_id, 2
        )
        
        # 保存到 Redis
        await self.save_to_redis(user_id, session_id, user_message, assistant_message, model, tokens_used)
    
    def trim_context(self, messages: List[Dict[str, str]], max_tokens: int = MAX_CONTEXT_TOKENS) -> List[Dict[str, str]]:
        """裁剪上下文，使其不超过最大 token 数。"""
        if not messages:
            return []
        
        total_tokens = self.count_messages_tokens(messages)
        
        if total_tokens <= max_tokens:
            return messages
        
        trimmed = messages.copy()
        while trimmed and self.count_messages_tokens(trimmed) > max_tokens:
            if len(trimmed) >= 2:
                trimmed = trimmed[2:]
            else:
                trimmed = []
        
        logger.info(f"Trimmed context: {len(messages)} -> {len(trimmed)} messages")
        return trimmed
    
    async def get_context_with_trim(self, user_id: int, session_id: str, 
                                    max_tokens: int = MAX_CONTEXT_TOKENS) -> List[Dict[str, str]]:
        """获取上下文并进行裁剪。"""
        messages = await self.get_history_from_redis(user_id, session_id)
        return self.trim_context(messages, max_tokens)
    
    def get_history_from_mysql(self, user_id: int, session_id: str, limit: int = 20, 
                               offset: int = 0, role: str = None) -> List[Dict[str, Any]]:
        """从 MySQL 获取对话历史。"""
        db = db_client.get_session()
        try:
            query = db.query(ChatHistory).filter(
                ChatHistory.user_id == user_id,
                ChatHistory.session_id == session_id
            )
            
            # 可选：按角色筛选
            if role:
                query = query.filter(ChatHistory.role == role)
            
            records = query.order_by(
                ChatHistory.created_at.desc()
            ).offset(offset).limit(limit).all()
            
            return [r.to_dict() for r in records]
            
        except Exception as e:
            logger.error(f"Error getting history from MySQL: {str(e)}")
            return []
        finally:
            db.close()
    
    def _generate_session_name(self, first_message: str = None, max_length: int = 50) -> str:
        """
        生成会话名称。
        
        如果提供了第一条消息，使用消息内容作为名称（截取前 max_length 个字符）
        否则使用默认格式：新对话 MM-DD HH:MM
        
        Args:
            first_message: 用户的第一条消息
            max_length: 会话名称最大长度
            
        Returns:
            str: 生成的会话名称
        """
        if first_message:
            # 清理消息内容：去除首尾空格和换行
            cleaned = first_message.strip().replace('\n', ' ').replace('\r', '')
            # 截取前 max_length 个字符
            if len(cleaned) > max_length:
                return cleaned[:max_length] + '...'
            return cleaned
        else:
            from datetime import datetime
            return f"新对话 {datetime.now().strftime('%m-%d %H:%M')}"
    
    def get_or_create_session(self, user_id: int, session_id: str, session_name: str = None, 
                              first_message: str = None) -> UserSession:
        """
        获取或创建会话。
        
        Args:
            user_id: 用户ID
            session_id: 会话ID
            session_name: 指定的会话名称（优先级最高）
            first_message: 用户的第一条消息（用于生成会话名称）
        """
        db = db_client.get_session()
        try:
            session = db.query(UserSession).filter(
                UserSession.user_id == user_id,
                UserSession.session_id == session_id
            ).first()
            
            if not session:
                # 生成会话名称：优先级：session_name > first_message > 默认
                if not session_name:
                    session_name = self._generate_session_name(first_message)
                
                session = UserSession(
                    user_id=user_id,
                    session_id=session_id,
                    session_name=session_name,
                    message_count=0,
                    last_message_at=None
                )
                db.add(session)
                db.commit()
                db.refresh(session)
                logger.info(f"Created new session: {session_id} with name: {session_name} for user {user_id}")
            
            return session
            
        except Exception as e:
            logger.error(f"Error getting or creating session: {str(e)}")
            db.rollback()
            raise
        finally:
            db.close()
    
    def update_session_message_count(self, user_id: int, session_id: str, increment: int = 2):
        """更新会话的消息数量和时间。"""
        from datetime import datetime
        
        db = db_client.get_session()
        try:
            session = db.query(UserSession).filter(
                UserSession.user_id == user_id,
                UserSession.session_id == session_id
            ).first()
            
            if session:
                session.message_count = (session.message_count or 0) + increment
                session.last_message_at = datetime.now()
                db.commit()
                logger.info(f"Updated session {session_id}: message_count={session.message_count}")
            else:
                # 如果会话不存在，创建一个
                self.get_or_create_session(user_id, session_id)
                # 递归调用更新
                self.update_session_message_count(user_id, session_id, increment)
                
        except Exception as e:
            logger.error(f"Error updating session message count: {str(e)}")
            db.rollback()
        finally:
            db.close()
    
    def get_session_list(self, user_id: int, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """获取用户的会话列表（从 user_session 表查询）。"""
        db = db_client.get_session()
        try:
            sessions = db.query(UserSession).filter(
                UserSession.user_id == user_id
            ).order_by(
                UserSession.is_pinned.desc(),
                UserSession.last_message_at.desc()
            ).offset(offset).limit(limit).all()
            
            return [s.to_dict() for s in sessions]
            
        except Exception as e:
            logger.error(f"Error getting session list: {str(e)}")
            return []
        finally:
            db.close()
    
    def update_session_name(self, user_id: int, session_id: str, session_name: str) -> bool:
        """更新会话名称。"""
        db = db_client.get_session()
        try:
            session = db.query(UserSession).filter(
                UserSession.user_id == user_id,
                UserSession.session_id == session_id
            ).first()
            
            if session:
                session.session_name = session_name
                db.commit()
                logger.info(f"Updated session name: {session_id} -> {session_name}")
                return True
            else:
                logger.warning(f"Session not found: {session_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating session name: {str(e)}")
            db.rollback()
            return False
        finally:
            db.close()
    
    def pin_session(self, user_id: int, session_id: str, is_pinned: bool) -> bool:
        """置顶/取消置顶会话。"""
        db = db_client.get_session()
        try:
            session = db.query(UserSession).filter(
                UserSession.user_id == user_id,
                UserSession.session_id == session_id
            ).first()
            
            if session:
                session.is_pinned = 1 if is_pinned else 0
                db.commit()
                logger.info(f"Updated session pin status: {session_id} -> {is_pinned}")
                return True
            else:
                logger.warning(f"Session not found: {session_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error pinning session: {str(e)}")
            db.rollback()
            return False
        finally:
            db.close()
    
    def delete_session(self, user_id: int, session_id: str) -> bool:
        """删除指定会话的所有历史记录。"""
        db = db_client.get_session()
        try:
            # 删除 MySQL 中的聊天记录
            deleted_chats = db.query(ChatHistory).filter(
                ChatHistory.user_id == user_id,
                ChatHistory.session_id == session_id
            ).delete()
            
            # 删除会话记录
            deleted_session = db.query(UserSession).filter(
                UserSession.user_id == user_id,
                UserSession.session_id == session_id
            ).delete()
            
            db.commit()
            logger.info(f"Deleted {deleted_chats} chats and {deleted_session} session from MySQL for user {user_id}, session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting session: {str(e)}")
            db.rollback()
            return False
        finally:
            db.close()


# 全局服务实例
chat_history_service = ChatHistoryService()
