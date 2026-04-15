from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps.auth import require_org
from app.db.session import get_db
from app.schemas.auth_context import AuthContext
from app.schemas.documents import DashboardSummaryResponse
from app.services.documents_service import DocumentsService
from app.repositories.documents_repository import DocumentsRepository

router = APIRouter(tags=["dashboard"])


def get_documents_service(db: Session = Depends(get_db)) -> DocumentsService:
    return DocumentsService(DocumentsRepository(db))


@router.get("/dashboard", response_model=DashboardSummaryResponse, status_code=status.HTTP_200_OK)
def get_dashboard(
    context: AuthContext = Depends(require_org),
    service: DocumentsService = Depends(get_documents_service),
) -> DashboardSummaryResponse:
    return service.get_dashboard_summary(context.org_id)
