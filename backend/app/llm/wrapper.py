from __future__ import annotations

import logging
import os
import time
from uuid import UUID

import httpx

from app.core.config import get_settings
from app.core.logging import log_event

FALLBACK_ANSWER = "I don't have enough information to answer that."
MAX_LOG_TEXT_LEN = 500

logger = logging.getLogger(__name__)


def _truncate_text(value: str, limit: int = MAX_LOG_TEXT_LEN) -> str:
    if len(value) <= limit:
        return value
    return value[:limit]


def _log_llm_event(
    *,
    request_id: str | None,
    org_id: UUID | str | None,
    user_id: UUID | str | None,
    query: str,
    prompt: str,
    answer: str,
    latency_ms: int,
) -> None:
    log_event(
        logger,
        logging.INFO,
        "llm_response",
        request_id=request_id,
        org_id=str(org_id) if org_id is not None else None,
        user_id=str(user_id) if user_id is not None else None,
        query=query,
        truncated_prompt=_truncate_text(prompt),
        truncated_answer=_truncate_text(answer),
        latency_ms=latency_ms,
    )


def _is_model_not_found_error(message: str | None) -> bool:
    if not message:
        return False
    normalized = message.lower()
    return (
        "model" in normalized
        and ("does not exist" in normalized or "doesn't exist" in normalized or "not found" in normalized or "is not available" in normalized)
    )


def _candidate_models(primary_model: str) -> list[str]:
    candidates = [primary_model, "gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]
    ordered: list[str] = []
    seen: set[str] = set()
    for value in candidates:
        model_name = (value or "").strip()
        if not model_name or model_name in seen:
            continue
        seen.add(model_name)
        ordered.append(model_name)
    return ordered


async def generate_llm_response(
    prompt: str,
    *,
    request_id: str | None = None,
    org_id: UUID | str | None = None,
    user_id: UUID | str | None = None,
    query: str | None = None,
) -> dict:
    started = time.perf_counter()
    settings = get_settings()
    api_key = (os.getenv("OPENAI_API_KEY", settings.openai_api_key) or "").strip()
    primary_model = (os.getenv("OPENAI_MODEL", settings.openai_model) or "").strip()
    timeout_seconds = float(os.getenv("OPENAI_TIMEOUT_SECONDS", str(settings.openai_timeout_seconds)))
    temperature = float(os.getenv("OPENAI_TEMPERATURE", str(settings.openai_temperature)))
    max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", str(settings.openai_max_tokens)))
    api_base = os.getenv("OPENAI_API_BASE", settings.openai_api_base).rstrip("/")
    openai_chat_url = f"{api_base}/chat/completions"
    safe_query = (query if query is not None else prompt).strip()

    if not api_key:
        logger.warning("OPENAI_API_KEY is not configured. Skipping OpenAI request and returning fallback answer.")
        answer = FALLBACK_ANSWER
        latency_ms = int((time.perf_counter() - started) * 1000)
        _log_llm_event(
            request_id=request_id,
            org_id=org_id,
            user_id=user_id,
            query=safe_query,
            prompt=prompt,
            answer=answer,
            latency_ms=latency_ms,
        )
        return {"answer": answer, "usage": {}}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    base_payload = {
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }

    for model in _candidate_models(primary_model):
        payload = dict(base_payload)
        payload["model"] = model

        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(
                    openai_chat_url,
                    headers=headers,
                    json=payload,
                )
            response.raise_for_status()
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if isinstance(content, list):
                answer = "".join(
                    part.get("text", "") for part in content if isinstance(part, dict)
                ).strip()
            else:
                answer = str(content).strip()
            usage = data.get("usage", {}) or {}
            if not answer:
                answer = FALLBACK_ANSWER
            latency_ms = int((time.perf_counter() - started) * 1000)
            _log_llm_event(
                request_id=request_id,
                org_id=org_id,
                user_id=user_id,
                query=safe_query,
                prompt=prompt,
                answer=answer,
                latency_ms=latency_ms,
            )
            return {"answer": answer, "usage": usage}
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            try:
                error_payload = exc.response.json() if exc.response is not None else {}
            except ValueError:
                error_payload = {}
            error_message = (
                error_payload.get("error", {}).get("message")
                if isinstance(error_payload.get("error"), dict)
                else str(error_payload)
            )
            error_code = (
                error_payload.get("error", {}).get("type")
                if isinstance(error_payload.get("error"), dict)
                else None
            )
            if not error_message and exc.response is not None:
                error_message = exc.response.text

            logger.warning(
                "OpenAI request failed",
                extra={
                    "event": "openai_http_error",
                    "status_code": status_code,
                    "model": model,
                    "error_code": error_code,
                    "error_message": error_message,
                },
            )

            if status_code == 400 and _is_model_not_found_error(error_message):
                continue

            answer = FALLBACK_ANSWER
            latency_ms = int((time.perf_counter() - started) * 1000)
            _log_llm_event(
                request_id=request_id,
                org_id=org_id,
                user_id=user_id,
                query=safe_query,
                prompt=prompt,
                answer=answer,
                latency_ms=latency_ms,
            )
            return {"answer": answer, "usage": {}}
        except (httpx.TimeoutException, ValueError, KeyError, IndexError):
            answer = FALLBACK_ANSWER
            latency_ms = int((time.perf_counter() - started) * 1000)
            _log_llm_event(
                request_id=request_id,
                org_id=org_id,
                user_id=user_id,
                query=safe_query,
                prompt=prompt,
                answer=answer,
                latency_ms=latency_ms,
            )
            return {"answer": answer, "usage": {}}

    logger.error(
        "OpenAI request failed for all configured models",
        extra={
            "event": "openai_model_fallback_exhausted",
            "models": ",".join(_candidate_models(primary_model)),
        },
    )
    answer = FALLBACK_ANSWER
    latency_ms = int((time.perf_counter() - started) * 1000)
    _log_llm_event(
        request_id=request_id,
        org_id=org_id,
        user_id=user_id,
        query=safe_query,
        prompt=prompt,
        answer=answer,
        latency_ms=latency_ms,
    )
    return {"answer": answer, "usage": {}}