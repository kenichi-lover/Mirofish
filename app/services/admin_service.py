import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..models.user import User
from ..schemas.user_schema import AdminUserUpdate
from ..utils.security import hash_password

logger = logging.getLogger(__name__)

# 管理员可修改的字段（包含管理权限字段）
_ADMIN_UPDATABLE_FIELDS = frozenset({
    "username", "email", "full_name", "is_active", "is_superuser",
})


class AdminService:
    """管理员服务层：管理所有用户"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ──────────────── 查询操作 ────────────────

    async def get_user(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def get_list(self, skip: int = 0, limit: int = 20) -> list[User]:
        result = await self.session.execute(
            select(User).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    # ──────────────── 写入操作 ────────────────

    async def create_user(self, username: str, email: str, password: str,
                          is_superuser: bool = False) -> User:
        """管理员创建用户（可指定超管身份）"""
        user = User(
            username=username.strip(),
            email=email.strip().lower(),
            hashed_password=hash_password(password),
            is_superuser=is_superuser,
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.commit()
        logger.info("管理员创建用户: id=%s", user.id)
        return user

    async def update_user(self, user: User, data: AdminUserUpdate) -> User:
        """管理员修改任意用户（含权限字段和密码）"""
        update_data = data.model_dump(exclude_unset=True)

        if "password" in update_data:
            user.hashed_password = hash_password(update_data.pop("password"))

        for field, value in update_data.items():
            if field in _ADMIN_UPDATABLE_FIELDS:
                setattr(user, field, value)

        await self.session.flush()
        await self.session.commit()
        logger.info("管理员更新用户: user_id=%s", user.id)
        return user

    async def deactivate_user(self, user: User) -> None:
        """管理员禁用用户"""
        user.is_active = False
        await self.session.flush()
        await self.session.commit()
        logger.info("管理员禁用用户: user_id=%s", user.id)

    async def activate_user(self, user: User) -> None:
        """管理员激活用户"""
        user.is_active = True
        await self.session.flush()
        await self.session.commit()
        logger.info("管理员激活用户: user_id=%s", user.id)
