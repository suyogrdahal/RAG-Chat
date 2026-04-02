from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.models import ChatLog


class ChatLogsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_chat_log(
        self,
        org_id: UUID,
        query_text: str,
        response_text: str,
        *,
        user_id: UUID | None = None,
        session_id: str | None = None,
        confidence: float | None = None,
        sources_json: list[dict] | None = None,
    ) -> ChatLog:
        log = ChatLog(
            org_id=org_id,
            user_id=user_id,
            session_id=session_id,
            query_text=query_text,
            response_text=response_text,
            confidence=confidence,
            sources_json=sources_json,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def list_chat_logs(
        self,
        org_id: UUID,
        limit: int,
        offset: int,
        *,
        search: str | None = None,
        session_id: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort: str = "-created_at",
    ) -> tuple[list[ChatLog], int]:
        filters = [ChatLog.org_id == org_id]
        if search:
            pattern = f"%{search.strip()}%"
            filters.append(
                or_(
                    ChatLog.query_text.ilike(pattern),
                    ChatLog.response_text.ilike(pattern),
                )
            )
        if session_id:
            filters.append(ChatLog.session_id == session_id)
        if date_from is not None:
            filters.append(ChatLog.created_at >= date_from)
        if date_to is not None:
            filters.append(ChatLog.created_at <= date_to)

        query = select(ChatLog).where(*filters)
        count_query = select(func.count(ChatLog.id)).where(*filters)

        if sort == "created_at":
            query = query.order_by(ChatLog.created_at.asc())
        else:
            query = query.order_by(ChatLog.created_at.desc())

        query = query.limit(limit).offset(offset)
        rows = list(self.db.scalars(query).all())
        total = int(self.db.scalar(count_query) or 0)
        return rows, total

    def get_chat_log_by_id(self, org_id: UUID, log_id: UUID) -> ChatLog | None:
        return self.db.scalar(
            select(ChatLog).where(ChatLog.org_id == org_id, ChatLog.id == log_id)
        )

    def delete_chat_log(self, org_id: UUID, log_id: UUID) -> bool:
        log = self.get_chat_log_by_id(org_id, log_id)
        if log is None:
            return False
        self.db.delete(log)
        self.db.commit()
        return True
