import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from ..config.settings import settings


def create_access_token(
    subject: str | int,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None
) -> str:
    """生成 JWT access token。"""
    if expires_delta is not None and expires_delta.total_seconds() <= 0:
        raise ValueError("expires_delta 必须为正数")

    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))

    payload: dict[str, Any] = {}
    if extra_claims is not None:
        payload.update(extra_claims)

    # 标准声明最后写入，拥有最高优先级，防止被 extra_claims 覆盖
    payload.update({
        "sub": str(subject),
        "iat": now,
        "exp": expire,
        "jti": str(uuid.uuid4()),
        "type": "access"
    })

    return jwt.encode(
        payload,
        settings.SECRET_KEY.get_secret_value(),
        algorithm = settings.ALGORITHM
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """解码并验证 JWT access token。失败时抛出 PyJWT 原生异常。"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms = [settings.ALGORITHM],
            options = {"require": ["exp", "iat", "sub"]}
        )
    except ExpiredSignatureError as exc:
        raise ExpiredSignatureError("Token 已过期") from exc
    except InvalidTokenError as exc:
        raise InvalidTokenError("无效的 Token") from exc

    if payload.get("type") != "access":
        raise InvalidTokenError("无效的 token 类型")

    return payload


