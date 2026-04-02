from __future__ import annotations

import re

_CANONICAL_GREETINGS = {
    "hi",
    "hello",
    "hey",
    "hiya",
    "yo",
    "sup",
    "good morning",
    "good afternoon",
    "good evening",
    "how are you",
    "how are you doing",
    "whats up",
    "what's up",
}


def _normalize(query: str) -> str:
    normalized = query.strip().lower()
    normalized = re.sub(r"[!?.,]+", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def is_greeting(query: str) -> bool:
    normalized = _normalize(query)
    if not normalized:
        return True
    if normalized in _CANONICAL_GREETINGS:
        return True
    if len(normalized) < 12 and normalized in {"hi", "hello", "hey", "yo", "sup"}:
        return True
    return normalized.startswith(("hi ", "hello ", "hey "))
