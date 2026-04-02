from __future__ import annotations

from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps.auth import require_org
from app.api.deps.rate_limit import rate_limit_public
from app.core.config import get_settings
from app.db.models import Organization
from app.db.session import get_db
from app.schemas.auth_context import AuthContext
from app.services.chat import ChatService

router = APIRouter(tags=["widget"])


def _normalize_domain(value: str) -> str:
    parsed = urlsplit(value.strip())
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError("Domain must use http or https")
    if not parsed.netloc or "@" in parsed.netloc:
        raise ValueError("Domain must include a valid host")
    if parsed.query or parsed.fragment:
        raise ValueError("Domain must not include query or fragment")
    if parsed.path not in {"", "/"}:
        raise ValueError("Domain must not include a path")
    return f"{scheme}://{parsed.netloc.lower()}"


def _resolve_request_origin(request: Request) -> str | None:
    origin = request.headers.get("origin")
    if origin:
        try:
            return _normalize_domain(origin)
        except ValueError:
            return None

    referer = request.headers.get("referer")
    if not referer:
        return None
    parsed = urlsplit(referer.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    try:
        return _normalize_domain(f"{parsed.scheme}://{parsed.netloc}")
    except ValueError:
        return None


def _dedupe_domains(domains: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for domain in domains:
        value = _normalize_domain(domain)
        if value not in seen:
            seen.add(value)
            normalized.append(value)
    return normalized


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class WidgetConfigResponse(BaseModel):
    widget_public_key: str
    allowed_domains: list[str]
    org_name: str
    organization_description: str | None = None
    theme: dict | None = None


class WidgetDomainsReplaceRequest(BaseModel):
    allowed_domains: list[str] = Field(default_factory=list)


class WidgetDomainsResponse(BaseModel):
    allowed_domains: list[str]


class PublicChatQueryRequest(BaseModel):
    widget_public_key: str = Field(min_length=16, max_length=256)
    query: str = Field(min_length=1)
    session_id: str | None = None


class PublicChatQueryResponse(BaseModel):
    answer: str
    sources: list[dict] = Field(default_factory=list)
    confidence: float = 0.0


@router.get("/widget/config", response_model=WidgetConfigResponse)
def get_widget_config(
    context: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> WidgetConfigResponse:
    org = db.get(Organization, context.org_id)
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Org not found")
    return WidgetConfigResponse(
        widget_public_key=org.widget_public_key,
        allowed_domains=org.allowed_domains,
        org_name=org.name,
        organization_description=org.organization_description,
        theme=None,
    )


@router.get("/widget/domains", response_model=WidgetDomainsResponse)
def get_widget_domains(
    context: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> WidgetDomainsResponse:
    org = db.get(Organization, context.org_id)
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Org not found")
    return WidgetDomainsResponse(allowed_domains=org.allowed_domains)


@router.put("/widget/domains", response_model=WidgetDomainsResponse)
def put_widget_domains(
    payload: WidgetDomainsReplaceRequest,
    context: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> WidgetDomainsResponse:
    try:
        domains = _dedupe_domains(payload.allowed_domains)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    org = db.get(Organization, context.org_id)
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Org not found")
    org.allowed_domains = domains
    db.add(org)
    db.commit()
    db.refresh(org)
    return WidgetDomainsResponse(allowed_domains=org.allowed_domains)


@router.post("/public/chat/query", response_model=PublicChatQueryResponse)
async def public_chat_query(
    payload: PublicChatQueryRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> PublicChatQueryResponse:
    settings = get_settings()
    org = db.scalar(
        select(Organization).where(Organization.widget_public_key == payload.widget_public_key)
    )
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not found")
    origin = _resolve_request_origin(request)
    try:
        allowed = set(_dedupe_domains(org.allowed_domains))
    except ValueError:
        allowed = set()
    if not origin or origin not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Origin not allowed")
    if len(payload.query) > int(settings.public_query_max_chars):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Query too long",
        )

    max_tokens = int(org.max_tokens_per_request or 0)
    if _estimate_tokens(payload.query) > max_tokens:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Query token budget exceeded",
        )

    ip_address = request.client.host if request.client else "unknown"
    await rate_limit_public(
        org_id=org.id,
        ip_address=ip_address,
        org_limit=int(settings.public_rate_limit_org_per_min),
        ip_limit=int(settings.public_rate_limit_ip_per_min),
    )
    service = ChatService(db)
    result = await service.query(
        org_id=org.id,
        query=payload.query,
        session_id=payload.session_id,
        request_id=getattr(request.state, "request_id", None),
        debug=False,
    )
    return PublicChatQueryResponse(
        answer=result.answer,
        sources=result.sources,
        confidence=result.confidence,
    )
