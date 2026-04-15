from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.ingestion.retrieval_guard import evaluate_retrieval_results
from app.llm.wrapper import generate_llm_response
from app.repositories.chat_logs import ChatLogsRepository
from app.repositories.org_repository import OrgRepository
from app.services.embeddings import embed_query
from app.services.greetings import is_greeting
from app.services.prompting import (
    build_fallback_message,
    build_greeting_message,
    build_rag_prompt,
    build_retrieved_context,
)
from app.services.similarity_search import search_similar_chunks


logger = logging.getLogger("app.chat")


@dataclass
class ChatResult:
    answer: str
    sources: list[dict]
    confidence: float
    retrieval_count: int | None = None
    used_context_chars: int | None = None


class ChatService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.org_repo = OrgRepository(db)
        self.chat_log_repo = ChatLogsRepository(db)
        self.settings = get_settings()

    def _fallback(self, org_name: str, org_description: str | None, *, debug: bool = False) -> ChatResult:
        return ChatResult(
            answer=build_fallback_message(org_name, org_description),
            sources=[],
            confidence=0.0,
            retrieval_count=0 if debug else None,
            used_context_chars=0 if debug else None,
        )

    @staticmethod
    def _sources(chunks: list[dict]) -> list[dict]:
        return [
            {
                "chunk_id": str(chunk.get("chunk_id", "")),
                "doc_id": str(chunk.get("doc_id", "")),
                "score": float(chunk.get("score", 0.0)),
            }
            for chunk in chunks
        ]

    def _log_interaction(
        self,
        *,
        org_id: UUID,
        user_id: UUID | str | None,
        query: str,
        response: str,
        confidence: float,
        sources: list[dict],
        session_id: str | None = None,
    ) -> None:
        safe_session_id = session_id or str(uuid4())
        normalized_user_id: UUID | None = None
        if isinstance(user_id, UUID):
            normalized_user_id = user_id
        elif isinstance(user_id, str):
            try:
                normalized_user_id = UUID(user_id)
            except ValueError:
                normalized_user_id = None

        try:
            self.chat_log_repo.create_chat_log(
                org_id=org_id,
                user_id=normalized_user_id,
                session_id=safe_session_id,
                query_text=query,
                response_text=response,
                confidence=confidence,
                sources_json=sources,
            )
        except Exception as exc:
            try:
                self.db.rollback()
            except Exception:
                pass
            logger.warning(
                "chat_log_persist_failed",
                extra={
                    "event": "chat_log_persist_failed",
                    "org_id": str(org_id),
                    "error": str(exc),
                },
            )

    async def query(
        self,
        *,
        org_id: UUID,
        query: str,
        request_id: str | None = None,
        user_id: UUID | str | None = None,
        session_id: str | None = None,
        debug: bool = False,
    ) -> ChatResult:
        org = self.org_repo.get_by_id(org_id)
        if org is None:
            result = self._fallback("this organization", None, debug=debug)
            self._log_interaction(
                org_id=org_id,
                user_id=user_id,
                session_id=session_id,
                query=query,
                response=result.answer,
                confidence=result.confidence,
                sources=result.sources,
            )
            return result

        org_name = org.name
        org_description = org.organization_description

        if is_greeting(query):
            result = ChatResult(
                answer=build_greeting_message(org_name),
                sources=[],
                confidence=0.0,
                retrieval_count=0 if debug else None,
                used_context_chars=0 if debug else None,
            )
            self._log_interaction(
                org_id=org_id,
                user_id=user_id,
                session_id=session_id,
                query=query,
                response=result.answer,
                confidence=result.confidence,
                sources=result.sources,
            )
            return result

        query_embedding = embed_query(query)
        chunks = await search_similar_chunks(
            db=self.db,
            org_id=org_id,
            query_embedding=query_embedding,
            top_k=int(self.settings.rag_top_k),
        )
        retrieval = evaluate_retrieval_results(
            chunks=chunks,
            threshold=float(self.settings.rag_similarity_threshold),
        )
        if not chunks or not retrieval.get("proceed", False):
            result = self._fallback(org_name, org_description, debug=debug)
            self._log_interaction(
                org_id=org_id,
                user_id=user_id,
                session_id=session_id,
                query=query,
                response=result.answer,
                confidence=result.confidence,
                sources=result.sources,
            )
            return result

        max_context_chars = max(
            256,
            min(
                int(self.settings.rag_max_context_chars),
                int(org.max_tokens_per_request or 800) * 4 - int(self.settings.rag_reserved_answer_tokens) * 4,
            ),
        )
        context = build_retrieved_context(chunks=chunks, max_context_chars=max_context_chars)
        if not context:
            result = self._fallback(org_name, org_description, debug=debug)
            self._log_interaction(
                org_id=org_id,
                user_id=user_id,
                session_id=session_id,
                query=query,
                response=result.answer,
                confidence=result.confidence,
                sources=result.sources,
            )
            return result

        prompt = build_rag_prompt(
            org_name=org_name,
            org_description=org_description,
            context=context,
            user_query=query,
        )
        llm_result = await generate_llm_response(
            prompt,
            request_id=request_id,
            org_id=org_id,
            user_id=user_id,
            query=query,
        )
        answer = str(llm_result.get("answer", "")).strip()
        if answer == "ERR1010" or not answer:
            result = self._fallback(org_name, org_description, debug=debug)
            self._log_interaction(
                org_id=org_id,
                user_id=user_id,
                session_id=session_id,
                query=query,
                response=result.answer,
                confidence=result.confidence,
                sources=result.sources,
            )
            return result

        result = ChatResult(
            answer=answer,
            sources=self._sources(chunks),
            confidence=float(retrieval.get("confidence", 0.0)),
            retrieval_count=len(chunks) if debug else None,
            used_context_chars=len(context) if debug else None,
        )
        self._log_interaction(
            org_id=org_id,
            user_id=user_id,
            session_id=session_id,
            query=query,
            response=result.answer,
            confidence=result.confidence,
            sources=result.sources,
        )
        return result
