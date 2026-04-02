from __future__ import annotations

from datetime import datetime

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from starlette.responses import Response

from app.api.deps.auth import require_org, require_role
from app.db.session import get_db
from app.repositories.chat_logs import ChatLogsRepository
from app.schemas.auth_context import AuthContext
from app.schemas.chat_logs import ChatLogListResponse, ChatLogOut

router = APIRouter(prefix="/chat-logs", tags=["chat-logs"])


def get_chat_logs_repository(db: Session = Depends(get_db)) -> ChatLogsRepository:
    return ChatLogsRepository(db)


def _to_log_out(log) -> ChatLogOut:
    sources = log.sources_json
    if not isinstance(sources, list):
        sources = []
    return ChatLogOut(
        id=log.id,
        session_id=log.session_id,
        query_text=log.query_text,
        response_text=log.response_text,
        confidence=log.confidence,
        sources=sources,
        created_at=log.created_at,
    )


@router.get("", response_model=ChatLogListResponse, status_code=status.HTTP_200_OK)
def list_chat_logs(
    limit: int = 25,
    offset: int = 0,
    search: str | None = None,
    session_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort: str = "-created_at",
    context: AuthContext = Depends(require_org),
    repo: ChatLogsRepository = Depends(get_chat_logs_repository),
) -> ChatLogListResponse:
    if limit < 1:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid limit")
    if limit > 100:
        limit = 100
    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid offset",
        )
    if sort not in {"created_at", "-created_at"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid sort")

    items, total = repo.list_chat_logs(
        context.org_id,
        limit,
        offset,
        search=search,
        session_id=session_id,
        date_from=date_from,
        date_to=date_to,
        sort=sort,
    )
    return ChatLogListResponse(
        items=[_to_log_out(log) for log in items],
        limit=limit,
        offset=offset,
        total=total,
    )


@router.get("/{log_id}", response_model=ChatLogOut, status_code=status.HTTP_200_OK)
def get_chat_log(
    log_id: UUID,
    context: AuthContext = Depends(require_org),
    repo: ChatLogsRepository = Depends(get_chat_logs_repository),
) -> ChatLogOut:
    log = repo.get_chat_log_by_id(context.org_id, log_id)
    if log is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat log not found")
    return _to_log_out(log)


@router.delete("/{log_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_role("admin"))])
def delete_chat_log(
    log_id: UUID,
    context: AuthContext = Depends(require_org),
    repo: ChatLogsRepository = Depends(get_chat_logs_repository),
) -> Response:
    deleted = repo.delete_chat_log(context.org_id, log_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat log not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
