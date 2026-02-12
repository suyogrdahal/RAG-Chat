from __future__ import annotations

import logging
import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import log_event

logger = logging.getLogger("app.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id

        endpoint = request.scope.get("endpoint")
        endpoint_name = (
            getattr(endpoint, "__name__", None)
            or getattr(request.scope.get("route"), "path", None)
            or request.url.path
        )

        log_event(
            logger,
            logging.INFO,
            "http_request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            endpoint_name=endpoint_name,
            status_code=response.status_code,
            latency_ms=latency_ms,
            user_id=getattr(request.state, "user_id", None),
            org_id=getattr(request.state, "org_id", None),
        )
        return response
