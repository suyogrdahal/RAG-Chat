from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import re

from pypdf import PdfReader


class ParseError(Exception):
    pass


@dataclass
class ParsedText:
    text: str
    page_count: int | None


def _normalize_text(value: str) -> str:
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = re.split(r"\n\s*\n+", value)
    normalized_paragraphs: list[str] = []
    for paragraph in paragraphs:
        cleaned = re.sub(r"[ \t\f\v]+", " ", paragraph)
        cleaned = re.sub(r"\n+", " ", cleaned)
        cleaned = cleaned.strip()
        if cleaned:
            normalized_paragraphs.append(cleaned)
    return "\n\n".join(normalized_paragraphs)


def parse_pdf(data: bytes) -> ParsedText:
    try:
        reader = PdfReader(BytesIO(data))
        pages: list[str] = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        text = _normalize_text("\n\n".join(pages))
        return ParsedText(text=text, page_count=len(reader.pages))
    except Exception as exc:
        raise ParseError("Unable to parse PDF") from exc


def parse_txt(data: bytes) -> ParsedText:
    candidates = ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "cp1252", "latin-1")
    decoded: str | None = None
    for encoding in candidates:
        try:
            decoded = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if decoded is None:
        decoded = data.decode("utf-8", errors="replace")
    return ParsedText(text=_normalize_text(decoded), page_count=None)
