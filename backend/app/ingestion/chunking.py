from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Chunk:
    chunk_index: int
    content: str
    start_char: int
    end_char: int


def _normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _split_paragraph_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    start = 0
    for match in re.finditer(r"\n\s*\n+", text):
        end = match.start()
        if end > start:
            spans.extend(_split_heading_spans(text, start, end))
        start = match.end()
    if start < len(text):
        spans.extend(_split_heading_spans(text, start, len(text)))
    return spans


def _split_heading_spans(text: str, start: int, end: int) -> list[tuple[int, int]]:
    segment = text[start:end]
    lines = segment.split("\n")
    spans: list[tuple[int, int]] = []
    cursor = start
    block_start = cursor
    heading_re = re.compile(r"^\s{0,3}(#{1,6}\s+|[A-Z][A-Z0-9 _-]{3,}:?\s*$)")

    for line in lines:
        line_end = cursor + len(line)
        is_heading = bool(heading_re.match(line))
        if is_heading and block_start < cursor:
            spans.append((block_start, cursor))
            block_start = cursor
        cursor = line_end + 1
    if block_start < end:
        spans.append((block_start, end))
    return spans


def _best_split_index(content: str, max_chars: int) -> int:
    if len(content) <= max_chars:
        return len(content)
    window = content[:max_chars]
    candidates = [
        window.rfind("\n\n"),
        window.rfind("\n"),
        window.rfind(". "),
        window.rfind("! "),
        window.rfind("? "),
        window.rfind("; "),
        window.rfind(", "),
        window.rfind(" "),
    ]
    split_at = max(candidates)
    min_threshold = max_chars // 2
    if split_at < min_threshold:
        split_at = max_chars
    return split_at


def _trim_span(content: str, start: int, end: int) -> tuple[str, int, int]:
    left_trim = len(content) - len(content.lstrip())
    right_trim = len(content) - len(content.rstrip())
    new_start = start + left_trim
    new_end = end - right_trim
    trimmed = content.strip()
    return trimmed, new_start, new_end


def _split_with_overlap(
    text: str,
    start: int,
    end: int,
    max_chars: int,
    overlap: int,
) -> list[tuple[str, int, int]]:
    out: list[tuple[str, int, int]] = []
    cursor = start
    while cursor < end:
        remaining = text[cursor:end]
        if len(remaining) <= max_chars:
            chunk_text, c_start, c_end = _trim_span(remaining, cursor, end)
            if chunk_text:
                out.append((chunk_text, c_start, c_end))
            break

        split_rel = _best_split_index(remaining, max_chars)
        split_abs = cursor + split_rel
        raw = text[cursor:split_abs]
        chunk_text, c_start, c_end = _trim_span(raw, cursor, split_abs)
        if chunk_text:
            out.append((chunk_text, c_start, c_end))

        next_cursor = max(split_abs - overlap, cursor + 1)
        cursor = next_cursor
    return out


def _merge_tiny_chunks(chunks: list[tuple[str, int, int]], min_chars: int) -> list[tuple[str, int, int]]:
    if not chunks:
        return chunks
    merged = list(chunks)
    i = 0
    while i < len(merged):
        content, start, end = merged[i]
        if len(content) >= min_chars or len(merged) == 1:
            i += 1
            continue

        if i > 0:
            p_content, p_start, _ = merged[i - 1]
            merged[i - 1] = (f"{p_content}\n\n{content}", p_start, end)
            del merged[i]
            i -= 1
        elif i + 1 < len(merged):
            n_content, _, n_end = merged[i + 1]
            merged[i + 1] = (f"{content}\n\n{n_content}", start, n_end)
            del merged[i]
        else:
            i += 1
    return merged


def chunk_text(
    text: str,
    max_chars: int = 1000,
    overlap: int = 120,
    min_chars: int = 200,
) -> list[Chunk]:
    normalized = _normalize_text(text)
    if not normalized.strip():
        return []

    spans = _split_paragraph_spans(normalized)
    raw_chunks: list[tuple[str, int, int]] = []
    for start, end in spans:
        if end <= start:
            continue
        raw_chunks.extend(
            _split_with_overlap(
                normalized,
                start,
                end,
                max_chars=max_chars,
                overlap=overlap,
            )
        )

    raw_chunks = _merge_tiny_chunks(raw_chunks, min_chars=min_chars)
    result: list[Chunk] = []
    for idx, (content, start, end) in enumerate(raw_chunks):
        result.append(
            Chunk(
                chunk_index=idx,
                content=content,
                start_char=start,
                end_char=end,
            )
        )
    return result
