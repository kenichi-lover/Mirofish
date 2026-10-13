# 运行时可变配置（环境变量：DB 连接、密钥、LLM key）
from typing import Literal
from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- 环境 ---
    APP_ENV: Literal["development", "production", "testing"] = "development"

    DATABASE_URL: str = "postgresql+asyncpg:///daiyuanyuan_db"
    SECRET_KEY: SecretStr
    DEBUG: bool = False

    # --- JWT ---
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7   # 7 天
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 天
    ALGORITHM: str = "HS256"

    @property
    def ACCESS_TOKEN_EXPIRE_SECONDS(self) -> int:
        return self.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # ✅ 分钟转秒


    # --- 头像 ---
    MAX_AVATAR_SIZE: int = 5 * 1024 * 1024  # 5 MB
    ALLOWED_AVATAR_EXTENSIONS: list[str] = ["jpg", "jpeg", "png", "gif", "webp"]

    # --- Cookie ---
    COOKIE_SECURE: bool = True
    COOKIE_SAME_SITE: Literal["strict", "lax", "none"] = "lax"

    # ---  数据库连接池 ---
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_RECYCLE: int = 3600  # 连接池中连接的最大存活时间（秒）

    # --- 日志 ---
    LOG_FORMAT: str = "console"  # 开发环境使用 console，生产环境使用 json

    @model_validator(mode="after")
    def check_production_settings(self):
        if self.APP_ENV == "production":
            if len(self.SECRET_KEY.get_secret_value()) < 32:
                raise ValueError("生产环境 SECRET_KEY 长度必须至少 32 位")
            if self.DEBUG:
                raise ValueError("生产环境不允许开启 DEBUG")
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()  # type: ignore

