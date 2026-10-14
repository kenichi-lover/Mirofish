from datetime import datetime

from pydantic import EmailStr, Field
from sqlmodel import SQLModel


# ═══════════════════════════════════════════════════
# 基础字段
# ═══════════════════════════════════════════════════

class UserBase(SQLModel):
    """用户核心标识字段，作为创建与公开信息的基类。"""

    username: str = Field(
        default=...,
        min_length=3,
        max_length=50,
        title="用户名",
        description="唯一登录凭证，仅允许字母、数字和下划线",
        examples=["paul_dev"],
        pattern=r"^[a-zA-Z0-9_]+$",
    )
    email: EmailStr = Field(
        default=...,
        title="电子邮箱",
        description="用于账号验证、通知及密码重置",
        examples=["paul@example.com"],
    )


# ═══════════════════════════════════════════════════
# 请求体（Request）
# ═══════════════════════════════════════════════════

class UserCreate(UserBase):
    """注册新用户时提交的完整信息。"""

    password: str = Field(
        default=...,
        min_length=8,
        max_length=128,
        title="密码",
        description="明文传输，服务端将自动进行 bcrypt 哈希处理",
        examples=["MyS3cur3P@ss!"],
    )
    full_name: str | None = Field(
        default=None,
        max_length=100,
        title="真实姓名",
        description="可选，用于后台审计或个性化展示",
        examples=["Paul Chen"],
    )


class UserUpdate(SQLModel):
    """PATCH 式局部更新，所有字段均为可选。未传递的字段不会被修改。"""

    username: str | None = Field(
        default=None,
        min_length=3,
        max_length=50,
        title="用户名",
        description="新的唯一用户名",
        examples=["paul_new"],
        pattern=r"^[a-zA-Z0-9_]+$",
    )
    email: EmailStr | None = Field(
        default=None,
        title="电子邮箱",
        description="新的邮箱地址，可能需要重新验证",
        examples=["new_paul@example.com"],
    )
    full_name: str | None = Field(
        default=None,
        max_length=100,
        title="真实姓名",
        examples=["Paul New Chen"],
    )
    is_active: bool | None = Field(
        default=None,
        title="账号状态",
        description="设为 false 可立即禁止该用户登录",
    )
    is_superuser: bool | None = Field(
        default=None,
        title="超级管理员权限",
        description="授予或撤销系统最高权限，请谨慎操作",
    )


class UserPasswordUpdate(SQLModel):
    """当前用户自助修改密码，需验证旧密码。"""

    old_password: str = Field(
        default=...,
        min_length=8,
        title="当前密码",
        description="用于身份校验的原始密码",
        examples=["OldP@ssw0rd"],
    )
    new_password: str = Field(
        default=...,
        min_length=8,
        max_length=128,
        title="新密码",
        description="替换后的新密码，建议包含大小写字母、数字及特殊字符",
        examples=["NewS3cur3P@ss!"],
    )


class AdminPasswordReset(SQLModel):
    """管理员强制重置指定用户密码，无需提供旧密码。"""

    new_password: str = Field(
        default=...,
        min_length=8,
        max_length=128,
        title="新密码",
        description="管理员为用户设置的新明文密码",
        examples=["AdminR3s3t!2026"],
    )


class UserLogin(SQLModel):
    """用户登录认证请求。"""

    username: str = Field(
        default=...,
        min_length=3,
        max_length=50,
        title="用户名",
        description="注册时设置的用户名",
        examples=["paul_dev"],
    )
    password: str = Field(
        default=...,
        min_length=8,
        max_length=128,
        title="密码",
        description="账号对应的明文密码",
        examples=["MyS3cur3P@ss!"],
    )


# ═══════════════════════════════════════════════════
# 响应体（Response）
# ═══════════════════════════════════════════════════

class MessageResponse(SQLModel):
    """通用操作结果消息。"""

    message: str = Field(
        default=...,
        title="提示消息",
        description="人类可读的操作结果描述",
        examples=["操作成功"],
    )


class AvatarResponse(SQLModel):
    """头像上传成功后的响应。"""

    success: bool = Field(
        default=True,
        title="是否成功",
        description="固定为 true，失败时接口会返回 HTTP 错误码而非此结构",
    )
    avatar_url: str = Field(
        default=...,
        title="头像链接",
        description="上传成功后生成的可访问 URL",
        examples=["https://cdn.example.com/avatars/paul_dev_20261012.webp"],
    )


class UserPublic(UserBase):
    """对外暴露的用户公开信息，已过滤敏感字段。可直接作为 response_model 使用。"""

    id: int = Field(
        default=...,
        title="用户ID",
        description="数据库自增主键",
        examples=[1],
    )
    is_active: bool = Field(
        default=...,
        title="账号状态",
        description="true 表示账号正常可用",
        examples=[True],
    )
    is_superuser: bool = Field(
        default=...,
        title="超级管理员",
        description="true 表示拥有系统最高权限",
        examples=[False],
    )
    created_at: datetime = Field(
        default=...,
        title="创建时间",
        description="账号注册时间 (ISO 8601)",
        examples=["2026-10-12T21:30:00+08:00"],
    )
    updated_at: datetime = Field(
        default=...,
        title="更新时间",
        description="资料最后修改时间 (ISO 8601)",
        examples=["2026-10-12T21:30:00+08:00"],
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "username": "paul_dev",
                    "email": "paul@example.com",
                    "is_active": True,
                    "is_superuser": False,
                    "created_at": "2026-10-12T21:30:00+08:00",
                    "updated_at": "2026-10-12T21:30:00+08:00",
                }
            ]
        },
    }


class TokenResponse(SQLModel):
    """JWT 认证成功响应。"""

    access_token: str = Field(
        default=...,
        title="访问令牌",
        description="用于后续 API 鉴权的 JWT Token",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    token_type: str = Field(
        default="bearer",
        title="令牌类型",
        description="固定为 bearer，遵循 OAuth 2.0 规范",
        examples=["bearer"],
    )
