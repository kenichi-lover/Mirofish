from fastapi import Response
from app.config.settings import settings

def set_auth_cookie(response: Response, access_token: str) -> None:
    """
    将 access_token 写入 HttpOnly Cookie。

    注意：这是一个普通辅助函数，不使用 FastAPI 依赖注入。
    配置项直接从 settings 单例中读取。
    """
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True, # JS 无法读取, 防 XSS
        secure=settings.COOKIE_SECURE,  # Https -only
        max_age=settings.ACCESS_TOKEN_EXPIRE_SECONDS,
        path="/",  # 全局可用
        samesite=settings.COOKIE_SAME_SITE  # CSRF 防护
    )


def clear_auth_cookie(response: Response) -> None:
    """
    登出时清除 Cookie
    参数必须与设置时完全一致
    """
    response.delete_cookie(
        key="access_token",
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAME_SITE,
        httponly=True,
        path="/"
    )
