# 数据库连接配置
from collections.abc import  AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from app.config.settings import settings

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL, 
    echo=settings.DEBUG, 
    future=True,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_recycle=settings.DATABASE_POOL_RECYCLE,
    pool_pre_ping=True,  # 检查连接是否有效
)

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,    # 绑定到已创建的数据库引擎
    expire_on_commit=False,    # 提交事务后不让对象过期
    class_=AsyncSession,    # 显式指定创建的会话类为异步会话
)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()  # 回滚事务
            raise e

async def create_db_and_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(
            SQLModel.metadata.create_all
            )  # 创建所有表
        
        
