from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps.auth import require_org
from app.db.session import get_db
from app.schemas.auth_context import AuthContext
from app.services.chat import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatQueryRequest(BaseModel):
    query: str = Field(min_length=1)
    session_id: str | None = None
    debug: bool = False


class ChatQueryResponse(BaseModel):
    answer: str
    sources: list[dict] = Field(default_factory=list)
    confidence: float = 0.0
    retrieval_count: int | None = None
    used_context_chars: int | None = None


@router.post("/query", response_model=ChatQueryResponse, status_code=status.HTTP_200_OK)
async def chat_query(
    payload: ChatQueryRequest,
    request: Request,
    context: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> ChatQueryResponse:
    service = ChatService(db)
    result = await service.query(
        org_id=context.org_id,
        query=payload.query,
        request_id=getattr(request.state, "request_id", None),
        user_id=context.user_id,
        session_id=payload.session_id,
        debug=payload.debug,
    )
    return ChatQueryResponse(
        answer=result.answer,
        sources=result.sources,
        confidence=result.confidence,
        retrieval_count=result.retrieval_count,
        used_context_chars=result.used_context_chars,
    )
