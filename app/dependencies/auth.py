"""
认证与权限依赖模块 (Authentication & Authorization Dependencies)

本模块提供 FastAPI 路由层所需的认证与权限校验依赖项，支持 API 强制认证、
SSR 页面可选认证以及管理员权限校验。所有依赖均为无状态函数，通过 FastAPI
的 Depends 机制注入。

主要依赖项:
    - get_current_user: 强制认证（适用于 API 路由，失败抛出 401）
    - resolve_user_from_cookie: 可选认证（适用于 SSR/Jinja2 页面，失败静默返回 None）
    - require_superuser: 管理员权限校验（失败抛出 403）

类型别名 (Type Aliases):
    - CurrentUser: 强制认证用户类型别名，消除路由层样板代码
    - OptionalUser: 可选认证用户类型别名
    - SuperUser: 管理员用户类型别名
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from . import DbSession
from ..models.user import User
from ..services.user_service import UserService
from ..utils.jwt import decode_access_token


security = HTTPBearer(auto_error=False)


def _credentials_exception() -> HTTPException:
    """工厂函数：避免重复构造，且每次创建新实例防止响应头污染。"""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def _get_user_from_token(
    session: DbSession,
    token: str | None,
) -> User | None:
    """底层纯函数：从 token 解析用户。无效返回 None，过期单独抛出。"""
    if not token:
        return None

    try:
        payload = decode_access_token(token)
    except ExpiredSignatureError:
        raise  # ⭐ 向上透传，供调用方区分"过期"和"无效"
    except InvalidTokenError:
        return None

    try:
        sub = payload.get("sub")
        if sub is None:
            return None
        user_id = int(sub)
    except (TypeError, ValueError):
        return None

    svc = UserService(session)
    user = await svc.get_by_id(user_id)
    if user is None or not user.is_active:
        return None

    return user


# ⭐ 强制认证（API 路由用）
async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    session: DbSession,
) -> User:
    token = credentials.credentials if credentials else request.cookies.get("access_token")

    try:
        user = await _get_user_from_token(session, token)
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user is None:
        raise _credentials_exception()

    return user


# ⭐ 可选认证（SSR/Jinja2 页面用）
async def resolve_user_from_cookie(
    request: Request,
    session: DbSession,
) -> User | None:
    """仅从 Cookie 尝试解析，失败静默返回 None。"""
    token = request.cookies.get("access_token")
    try:
        return await _get_user_from_token(session, token)
    except ExpiredSignatureError:
        return None  # 页面场景下过期也视为未登录


# ⭐ 权限校验
async def require_superuser(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# ⭐ 类型别名（取自新建议，消除路由层样板代码）
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(resolve_user_from_cookie)]
SuperUser = Annotated[User, Depends(require_superuser)]
