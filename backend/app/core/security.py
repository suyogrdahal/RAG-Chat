from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return _pwd_context.verify(plain, hashed)


def create_access_token(data: dict[str, Any], expires_minutes: int | None = None) -> str:
    """Create a signed JWT access token with exp and iat claims."""
    settings = get_settings()
    to_encode: dict[str, Any] = data.copy()

    for key in ("sub", "org_id"):
        if key in to_encode and to_encode[key] is not None:
            to_encode[key] = str(to_encode[key])

    now = datetime.now(timezone.utc)
    expire_minutes = (
        expires_minutes
        if expires_minutes is not None
        else settings.access_ttl_min
    )
    expire = now + timedelta(minutes=expire_minutes)
    to_encode.update(
        {
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
        }
    )

    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token."""
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def create_refresh_token_value() -> str:
    """Create a cryptographically secure random refresh token value."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(token_value: str) -> str:
    """Hash refresh token value with a configured pepper."""
    settings = get_settings()
    payload = f"{settings.refresh_token_pepper}:{token_value}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def verify_refresh_token(token_value: str, token_hash: str) -> bool:
    """Verify raw refresh token against stored hash in constant time."""
    return hmac.compare_digest(hash_refresh_token(token_value), token_hash)
