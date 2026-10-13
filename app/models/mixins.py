"""
本模块为项目内的模型提供了混入类，旨在为模型类提供额外的功能和行为。
通过使用这些混入类，开发者可以在不修改原有模型类的情况下，
轻松地扩展其功能，从而提高代码的可重用性和可维护性。

比如: 为所有表模型提供共享的 created_at 和 updated_at 字段
"""

from datetime import datetime, timezone
from typing import cast

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel

# ──────────────────────────────────────────────────────────────
# 模块元数据（遵循 FastAPI 元数据规范格式）
# ──────────────────────────────────────────────────────────────

METADATA: dict = {
    "title": "Mirosh Timestamp Mixin",
    "summary": "为 SQLModel 模型提供统一的时间戳字段（created_at 和 updated_at）",
    "description":  """
    定义 TimestampMixin, 为项目所有表模型提供共享的时间戳字段。

    ## 设计约定
    - **时区统一**：所有时间使用 UTC（timezone-aware），通过 `_utcnow()` 生成。
    - **created_at**：写入时自动填充，之后不再变化（`nullable=False`）。
    - **updated_at**：由 SQLAlchemy 的 `onupdate` 在每次 UPDATE 时自动刷新，
      业务代码无需手动维护；首次创建时为 `NULL`。

      ## 实现要点
    - 使用 `sa_column_kwargs` 而非直接传 `sa_column`，
      确保每个继承者获得独立的 Column 实例。
    - 通过 `sa_type` 显式指定 `DateTime(timezone=True)`。
    """,
    "version": "0.1.0",
    "contact": {
        "name": "Paul",
        "url": "https://paul-nebula.online",
        "email": "paulken731@gmail.com",
    },
    "license_info": {
        "name": "MIT",
        "identifier": "MIT",  # SPDX 标识符（OpenAPI 3.1.0 / FastAPI ≥ 0.99.0）
    },
}

__version__ = METADATA["version"]  # 供 __version__ 协议使用
__all__ = ["TimestampMixin", "METADATA", "_utcnow"]


# ──────────────────────────────────────────────────────────────
# 时间工具函数
# ──────────────────────────────────────────────────────────────

def _utcnow() -> datetime:
    """
    获取当前 UTC 时间（带时区信息）。

    Returns:
        datetime: 当前 UTC 时间，类型为 `datetime`，并带有时区信息。
    """
    return datetime.now(timezone.utc)


# ──────────────────────────────────────────────────────────────
# TimestampMixin
# ──────────────────────────────────────────────────────────────

class TimestampMixin(SQLModel):
    """
     用法:
        class User(TimestampMixin, SQLModel, table=True):
            id: int = Field(default=None, primary_key=True)
            name: str

    元数据说明:
    - `__abstract__ = True`：声明为抽象模型，SQLModel 不会为 Mixin
      本身创建表，字段传递给子类。
    - `model_config`：遵循 FastAPI 元数据规范，
      为 Swagger UI / ReDoc 提供 JSON Schema 示例。
    """

    __abstract__  =  True  # 声明为抽象模型，SQLModel 不会为 Mixin 本身创建表

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "created_at": "2026-10-12T12:00:00+00:00",
                    "updated_at": "2026-10-12T12:30:00+00:00",
                }
            ]
        }
    }

    created_at: datetime = Field(
        default_factory=_utcnow,
        sa_type=cast(type, DateTime(timezone=True)),
        sa_column_kwargs={
            "nullable": False,
            "comment": "创建时间（UTC）",
        },
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_type=cast(type, DateTime(timezone=True)),
        sa_column_kwargs={
            "nullable": True,
            "onupdate": _utcnow,
            "comment": "最后更新时间（UTC），首次创建时为 NULL",
        },
    )