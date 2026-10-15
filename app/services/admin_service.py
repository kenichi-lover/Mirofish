"""管理员服务模块 (Admin Service)

管理员对任意用户的管理操作。所有变更方法都带自我保护校验，
防止系统失去最后一个可用超管。
"""

import logging

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import User
from ..schemas.user_schema import AdminUserUpdate
from ..utils.security import hash_password

logger = logging.getLogger(__name__)

# 管理员可修改的字段（包含管理权限字段）
_ADMIN_UPDATABLE_FIELDS = frozenset({
    "username", "email", "full_name", "is_active", "is_superuser",
})


class AdminService:
    """管理员服务层：管理所有用户。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ──────────────── 查询操作 ────────────────

    async def get_user(self, user_id: int) -> User | None:
        """按 ID 查询任意用户。"""
        return await self.session.get(User, user_id)

    async def get_list(self, skip: int = 0, limit: int = 20) -> tuple[list[User], int]:
        """分页查询用户列表，返回 (用户列表, 总数)。"""
        result = await self.session.execute(select(User).offset(skip).limit(limit))
        total = await self.session.scalar(select(func.count(User.id)))
        return list(result.scalars().all()), total or 0

    # ──────────────── 内部校验 ────────────────

    async def _ensure_last_superuser_safe(self, target: User, operator: User) -> None:
        """防止删除/禁用自己或最后一个超管。

        Args:
            target: 被操作的用户。
            operator: 执行操作的管理员（来自 CurrentUser）。

        Raises:
            ValueError: 违反自我保护规则。
        """
        if target.id == operator.id:
            raise ValueError("不能对自身执行禁用或删除操作")

        if target.is_superuser:
            superuser_count = await self.session.scalar(
                select(func.count(User.id)).where(
                    User.is_superuser.is_(True),
                    User.is_active.is_(True),
                )
            )
            # 目标是超管，且（禁用后/删除后）将不存在其他可用超管
            if (superuser_count or 0) <= 1:
                raise ValueError("系统必须保留至少一个可用的超级管理员")

    # ──────────────── 写入操作 ────────────────

    async def create_user(self, username: str, email: str, password: str,
                          is_superuser: bool = False) -> User:
        """管理员创建用户（可指定超管身份）。冲突抛 ValueError。"""
        user = User(
            username=username.strip().lower(),
            email=email.strip().lower(),
            hashed_password=hash_password(password),
            is_superuser=is_superuser,
        )
        self.session.add(user)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ValueError("用户名或邮箱已存在") from exc
        logger.info("管理员创建用户: id=%s", user.id)
        return user

    async def update_user(self, user: User, data: AdminUserUpdate,
                          operator: User) -> User:
        """管理员修改任意用户（含权限字段和密码）。冲突抛 ValueError。"""
        update_data = data.model_dump(exclude_unset=True)

        if "password" in update_data:
            user.hashed_password = hash_password(update_data.pop("password"))
        if "username" in update_data:
            update_data["username"] = update_data["username"].strip().lower()
        if "email" in update_data:
            update_data["email"] = update_data["email"].strip().lower()

        for field, value in update_data.items():
            if field in _ADMIN_UPDATABLE_FIELDS:
                setattr(user, field, value)

        # 涉及 is_active/is_superuser 变更时做自我保护校验
        if "is_active" in update_data or "is_superuser" in update_data:
            await self._ensure_last_superuser_safe(user, operator)

        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ValueError("用户名或邮箱已被占用") from exc
        logger.info("管理员更新用户: user_id=%s", user.id)
        return user

    async def deactivate_user(self, user: User, operator: User) -> None:
        """管理员禁用用户（软删除的第一步）。"""
        await self._ensure_last_superuser_safe(user, operator)
        user.is_active = False
        await self.session.commit()
        logger.info("管理员禁用用户: user_id=%s, operator_id=%s", user.id, operator.id)

    async def activate_user(self, user: User) -> None:
        """管理员激活用户。"""
        user.is_active = True
        await self.session.commit()
        logger.info("管理员激活用户: user_id=%s", user.id)

    async def delete_user(self, user: User, operator: User) -> None:
        """管理员删除用户（硬删除）。

        生产环境建议改为软删除：is_active=False + 匿名化 PII，
        保留关联业务数据的外键完整性。
        """
        await self._ensure_last_superuser_safe(user, operator)
        await self.session.delete(user)
        await self.session.commit()
        logger.info("管理员删除用户: user_id=%s, operator_id=%s", user.id, operator.id)

