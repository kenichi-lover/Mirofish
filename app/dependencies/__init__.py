from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

# ⭐ 直接复用你现有的 get_session
from ..config.database import get_session

# 全局类型别名，路由层只需写 session: DbSession
DbSession = Annotated[AsyncSession, Depends(get_session)]

