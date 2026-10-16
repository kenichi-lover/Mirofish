from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import DbSession
from app.services import auth_service
from app.services.auth_service import AuthError   # 按你项目实际异常名调整
from app.utils.auth import set_auth_cookie        # 你项目已有的 Cookie 工具

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _form(request: Request, mode: str, error: str = "", **ctx):
    """渲染表单片段（登录/注册共用）"""
    return templates.TemplateResponse(
        "partials/auth_form.html",
        {"request": request, "mode": mode, "error": error, **ctx},
    )


@router.get("/auth/form/{mode}")
async def auth_form(mode: str, request: Request):
    if mode not in ("login", "register"):
        raise HTTPException(404)
    return _form(request, mode)


@router.post("/auth/login")
async def login_htmx(request: Request,
                     username: str = Form(...), password: str = Form(...),
                     db: AsyncSession = Depends(DbSession)):
    try:
        user = await auth_service.authenticate(db, username, password)
    except AuthError as e:
        # 失败：返回 200 + 带错误提示的表单片段
        # （htmx 默认不交换 4xx 响应体，所以错误必须以 200 返回）
        return _form(request, "login", error=str(e), username=username)

    response = Response(status_code=204)
    set_auth_cookie(response, user)
    # 成功：让 htmx 整页跳转，浏览器重新拿到「已登录」状态的 base.html
    response.headers["HX-Redirect"] = "/"
    return response


@router.post("/auth/register")
async def register_htmx(request: Request,
                        username: str = Form(...), email: str = Form(...),
                        password: str = Form(...),
                        db: AsyncSession = Depends(DbSession)):
    try:
        user = await auth_service.register(db, username, email, password)
    except AuthError as e:
        return _form(request, "register", error=str(e),
                     username=username, email=email)

    response = Response(status_code=204)
    set_auth_cookie(response, user)
    response.headers["HX-Redirect"] = "/"
    return response


@router.post("/auth/logout")
async def logout_htmx():
    response = Response(status_code=204)
    response.delete_cookie("access_token")  # 按你项目的 Cookie 名
    response.headers["HX-Redirect"] = "/"
    return response

