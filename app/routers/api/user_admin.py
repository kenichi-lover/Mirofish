"""管理员用户治理路由 (Admin User Management Router)

管理员对任意用户的管理接口。所有端点要求 SuperUser 依赖
（内部链式调用 get_current_user 完成认证，再校验 is_superuser）。

业务逻辑在 services/admin_service.py，本文件只做请求编排：
调 Service → 翻译 ValueError → 组装响应。

与 routers/api/user.py 的分工：
- user.py       用户操作自己（CurrentUser）
- user_admin.py 管理员操作任意用户（SuperUser）
"""

from fastapi import APIRouter, HTTPException, status

from ...dependencies import DbSession, SuperUser
from ...models.user import User
from ...schemas.user_schema import (
    AdminUserCreate,
    AdminUserUpdate,
    UserRead,
)
from ...services.admin_service import AdminService

router: APIRouter = APIRouter(prefix="/admin/users", tags=["admin"])


# ──────────────── 查询 ────────────────


@router.get("", response_model=list[UserRead], summary="用户列表（分页）")
async def list_users(
    operator: SuperUser,
    session: DbSession,
    skip: int = 0,
    limit: int = 20,
) -> list[User]:
    """分页返回全部用户。limit 上限 100，防止一次拉爆。"""
    limit = min(limit, 100)
    users, _total = await AdminService(session).get_list(skip=skip, limit=limit)
    return users


@router.get("/{user_id}", response_model=UserRead, summary="查询单个用户")
async def get_user(
    user_id: int,
    operator: SuperUser,
    session: DbSession,
) -> User:
    target = await AdminService(session).get_user(user_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return target


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
        )
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

    涉及权限字段变更时，Service 内部做"最后一个超管"保护校验。
    """
    target = await AdminService(session).get_user(user_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    try:
        user = await AdminService(session).update_user(target, data, operator)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    return user


# ──────────────── 禁用 / 激活 ────────────────


@router.post("/{user_id}/deactivate", summary="禁用用户")
async def deactivate_user(
    user_id: int,
    operator: SuperUser,
    session: DbSession,
) -> dict[str, str]:
    """禁用后该用户所有请求在认证依赖处 401（is_active=False 被拦截）。"""
    target = await AdminService(session).get_user(user_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    try:
        await AdminService(session).deactivate_user(target, operator)
    except ValueError as exc:
        # 不能禁用自己 / 不能禁用最后一个可用超管
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    return {"message": "User deactivated"}


@router.post("/{user_id}/activate", summary="激活用户")
async def activate_user(
    user_id: int,
    operator: SuperUser,
    session: DbSession,
) -> dict[str, str]:
    target = await AdminService(session).get_user(user_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    await AdminService(session).activate_user(target)
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
    target = await AdminService(session).get_user(user_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    try:
        await AdminService(session).delete_user(target, operator)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    return {"message": "User deleted"}

