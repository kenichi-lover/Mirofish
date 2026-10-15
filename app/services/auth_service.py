"""认证服务模块 (Authentication Service)

身份生命周期：注册（register）→ 登录校验（authenticate）。
用户创建统一复用 AdminService.create_user（唯一创建入口），
管理员后台开户与本模块共享同一套归一化/哈希/冲突处理逻辑。
"""

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import User
from ..utils.security import DUMMY_HASH, verify_password
from .admin_service import AdminService
from .user_service import UserService


class AuthService:
    """认证业务：用户自助注册与登录凭据校验。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def register(self, username: str, email: str, password: str) -> User:
        """用户自助注册。

        复用 AdminService.create_user 作为唯一创建入口，
        并硬编码 is_superuser=False —— 自助注册永远是普通用户，
        不存在参数注入提权的可能。
        用户名/邮箱冲突抛 ValueError（由路由层映射为 409）。
        """
        return await AdminService(self.session).create_user(
            username=username,
            email=email,
            password=password,
            is_superuser=False,  # 硬编码，不透传任何外部参数
        )

    async def authenticate(self, username: str, password: str) -> User:
        """登录凭据校验：统一哈希比较防时序攻击。

        登录失败属于协议级认证响应（401/403），故保留 HTTPException；
        数据冲突类错误则统一抛 ValueError，见各 create/update 方法。
        """
        user = await UserService(self.session).get_by_username(username)

        hashed = user.hashed_password if user else DUMMY_HASH
        password_ok = verify_password(password, hashed)

        if user is None or not password_ok:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is inactive",
            )
        return user

