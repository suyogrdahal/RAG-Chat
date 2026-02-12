from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.api.deps.auth import require_org, require_role
from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.db.models import OrgMembership, Organization, User
from app.db.session import get_db
from app.middlewares.request_logging import RequestLoggingMiddleware
from app.schemas.auth_context import AuthContext

settings = get_settings()
configure_logging()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(auth_router)
app.include_router(users_router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "env": settings.env,
        "debug": settings.debug,
    }


@app.get("/auth/whoami")
def whoami(auth: AuthContext = Depends(require_org)):
    return auth


@app.get("/protected/org-scope")
def protected_org_scope(auth: AuthContext = Depends(require_org)):
    return {"user_id": str(auth.user_id), "org_id": str(auth.org_id), "role": auth.role}


class OrgCreate(BaseModel):
    name: str
    slug: str | None = None
    status: str | None = None
    allowed_domains: list[str] | None = None
    rate_limit_per_minute: int | None = None
    max_tokens_per_request: int | None = None


class UserCreate(BaseModel):
    org_id: UUID | None = None
    email: str
    password_hash: str | None = None
    role: str | None = None
    is_active: bool | None = None


@app.post(
    "/debug/orgs",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role("admin"))],
)
def create_org(
    payload: OrgCreate,
    auth: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
):
    org = db.query(Organization).filter(Organization.id == auth.org_id).one_or_none()
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Org not found")
    org.name = payload.name
    if payload.slug is not None:
        org.slug = payload.slug
    if payload.status is not None:
        org.status = payload.status
    if payload.allowed_domains is not None:
        org.allowed_domains = payload.allowed_domains
    if payload.rate_limit_per_minute is not None:
        org.rate_limit_per_minute = payload.rate_limit_per_minute
    if payload.max_tokens_per_request is not None:
        org.max_tokens_per_request = payload.max_tokens_per_request
    db.add(org)
    db.commit()
    db.refresh(org)
    return {
        "id": str(org.id),
        "name": org.name,
        "slug": org.slug,
        "status": org.status,
        "allowed_domains": org.allowed_domains,
        "rate_limit_per_minute": org.rate_limit_per_minute,
        "max_tokens_per_request": org.max_tokens_per_request,
        "created_at": org.created_at,
        "updated_at": org.updated_at,
    }


@app.get("/debug/orgs/{org_id}")
def get_org(
    org_id: UUID,
    auth: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
):
    if auth.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Org not found")
    org = db.get(Organization, org_id)
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Org not found")
    return {
        "id": str(org.id),
        "name": org.name,
        "slug": org.slug,
        "status": org.status,
        "allowed_domains": org.allowed_domains,
        "rate_limit_per_minute": org.rate_limit_per_minute,
        "max_tokens_per_request": org.max_tokens_per_request,
        "created_at": org.created_at,
        "updated_at": org.updated_at,
    }


@app.post(
    "/debug/users",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("admin"))],
)
def create_user(
    payload: UserCreate,
    auth: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
):
    user = User(
        org_id=auth.org_id,
        active_org_id=auth.org_id,
        email=payload.email,
        password_hash=payload.password_hash,
        role=payload.role or "admin",
        is_active=True if payload.is_active is None else payload.is_active,
    )
    db.add(user)
    db.flush()
    db.add(OrgMembership(user_id=user.id, org_id=user.org_id, role=user.role))
    db.commit()
    db.refresh(user)
    return {
        "id": str(user.id),
        "org_id": str(user.org_id),
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "last_login_at": user.last_login_at,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


@app.get("/debug/users/{user_id}")
def get_user(
    user_id: UUID,
    auth: AuthContext = Depends(require_org),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id, User.org_id == auth.org_id).one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {
        "id": str(user.id),
        "org_id": str(user.org_id),
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "last_login_at": user.last_login_at,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }
