import asyncio
import importlib
from uuid import uuid4

import pytest
from fastapi import HTTPException

rate_limit_module = importlib.import_module("app.api.deps.rate_limit")


class _MockRedis:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.expirations: dict[str, int] = {}
        self.incr_calls = 0

    async def incr(self, key: str) -> int:
        self.incr_calls += 1
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key: str, ttl: int) -> bool:
        self.expirations[key] = ttl
        return True


@pytest.fixture
def fixed_time(monkeypatch):
    monkeypatch.setattr(rate_limit_module.time, "time", lambda: 1_700_000_000)


@pytest.fixture
def mock_redis(monkeypatch):
    redis = _MockRedis()
    monkeypatch.setattr(rate_limit_module, "get_redis_client", lambda: redis)
    return redis


def test_30_allowed(mock_redis, fixed_time) -> None:
    org_id = uuid4()
    for _ in range(30):
        asyncio.run(rate_limit_module.rate_limit(org_id))
    assert mock_redis.incr_calls == 30


def test_31st_rejected(mock_redis, fixed_time) -> None:
    org_id = uuid4()
    for _ in range(30):
        asyncio.run(rate_limit_module.rate_limit(org_id))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(rate_limit_module.rate_limit(org_id))
    assert exc.value.status_code == 429


def test_separate_orgs_isolated(mock_redis, fixed_time) -> None:
    org_a = uuid4()
    org_b = uuid4()

    for _ in range(30):
        asyncio.run(rate_limit_module.rate_limit(org_a))
    for _ in range(29):
        asyncio.run(rate_limit_module.rate_limit(org_b))

    with pytest.raises(HTTPException):
        asyncio.run(rate_limit_module.rate_limit(org_a))

    # org_b still has budget because it's a separate keyspace.
    asyncio.run(rate_limit_module.rate_limit(org_b))


def test_mock_redis_used(mock_redis, fixed_time) -> None:
    org_id = uuid4()
    asyncio.run(rate_limit_module.rate_limit(org_id))
    assert mock_redis.incr_calls == 1
    assert len(mock_redis.expirations) == 1
