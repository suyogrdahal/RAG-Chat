from __future__ import annotations

import time
from uuid import UUID

from fastapi import Depends, HTTPException, status
from redis.asyncio import Redis

from app.api.deps.auth import require_org
from app.core.config import get_settings
from app.schemas.auth_context import AuthContext

RATE_LIMIT_PER_MINUTE = 30
_redis_client: Redis | None = None


def get_redis_client() -> Redis:
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


async def rate_limit(org_id: UUID) -> None:
    await _rate_limit_with_key(
        key=f"rag:rate:{org_id}",
        limit=RATE_LIMIT_PER_MINUTE,
    )


async def _rate_limit_with_key(*, key: str, limit: int) -> None:
    minute_timestamp = int(time.time() // 60)
    rate_key = f"{key}:{minute_timestamp}"
    redis = get_redis_client()

    count = await redis.incr(rate_key)
    if count == 1:
        await redis.expire(rate_key, 120)

    if int(count) > int(limit):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
        )


async def rate_limit_public(
    *,
    org_id: UUID,
    ip_address: str,
    org_limit: int,
    ip_limit: int,
) -> None:
    await _rate_limit_with_key(
        key=f"rag:rate:public:org:{org_id}",
        limit=org_limit,
    )
    await _rate_limit_with_key(
        key=f"rag:rate:public:ip:{ip_address}",
        limit=ip_limit,
    )


async def enforce_rate_limit(context: AuthContext = Depends(require_org)) -> None:
    await rate_limit(context.org_id)
