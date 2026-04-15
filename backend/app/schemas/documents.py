from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    doc_id: UUID
    status: str


class DocumentStatusResponse(BaseModel):
    doc_id: UUID
    status: str
    error_message: str | None
    total_chunks: int
    embedded_chunks: int


class DocumentOut(BaseModel):
    id: UUID
    filename: str
    content_type: str
    size_bytes: int
    status: str
    error_message: str | None
    total_chunks: int
    embedded_chunks: int
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    items: list[DocumentOut]
    limit: int
    offset: int
    total: int


class DocumentMutationResponse(BaseModel):
    success: bool
    detail: str | None = None
    status: str | None = None


class DashboardSummaryResponse(BaseModel):
    total_documents: int
    documents_completed: int
    documents_processing: int
    documents_failed: int
    total_tokens_used: int
    total_chunks: int
