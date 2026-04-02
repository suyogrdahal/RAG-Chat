from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChatLogOut(BaseModel):
    id: UUID
    session_id: str | None = None
    query_text: str
    response_text: str
    confidence: float | None = None
    sources: list[dict] = Field(default_factory=list)
    created_at: datetime


class ChatLogListResponse(BaseModel):
    items: list[ChatLogOut]
    limit: int
    offset: int
    total: int
