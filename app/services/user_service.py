"""
承载用户资料的查询与更新逻辑。注册/登录等认证业务
本模块仅管理用户自身数据。
"""

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..models.user import User
from ..schemas.user_schema import UserUpdate
from ..utils.security import hash_password, verify_password

logger = logging.getLogger(__name__)

# 普通用户可修改的字段（不含密码，密码走独立逻辑）
_USER_UPDATABLE_FIELDS = frozenset({"username", "email", "full_name"})


class UserService:
    """普通用户服务层：仅允许用户操作自身数据"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ──────────────── 查询操作 ────────────────

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_username(self, username: str) -> User | None:
        """按用户名查询（写入时已统一小写，此处无需 func.lower）。"""
        normalized = (username or "").strip().lower()
        if not normalized:
            return None
        result = await self.session.execute(
            select(User).where(User.username == normalized)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        normalized = (email or "").strip().lower()
        if not normalized:
            return None
        result = await self.session.execute(
            select(User).where(User.email == normalized)
        )
        return result.scalar_one_or_none()

    # ──────────────── 写入操作 ────────────────

    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: str | None = None,
        is_superuser: bool = False,
    ) -> User:
        """创建新用户。"""
        user = User(
            username=username.strip().lower(),
            email=email.strip().lower(),
            full_name=full_name.strip() if full_name and full_name.strip() else None,
            hashed_password=hash_password(password),
            is_superuser=is_superuser,
        )
        self.session.add(user)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ValueError("用户名或邮箱已存在") from exc

        logger.info("创建用户: user_id=%s", user.id)
        return user

    async def update_profile(self, user: User, data: UserUpdate) -> User:
        """用户修改自己的资料。"""
        update_data = data.model_dump(exclude_unset=True)

        if "username" in update_data:
            update_data["username"] = update_data["username"].strip().lower()

        if "email" in update_data:
            update_data["email"] = update_data["email"].strip().lower()

        for field, value in update_data.items():
            if field in _USER_UPDATABLE_FIELDS:
                setattr(user, field, value)

        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            logger.warning(
                "资料更新冲突: user_id=%s, username=%s, email=%s",
                user.id,
                user.username,
                user.email,
            )
            raise ValueError("用户名或邮箱已被占用") from exc

        logger.info("用户资料已更新: user_id=%s", user.id)
        return user

    async def change_password(
        self,
        user: User,
        old_password: str,
        new_password: str,
    ) -> None:
        """修改密码：必须验证当前密码，防止会话被劫持后直接重置。"""
        if not verify_password(old_password, user.hashed_password):
            raise ValueError("当前密码不正确")

        user.hashed_password = hash_password(new_password)
        await self.session.commit()
        logger.info("用户密码已修改: user_id=%s", user.id)

    async def admin_reset_password(self, user: User, new_password: str) -> None:
        """管理员强制重置用户密码。"""
        user.hashed_password = hash_password(new_password)
        await self.session.commit()
        logger.info("管理员已重置密码: user_id=%s", user.id)

    async def update_avatar_url(self, user: User, avatar_url: str) -> None:
        """用户修改自己的头像"""
        user.avatar_url = avatar_url
        await self.session.flush()
        await self.session.commit()
        logger.info("用户头像已更新: user_id=%s", user.id)
