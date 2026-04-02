from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings
from app.db.models import Document, DocumentStatus
from app.repositories.documents_repository import DocumentsRepository
from app.schemas.documents import DocumentOut, DocumentListResponse

ALLOWED_CONTENT_TYPES = {"application/pdf", "text/plain"}


class DocumentsService:
    def __init__(self, repo: DocumentsRepository) -> None:
        self.repo = repo
        self.settings = get_settings()

    async def upload(
        self,
        org_id: UUID,
        upload_file: UploadFile,
    ) -> Document:
        content_type = upload_file.content_type or ""
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Unsupported content type",
            )

        max_bytes = int(self.settings.max_upload_mb) * 1024 * 1024
        content = bytearray()
        while True:
            chunk = await upload_file.read(1024 * 1024)
            if not chunk:
                break
            content.extend(chunk)
            if len(content) > max_bytes:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="File too large",
                )

        doc = Document(
            org_id=org_id,
            filename=upload_file.filename or "uploaded",
            content_type=content_type,
            size_bytes=len(content),
            status=DocumentStatus.QUEUED,
            error_message=None,
        )
        self.repo.create(doc)
        self.repo.commit()
        self.repo.refresh(doc)

        path = Path("data") / str(org_id) / str(doc.id) / "original"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(bytes(content))
        return doc

    def get_status(self, org_id: UUID, doc_id: UUID) -> tuple[Document, int, int]:
        doc = self.repo.get_by_id(org_id, doc_id)
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        total_chunks, embedded_chunks = self.repo.get_chunk_counts(org_id, doc_id)
        return doc, total_chunks, embedded_chunks

    def list_documents(
        self,
        org_id: UUID,
        status_filter: str | None,
        limit: int,
        offset: int,
        sort: str,
    ) -> DocumentListResponse:
        items, total = self.repo.list_documents(org_id, status_filter, limit, offset, sort)
        payload = []
        for doc in items:
            total_chunks, embedded_chunks = self.repo.get_chunk_counts(org_id, doc.id)
            payload.append(
                DocumentOut(
                    id=doc.id,
                    filename=doc.filename,
                    content_type=doc.content_type,
                    size_bytes=doc.size_bytes,
                    status=doc.status.value,
                    error_message=doc.error_message,
                    total_chunks=total_chunks,
                    embedded_chunks=embedded_chunks,
                    created_at=doc.created_at,
                    updated_at=doc.updated_at,
                )
            )
        return DocumentListResponse(items=payload, limit=limit, offset=offset, total=total)

    def get_document(self, org_id: UUID, doc_id: UUID) -> DocumentOut:
        doc = self.repo.get_by_id(org_id, doc_id)
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        total_chunks, embedded_chunks = self.repo.get_chunk_counts(org_id, doc.id)
        return DocumentOut(
            id=doc.id,
            filename=doc.filename,
            content_type=doc.content_type,
            size_bytes=doc.size_bytes,
            status=doc.status.value,
            error_message=doc.error_message,
            total_chunks=total_chunks,
            embedded_chunks=embedded_chunks,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )
