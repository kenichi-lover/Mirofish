"""认证路由 (Authentication Router)

注册、登录、登出接口。业务逻辑在 services/auth_service.py，
Cookie 操作在 utils/auth.py，本文件只做请求编排：
调 Service → 翻译 ValueError → 签发/清除凭据。

服务层异常契约：
- 数据冲突 → ValueError（此处翻译为 409）
- 认证失败 → HTTPException(401/403)，Service 直接抛，无需翻译
"""

from fastapi import APIRouter, Request, Response, status

from ...dependencies import DbSession
from ...schemas.user_schema import TokenResponse, UserCreate, UserLogin
from ...services.auth_service import AuthService
from ...utils.auth import clear_auth_cookie, set_auth_cookie
from ...utils.jwt import create_access_token
from ...utils.limiter import limiter

router: APIRouter = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="用户注册",
)
@limiter.limit("5/minute")
async def register(
    request: Request,            # slowapi 必需
    response: Response,
    data: UserCreate,
    session: DbSession,
) -> TokenResponse:
    """自助注册，成功后自动登录。

    Service 强制 is_superuser=False；用户名/邮箱冲突返回 409。
    """
    try:
        user = await AuthService(session).register(
            username=data.username,
            email=data.email,
            password=data.password,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    access_token = create_access_token(subject=str(user.id))
    set_auth_cookie(response, access_token)
    return TokenResponse(access_token=access_token, token_type="bearer")


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="用户登录",
)
@limiter.limit("10/minute")
async def login(
    request: Request,
    response: Response,
    data: UserLogin,
    session: DbSession,
) -> TokenResponse:
    """校验凭据，签发 JWT 并写入 HttpOnly Cookie。

    凭据错误由 Service 直接抛 HTTPException(401/403)，此处不翻译。
    """
    user = await AuthService(session).authenticate(
        username=data.username,
        password=data.password,
    )
    access_token = create_access_token(subject=str(user.id))
    set_auth_cookie(response, access_token)
    return TokenResponse(access_token=access_token, token_type="bearer")


@router.post("/logout", summary="用户登出")
async def logout(response: Response) -> dict[str, str]:
    """清除认证 Cookie。

    无状态 JWT 无法服务端作废，登出本质是客户端丢弃凭据；
    若需强制失效，需引入 token 黑名单或改用短期 token + refresh。
    """
    clear_auth_cookie(response)
    return {"message": "Logged out"}

