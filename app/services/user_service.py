import logging
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..models.user import User
from ..schemas.user_schema import UserUpdate
from ..utils.security import hash_password

logger = logging.getLogger(__name__)

# 普通用户可修改的字段（不含密码，密码走独立逻辑）
_USER_UPDATABLE_FIELDS = frozenset({"username", "email", "full_name"})


class UserService:
    """普通用户服务层：仅允许用户操作自身数据"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ──────────────── 查询操作 ────────────────

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_username(self, username: str) -> User | None:
        result = await self.session.execute(
            select(User).where(func.lower(User.username) == func.lower(username.strip()))
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(User).where(func.lower(User.email) == email.strip().lower())
        )
        return result.scalar_one_or_none()

    # ──────────────── 写入操作 ────────────────

    async def register(self, username: str, email: str, password: str) -> User:
        """用户自行注册"""
        user = User(
            username=username.strip(),
            email=email.strip().lower(),
            hashed_password=hash_password(password),
        )
        self.session.add(user)
        try:
            await self.session.flush()
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            logger.warning("注册冲突: username=%s, email=%s", username, email)
            raise ValueError("用户名或邮箱已存在") from exc
        logger.info("用户注册成功: id=%s", user.id)
        return user

    async def update_profile(self, user: User, data: UserUpdate) -> User:
        """用户修改自己的资料（含密码）"""
        update_data = data.model_dump(exclude_unset=True)

        # 密码单独哈希处理
        if "password" in update_data:
            user.hashed_password = hash_password(update_data.pop("password"))

        # 白名单字段直接赋值
        for field, value in update_data.items():
            if field in _USER_UPDATABLE_FIELDS:
                setattr(user, field, value)

        await self.session.flush()
        await self.session.commit()
        logger.info("用户资料已更新: user_id=%s", user.id)
        return user

    async def update_avatar_url(self, user: User, avatar_url: str) -> None:
        """用户修改自己的头像"""
        user.avatar_url = avatar_url
        await self.session.flush()
        await self.session.commit()
        logger.info("用户头像已更新: user_id=%s", user.id)
