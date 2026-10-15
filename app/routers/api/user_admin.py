"""管理员用户治理路由 (Admin User Management Router)

管理员对任意用户的管理接口。所有端点要求 SuperUser 依赖
（内部链式调用 get_current_user 完成认证，再校验 is_superuser）。

业务逻辑在 services/admin_service.py，本文件只做请求编排：
调 Service → 翻译 ValueError → 组装响应。

与相邻路由的分工：
- user.py       用户操作自己（CurrentUser）
- user_admin.py 管理员操作任意用户（SuperUser）

错误状态码约定：Service 抛出的 ValueError（用户名/邮箱冲突、
最后一个超管保护、禁用/删除自己）统一映射为 409。
"""

from fastapi import APIRouter, HTTPException, Query, status

from ...dependencies import DbSession, SuperUser
from ...models.user import User
from ...schemas.user_schema import (
    AdminUserCreate,
    AdminUserUpdate,
    UserRead,
)
from ...services.admin_service import AdminService

router: APIRouter = APIRouter(prefix="/admin/users", tags=["admin"])


# ──────────────── 内部辅助 ────────────────


async def _get_user_or_404(service: AdminService, user_id: int) -> User:
    """按 ID 取用户，不存在则抛 404。收敛原先重复 5 次的查询+判空样板。"""
    target = await service.get_user(user_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return target


# ──────────────── 查询 ────────────────


@router.get("", response_model=list[UserRead], summary="用户列表（分页）")
async def list_users(
    operator: SuperUser,
    session: DbSession,
    skip: int = Query(0, ge=0, description="偏移量"),
    limit: int = Query(20, ge=1, le=100, description="每页数量，上限 100"),
) -> list[User]:
    """分页返回全部用户。

    参数越界由 Query 校验直接返回 422，不做静默修正——
    让调用方明确知道参数不合法。
    """
    users, _total = await AdminService(session).get_list(skip=skip, limit=limit)
    return users


@router.get("/{user_id}", response_model=UserRead, summary="查询单个用户")
async def get_user(
    user_id: int,
    operator: SuperUser,
    session: DbSession,
) -> User:
    return await _get_user_or_404(AdminService(session), user_id)


# ──────────────── 创建 ────────────────


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="创建用户（可指定超管）",
)
async def create_user(
    data: AdminUserCreate,
    operator: SuperUser,
    session: DbSession,
) -> User:
    """管理员后台开户。与 /auth/register 的区别：可指定 is_superuser。"""
    try:
        user = await AdminService(session).create_user(
            username=data.username,
            email=data.email,
            password=data.password,
            is_superuser=data.is_superuser,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return user


# ──────────────── 更新 ────────────────


@router.patch("/{user_id}", response_model=UserRead, summary="修改任意用户")
async def update_user(
    user_id: int,
    data: AdminUserUpdate,
    operator: SuperUser,
    session: DbSession,
) -> User:
    """修改任意用户资料，含权限字段（is_active / is_superuser）与密码重置。

    "收回权限"方向（禁用/降权）的最后一个超管保护由 Service 在
    变更落库前校验，违规返回 409。
    """
    service = AdminService(session)
    target = await _get_user_or_404(service, user_id)
    try:
        user = await service.update_user(target, data, operator)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return user


# ──────────────── 禁用 / 激活 ────────────────


@router.post("/{user_id}/deactivate", summary="禁用用户")
async def deactivate_user(
    user_id: int,
    operator: SuperUser,
    session: DbSession,
) -> dict[str, str]:
    """禁用后该用户所有请求在认证依赖处 401（is_active=False 被拦截）。"""
    service = AdminService(session)
    target = await _get_user_or_404(service, user_id)
    try:
        await service.deactivate_user(target, operator)
    except ValueError as exc:
        # 不能禁用自己 / 不能禁用最后一个可用超管 → 409
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return {"message": "User deactivated"}


@router.post("/{user_id}/activate", summary="激活用户")
async def activate_user(
    user_id: int,
    operator: SuperUser,
    session: DbSession,
) -> dict[str, str]:
    """激活用户。恢复方向无保护约束，故无 ValueError 分支。"""
    service = AdminService(session)
    target = await _get_user_or_404(service, user_id)
    await service.activate_user(target)
    return {"message": "User activated"}


# ──────────────── 删除 ────────────────


@router.delete("/{user_id}", summary="删除用户")
async def delete_user(
    user_id: int,
    operator: SuperUser,
    session: DbSession,
) -> dict[str, str]:
    """硬删除用户。受"最后一个超管"保护约束。

    生产环境若用户已产生关联业务数据，建议改走
    deactivate（软删除）而非物理删除，以维持外键完整性。
    """
    service = AdminService(session)
    target = await _get_user_or_404(service, user_id)
    try:
        await service.delete_user(target, operator)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return {"message": "User deleted"}

