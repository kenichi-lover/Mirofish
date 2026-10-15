"""认证服务模块 (Authentication Service)

身份生命周期：注册（register）→ 登录校验（authenticate）。
管理员后台开户见 admin_service.py，与本模块职责分离。
"""

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.user import User
from ..utils.security import DUMMY_HASH, hash_password, verify_password
from .user_service import UserService


class AuthService:
    """认证业务：用户自助注册与登录凭据校验。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def register(self, username: str, email: str, password: str) -> User:
        """用户自助注册。用户名/邮箱冲突抛 HTTPException(409)。"""
        user = User(
            username=username.strip().lower(),
            email=email.strip().lower(),
            hashed_password=hash_password(password),
            # 注意：不接收 is_superuser 参数，自助注册永远是普通用户
            is_superuser=False,
        )
        self.session.add(user)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username or email already registered",
            ) from exc
        return user

    async def authenticate(self, username: str, password: str) -> User:
        """登录凭据校验：统一哈希比较防时序攻击。"""
        user = await UserService(self.session).get_by_username(username)

        hashed = user.hashed_password if user else DUMMY_HASH
        password_ok = verify_password(password, hashed)

        if user is None or not password_ok:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is inactive",
            )
        return user

