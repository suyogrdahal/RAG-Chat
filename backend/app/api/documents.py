from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps.auth import require_org
from app.core.config import get_settings
from app.core.logging import log_event
from app.db.models import DocumentStatus
from app.db.session import SessionLocal, get_db
from app.ingestion.chunking import chunk_text
from app.ingestion.embeddings import embed_texts
from app.ingestion.parsers import parse_pdf, parse_txt
from app.ingestion.pipeline import build_chunk_rows
from app.repositories.documents_repository import DocumentsRepository
from app.repositories.vector_repository import VectorRepository
from app.schemas.auth_context import AuthContext
from app.schemas.documents import DocumentListResponse, DocumentOut, DocumentStatusResponse, DocumentUploadResponse
from app.services.documents_service import DocumentsService

router = APIRouter(prefix="/documents", tags=["documents"])
logger = logging.getLogger("app.documents")
SAFE_ERROR_MESSAGES = {
    "Document not found",
    "Original file not found",
    "Unsupported content type",
    "Extracted text exceeds allowed size",
    "Unable to parse PDF",
}


def get_documents_service(db: Session = Depends(get_db)) -> DocumentsService:
    return DocumentsService(DocumentsRepository(db))


def _run_ingestion_pipeline(doc_id: UUID, org_id: UUID, repo: DocumentsRepository) -> None:
    settings = get_settings()
    doc = repo.get_by_id(org_id, doc_id)
    if doc is None:
        raise RuntimeError("Document not found")

    path = Path("data") / str(org_id) / str(doc_id) / "original"
    if not path.exists():
        raise RuntimeError("Original file not found")

    data = path.read_bytes()
    if doc.content_type == "application/pdf":
        parsed = parse_pdf(data)
    elif doc.content_type == "text/plain":
        parsed = parse_txt(data)
    else:
        raise RuntimeError("Unsupported content type")

    if len(parsed.text) > int(settings.max_text_chars):
        raise RuntimeError("Extracted text exceeds allowed size")

    chunks = chunk_text(parsed.text)
    if not chunks:
        return
    embeddings = embed_texts([chunk.content for chunk in chunks])
    rows = build_chunk_rows(
        org_id=org_id,
        doc_id=doc_id,
        text=parsed.text,
        embeddings=embeddings,
    )
    vector_repo = VectorRepository(repo.db)
    vector_repo.insert_chunks_with_embeddings(org_id=org_id, doc_id=doc_id, rows=rows)


def _short_safe_error_message(exc: Exception) -> str:
    message = str(exc).strip().replace("\n", " ")
    if message in SAFE_ERROR_MESSAGES:
        return message
    return "Ingestion failed"


def _ingest_document_background(doc_id: UUID, org_id: UUID, request_id: str | None = None) -> None:
    session = SessionLocal()
    repo = DocumentsRepository(session)
    try:
        doc = repo.get_by_id(org_id, doc_id)
        if doc is None:
            return
        doc.status = DocumentStatus.PROCESSING
        repo.commit()

        _run_ingestion_pipeline(doc_id, org_id, repo)

        doc.status = DocumentStatus.SUCCEEDED
        doc.error_message = None
        repo.commit()
    except Exception as exc:
        repo.rollback()
        doc = repo.get_by_id(org_id, doc_id)
        safe_message = _short_safe_error_message(exc)
        if doc is not None:
            doc.status = DocumentStatus.FAILED
            doc.error_message = safe_message
            repo.commit()
        log_event(
            logger,
            logging.WARNING,
            "ingestion_failed",
            request_id=request_id,
            doc_id=str(doc_id),
            org_id=str(org_id),
            exception_type=type(exc).__name__,
            message=safe_message,
        )
    finally:
        session.close()


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_200_OK)
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    context: AuthContext = Depends(require_org),
    service: DocumentsService = Depends(get_documents_service),
) -> DocumentUploadResponse:
    settings = get_settings()
    max_bytes = int(settings.max_upload_mb) * 1024 * 1024
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > max_bytes + 64 * 1024:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="File too large",
                )
        except ValueError:
            pass
    doc = await service.upload(context.org_id, file)
    request_id = getattr(request.state, "request_id", None)
    background_tasks.add_task(_ingest_document_background, doc.id, context.org_id, request_id)
    return DocumentUploadResponse(doc_id=doc.id, status=doc.status.value)


@router.get("", response_model=DocumentListResponse, status_code=status.HTTP_200_OK)
def list_documents(
    status: str | None = None,
    limit: int = 25,
    offset: int = 0,
    sort: str = "-created_at",
    context: AuthContext = Depends(require_org),
    service: DocumentsService = Depends(get_documents_service),
) -> DocumentListResponse:
    if limit < 1:
        limit = 1
    if limit > 100:
        limit = 100
    if offset < 0:
        offset = 0
    if sort not in {"created_at", "-created_at"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid sort")
    if status and status not in {s.value for s in DocumentStatus}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid status",
        )
    return service.list_documents(context.org_id, status, limit, offset, sort)


@router.get("/{doc_id}", response_model=DocumentOut, status_code=status.HTTP_200_OK)
def get_document(
    doc_id: UUID,
    context: AuthContext = Depends(require_org),
    service: DocumentsService = Depends(get_documents_service),
) -> DocumentOut:
    return service.get_document(context.org_id, doc_id)


@router.get("/{doc_id}/status", response_model=DocumentStatusResponse, status_code=status.HTTP_200_OK)
def get_document_status(
    doc_id: UUID,
    context: AuthContext = Depends(require_org),
    service: DocumentsService = Depends(get_documents_service),
) -> DocumentStatusResponse:
    doc, total_chunks, embedded_chunks = service.get_status(context.org_id, doc_id)
    return DocumentStatusResponse(
        doc_id=doc.id,
        status=doc.status.value,
        error_message=doc.error_message,
        total_chunks=total_chunks,
        embedded_chunks=embedded_chunks,
    )
