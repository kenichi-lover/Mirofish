"""管理员服务模块 (Admin Service)

管理员对任意用户的管理操作，同时承担系统内唯一的用户创建入口
（AuthService.register 亦复用 create_user）。
所有"收回权限"方向的操作（禁用/降权/删除）都带自我保护校验，
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

# 管理员可修改的字段（password 不在其中，单独处理）
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
        """分页查询用户列表，返回 (用户列表, 总数)。

        显式 order_by 保证翻页顺序稳定，避免不同执行计划下
        出现重复或遗漏。
        """
        result = await self.session.execute(
            select(User).order_by(User.id).offset(skip).limit(limit)
        )
        total = await self.session.scalar(select(func.count(User.id)))
        return list(result.scalars().all()), total or 0

    # ──────────────── 内部校验 ────────────────

    async def _count_active_superusers(self) -> int:
        """统计当前可用的（活跃）超管数量。"""
        return await self.session.scalar(
            select(func.count(User.id)).where(
                User.is_superuser.is_(True),
                User.is_active.is_(True),
            )
        ) or 0

    async def _ensure_safe_revoke(
        self,
        target: User,
        operator: User,
        *,
        revoke_active: bool,
        revoke_superuser: bool,
    ) -> None:
        """校验"收回权限"方向的操作不会使系统失去自我修复能力。

        必须在 setattr / delete 之前调用——先改后查会因 autoflush
        把变更刷入事务，导致计数包含目标自身，出现两个恶果：
        1. 降权/禁用最后一个超管时计数被算漏；
        2. 系统中不存在超管时永远无法提升出第一个（bootstrap 死锁）。

        Args:
            target: 被操作的用户（此时尚未被修改，读到的是数据库状态）。
            operator: 执行操作的管理员（来自 CurrentUser）。
            revoke_active: 本次操作是否会收回 target 的活跃状态。
            revoke_superuser: 本次操作是否会收回 target 的超管身份。

        Raises:
            ValueError: 违反自我保护规则。
        """
        # 禁用自己后无法再登录管理，一律禁止（删除同理，见调用方）
        if revoke_active and target.id == operator.id:
            raise ValueError("不能禁用或删除自己的账号")

        # 目标是当前可用的超管，且本次操作会剥夺其可用性：
        # 扣除目标自身后，必须仍剩下至少一个可用超管。
        if (
            target.is_superuser
            and target.is_active
            and (revoke_active or revoke_superuser)
        ):
            if await self._count_active_superusers() <= 1:
                raise ValueError("系统必须保留至少一个可用的超级管理员")

    # ──────────────── 写入操作 ────────────────

    async def create_user(self, username: str, email: str, password: str,
                          is_superuser: bool = False) -> User:
        """创建用户（系统唯一创建入口，AuthService.register 亦复用此方法）。

        管理员可指定超管身份；自助注册方必须显式传 is_superuser=False。
        用户名/邮箱冲突抛 ValueError。
        """
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
        logger.info("创建用户: user_id=%s, is_superuser=%s", user.id, is_superuser)
        return user

    async def update_user(self, user: User, data: AdminUserUpdate,
                          operator: User) -> User:
        """管理员修改任意用户（含权限字段和密码）。冲突抛 ValueError。"""
        update_data = data.model_dump(exclude_unset=True)

        if "username" in update_data:
            update_data["username"] = update_data["username"].strip().lower()
        if "email" in update_data:
            update_data["email"] = update_data["email"].strip().lower()

        # "收回权限"方向的变更，必须在任何 setattr 之前完成校验，
        # 避免变更被 autoflush 污染计数查询（见 _ensure_safe_revoke 文档）。
        # 收回方向之外的操作（提升超管、激活、改密码/资料）不受限制，
        # 从而保证系统在失去全部超管后仍能自我修复。
        revoke_active = update_data.get("is_active") is False and user.is_active
        revoke_superuser = (
            update_data.get("is_superuser") is False and user.is_superuser
        )
        if revoke_active or revoke_superuser:
            await self._ensure_safe_revoke(
                user, operator,
                revoke_active=revoke_active,
                revoke_superuser=revoke_superuser,
            )

        # 校验全部通过后再做任何变更
        # 密码不进入字段白名单，单独处理（有意为之）
        if "password" in update_data:
            user.hashed_password = hash_password(update_data.pop("password"))
        for field, value in update_data.items():
            if field in _ADMIN_UPDATABLE_FIELDS:
                setattr(user, field, value)

        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ValueError("用户名或邮箱已被占用") from exc
        logger.info("管理员更新用户: user_id=%s, operator_id=%s", user.id, operator.id)
        return user

    async def deactivate_user(self, user: User, operator: User) -> None:
        """管理员禁用用户（软删除的第一步）。"""
        await self._ensure_safe_revoke(
            user, operator,
            revoke_active=True,
            revoke_superuser=user.is_superuser,
        )
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
        await self._ensure_safe_revoke(
            user, operator,
            revoke_active=True,
            revoke_superuser=user.is_superuser,
        )
        await self.session.delete(user)
        await self.session.commit()
        logger.info("管理员删除用户: user_id=%s, operator_id=%s", user.id, operator.id)

