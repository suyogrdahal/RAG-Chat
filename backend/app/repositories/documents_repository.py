from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentChunk


class DocumentsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, document: Document) -> Document:
        self.db.add(document)
        return document

    def get_by_id(self, org_id, doc_id) -> Document | None:
        return self.db.scalar(
            select(Document).where(Document.org_id == org_id, Document.id == doc_id)
        )

    def list_documents(
        self,
        org_id,
        status: str | None,
        limit: int,
        offset: int,
        sort: str,
    ) -> tuple[list[Document], int]:
        query = select(Document).where(Document.org_id == org_id)
        count_query = select(func.count(Document.id)).where(Document.org_id == org_id)

        if status:
            query = query.where(Document.status == status)
            count_query = count_query.where(Document.status == status)

        if sort == "created_at":
            query = query.order_by(Document.created_at.asc())
        else:
            query = query.order_by(Document.created_at.desc())

        query = query.limit(limit).offset(offset)
        items = list(self.db.scalars(query).all())
        total = int(self.db.scalar(count_query) or 0)
        return items, total

    def get_chunk_counts(self, org_id, doc_id) -> tuple[int, int]:
        total = self.db.scalar(
            select(func.count(DocumentChunk.id)).where(
                DocumentChunk.org_id == org_id,
                DocumentChunk.doc_id == doc_id,
            )
        )
        embedded = self.db.scalar(
            select(func.count(DocumentChunk.id)).where(
                DocumentChunk.org_id == org_id,
                DocumentChunk.doc_id == doc_id,
                DocumentChunk.embedding.is_not(None),
            )
        )
        return int(total or 0), int(embedded or 0)

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    def refresh(self, document: Document) -> None:
        self.db.refresh(document)
