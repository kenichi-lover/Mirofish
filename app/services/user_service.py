import logging
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..models.user import User
from ..schemas.user_schema import UserUpdate
from ..utils.security import hash_password

logger = logging.getLogger(__name__)

# 允许通过 update_user 修改的字段白名单
_USER_UPDATABLE_FIELDS = frozenset({"username", "email", "is_active", "is_superuser"})


class UserService:
    """用户服务层：整合 CRUD 与业务逻辑"""
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # ──────────────── 查询操作（只读，无事务副作用） ────────────────

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

    async def get_list(self, skip: int = 0, limit: int = 20) -> list[User]:
        result = await self.session.execute(select(User).offset(skip).limit(limit))
        return list(result.scalars().all())


    # ──────────────── 写入操作（统一事务控制） ────────────────

    async def create_user(self, username: str, email: str, password: str) -> User:
        user = User(
            username = username.strip(),
            email = email.strip().lower(),
            hashed_password = hash_password(password)
        )
        self.session.add(user)

        try:
            await self.session.flush()
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            logger.warning("创建用户冲突: username=%s, email=%s", username, email)
            raise ValueError("用户名或邮箱已存在") from exc

        logger.info("用户创建成功: id=%s", user.id)
        return user

    async def update_user(self, user: User, data: UserUpdate) -> User:
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field in _USER_UPDATABLE_FIELDS:
                setattr(user, field, value)
        await self.session.flush()
        await self.session.commit()
        logger.info("用户信息已更新: user_id=%s", user.id)
        return user

    async def deactivate_user(self, user: User) -> None:
        user.is_active = False
        await self.session.flush()
        await self.session.commit()
        logger.info("用户已禁用: user_id=%s", user.id)

    async def update_avatar_url(self, user: User, avatar_url: str) -> None:
        user.avatar_url = avatar_url
        await self.session.flush()
        await self.session.commit()
        logger.info("用户头像已更新: user_id=%s", user.id)




