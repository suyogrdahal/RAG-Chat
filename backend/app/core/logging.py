from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

JWT_LIKE_RE = re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$")
REDACT_KEYS = {"password", "token", "access_token", "refresh_token", "authorization"}
COOKIE_REDACT_KEYS = {"access_token", "refresh_token", "token"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        if hasattr(record, "payload") and isinstance(record.payload, dict):
            payload.update(record.payload)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    root = logging.getLogger()
    if root.handlers:
        for handler in root.handlers:
            handler.setFormatter(JsonFormatter())
        root.setLevel(logging.INFO)
        return

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def hash_email(email: str) -> str:
    return sha256(email.strip().lower().encode("utf-8")).hexdigest()


def redact(value: Any, key: str | None = None) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            k_lower = str(k).lower()
            if k_lower in REDACT_KEYS:
                out[k] = "REDACTED"
            elif k_lower == "cookie" and isinstance(v, str):
                out[k] = _redact_cookie_header(v)
            else:
                out[k] = redact(v, key=k_lower)
        return out

    if isinstance(value, list):
        return [redact(v, key=key) for v in value]

    if isinstance(value, tuple):
        return tuple(redact(v, key=key) for v in value)

    if isinstance(value, str):
        if key in REDACT_KEYS:
            return "REDACTED"
        if JWT_LIKE_RE.match(value):
            return "REDACTED_JWT"
        return value

    return value


def _redact_cookie_header(cookie_value: str) -> str:
    parts = [p.strip() for p in cookie_value.split(";") if p.strip()]
    redacted: list[str] = []
    for part in parts:
        if "=" not in part:
            redacted.append(part)
            continue
        k, v = part.split("=", 1)
        if k.strip().lower() in COOKIE_REDACT_KEYS:
            redacted.append(f"{k}=REDACTED")
        elif JWT_LIKE_RE.match(v.strip()):
            redacted.append(f"{k}=REDACTED_JWT")
        else:
            redacted.append(f"{k}={v}")
    return "; ".join(redacted)


def log_event(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    payload = redact({"event": event, **fields})
    logger.log(level, event, extra={"payload": payload})
