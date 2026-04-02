from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps.auth import require_org
from app.db.models import Organization
from app.db.session import get_db
from app.schemas.auth_context import AuthContext

router = APIRouter(prefix="/org", tags=["org"])


class OrgProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    organization_description: str | None = None


class OrgProfileResponse(BaseModel):
    id: str
    name: str
    organization_description: str | None = None


@router.put("/profile", response_model=OrgProfileResponse, status_code=status.HTTP_200_OK)
def update_org_profile(
    payload: OrgProfileUpdateRequest,
    context: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
) -> OrgProfileResponse:
    org = db.get(Organization, context.org_id)
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Org not found")
    if payload.name is not None:
        org.name = payload.name
    if payload.organization_description is not None:
        org.organization_description = payload.organization_description.strip() or None
    db.add(org)
    db.commit()
    db.refresh(org)
    return OrgProfileResponse(
        id=str(org.id),
        name=org.name,
        organization_description=org.organization_description,
    )
