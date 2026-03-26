"""
用户认证模块。

提供用户注册、登录和 JWT 认证功能。
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel, Field

from backend_common import User, DatabaseClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])
db_client = DatabaseClient()

# JWT 配置
SECRET_KEY = "your-secret-key-change-in-production"  # 生产环境请更换
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

# HTTP Bearer 认证
security = HTTPBearer(auto_error=False)


class UserRegisterRequest(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    email: Optional[str] = Field(None, description="邮箱（可选）")
    nickname: Optional[str] = Field(None, description="昵称（可选）")


class UserLoginRequest(BaseModel):
    """用户登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    username: str
    email: Optional[str]
    nickname: Optional[str]
    avatar: Optional[str]
    is_admin: bool


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        logger.warning(f"Password verification error: {e}")
        return False


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT Token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[int]:
    """解码 JWT Token，返回用户ID"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        return user_id
    except (JWTError, ValueError) as e:
        logger.warning(f"Token decode error: {e}")
        return None


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    """
    获取当前登录用户ID。
    
    用于需要登录的接口。
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭证",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user_id = decode_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return user_id


def get_current_user(user_id: int = Depends(get_current_user_id)) -> User:
    """获取当前登录用户对象"""
    db = db_client.get_session()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在"
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户已被禁用"
            )
        return user
    finally:
        db.close()


@router.post("/register", response_model=TokenResponse)
async def register(request: UserRegisterRequest):
    """
    用户注册。
    
    注册成功后自动登录，返回 JWT Token。
    """
    db = db_client.get_session()
    try:
        # 检查用户名是否已存在
        existing_user = db.query(User).filter(
            User.username == request.username
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在"
            )
        
        # 检查邮箱是否已存在
        if request.email:
            existing_email = db.query(User).filter(
                User.email == request.email
            ).first()
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="邮箱已被注册"
                )
        
        # 创建新用户
        user = User(
            username=request.username,
            email=request.email,
            password_hash=get_password_hash(request.password),
            nickname=request.nickname or request.username
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        logger.info(f"User registered: {user.username} (ID: {user.id})")
        
        # 生成 Token
        token = create_access_token(user.id)
        
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_DAYS * 24 * 3600,
            user=user.to_dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注册失败"
        )
    finally:
        db.close()


@router.post("/login", response_model=TokenResponse)
async def login(request: UserLoginRequest):
    """
    用户登录。
    
    验证用户名密码，返回 JWT Token。
    """
    db = db_client.get_session()
    try:
        # 查找用户
        user = db.query(User).filter(
            User.username == request.username
        ).first()
        
        if not user or not verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户已被禁用"
            )
        
        # 更新最后登录时间
        user.last_login_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"User logged in: {user.username} (ID: {user.id})")
        
        # 生成 Token
        token = create_access_token(user.id)
        
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_DAYS * 24 * 3600,
            user=user.to_dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录失败"
        )
    finally:
        db.close()


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    获取当前登录用户信息。
    """
    return UserResponse(**current_user.to_dict())


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """
    用户登出。
    
    前端应清除 Token。
    """
    logger.info(f"User logged out: {current_user.username} (ID: {current_user.id})")
    return {"message": "登出成功"}
