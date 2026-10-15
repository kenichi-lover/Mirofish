"""用户自助路由 (User Self-Service Router)

已登录用户对自身资料的管理接口。业务逻辑在 services/user_service.py，
本文件只做请求编排：调 Service → 翻译 ValueError → 组装响应。

与 routers/api/auth.py 的分工：
- auth.py     管身份的进出（注册/登录/登出，无 CurrentUser）
- user.py     管登录后的自我操作（改资料/改密码/注销，必须 CurrentUser）
- user_admin.py 管对别人的操作（管理员治理，必须 SuperUser）
"""

from fastapi import APIRouter, HTTPException, Response, status

from ...dependencies import CurrentUser, DbSession
from ...models.user import User
from ...schemas.user_schema import (
    PasswordChangeRequest,
    UserRead,
    UserUpdate,
)
from ...services.user_service import UserService
from ...utils.auth import clear_auth_cookie

router: APIRouter = APIRouter(prefix="/users", tags=["users"])


# ──────────────── 查询 ────────────────


@router.get("/me", response_model=UserRead, summary="获取当前用户信息")
async def get_me(
    current_user: CurrentUser,
) -> User:
    """返回当前登录用户的基本资料（密码哈希等敏感字段由 schema 排除）。"""
    return current_user


# ──────────────── 资料更新 ────────────────


@router.patch("/me", response_model=UserRead, summary="更新个人资料")
async def update_me(
    data: UserUpdate,
    current_user: CurrentUser,
    session: DbSession,
) -> User:
    """修改自己的资料（用户名/邮箱/姓名）。用户名或邮箱冲突返回 409。"""
    try:
        user = await UserService(session).update_profile(current_user, data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    return user


# ──────────────── 修改密码 ────────────────


@router.patch("/me/password", summary="修改密码")
async def change_password(
    data: PasswordChangeRequest,
    response: Response,
    current_user: CurrentUser,
    session: DbSession,
) -> dict[str, str]:
    """修改密码：必须验证当前密码，防止会话被劫持后直接重置。

    改密成功后清除认证 Cookie，强制用新密码重新登录
    （无状态 JWT 无法作废已签发 token，清 Cookie 是当下最有效的失效手段）。
    """
    try:
        await UserService(session).change_password(
            current_user, data.old_password, data.new_password,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    clear_auth_cookie(response)
    return {"message": "Password updated, please login again"}


# ──────────────── 注销账号 ────────────────


@router.delete("/me", summary="注销账号")
async def delete_me(
    data: DeleteAccountRequest,
    response: Response,
    current_user: CurrentUser,
    session: DbSession,
) -> dict[str, str]:
    """注销自己的账号：高危操作，必须验证登录密码确认是本人。

    账号被禁用并匿名化后，后续请求因 `_get_user_from_token`
    查不到有效用户而自然 401，无需额外拉黑 token。
    """
    try:
        await UserService(session).delete_account(current_user, data.password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    clear_auth_cookie(response)
    return {"message": "Account deleted"}

