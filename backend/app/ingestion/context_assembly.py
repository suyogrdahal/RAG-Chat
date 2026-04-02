from __future__ import annotations


def _estimate_tokens(text: str) -> float:
    return len(text) / 4.0


def assemble_context(chunks: list[dict], max_tokens: int) -> str:
    if not chunks or max_tokens <= 0:
        return ""

    selected: list[str] = []
    current = ""
    for chunk in chunks:
        content = str(chunk.get("content", ""))
        if not content:
            continue

        candidate = content if not selected else f"{current}\n\n{content}"
        if _estimate_tokens(candidate) > float(max_tokens):
            break
        selected.append(content)
        current = candidate

    return current
