from sqlmodel import Field, SQLModel
from .mixins import TimestampMixin

class User(TimestampMixin,SQLModel, table=True):
    '''用户模型类，继承自 SQLModel，表示数据库中的用户表。'''
    __tablename__: str = "users"

    id: int | None = Field(
        default=None,
        primary_key=True,
    )

    username: str = Field(
        index=True,
        unique=True,
        max_length=50,
        min_length=3,
    )
    email: str = Field(
        index=True,
        unique=True,
        max_length=100,
    )

    # 排除敏感信息，避免在序列化时泄露
    # exclude=True → model_dump() 序列化时自动跳过该字段
    hashed_password: str = Field(max_length=255, exclude=True)

    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    avatar_url: str | None = Field(default=None, max_length=500)



