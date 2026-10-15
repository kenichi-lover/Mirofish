"""认证路由 (Authentication Router)

注册、登录、登出接口。业务逻辑在 services/auth_service.py，
Cookie 操作在 utils/auth.py，本文件只做请求编排。
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
    """自助注册；冲突由 Service 抛 409，成功后自动登录。"""
    user = await AuthService(session).register(
        username=data.username,
        email=data.email,
        password=data.password,
    )
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
    """校验凭据，签发 JWT 并写入 HttpOnly Cookie。"""
    user = await AuthService(session).authenticate(
        username=data.username,
        password=data.password,
    )
    access_token = create_access_token(subject=str(user.id))
    set_auth_cookie(response, access_token)
    return TokenResponse(access_token=access_token, token_type="bearer")


@router.post("/logout", summary="用户登出")
async def logout(response: Response) -> dict[str, str]:
    """清除认证 Cookie。"""
    clear_auth_cookie(response)
    return {"message": "Logged out"}

