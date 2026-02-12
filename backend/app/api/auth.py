import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.logging import hash_email, log_event
from app.core.security import decode_access_token
from app.db.session import get_db
from app.repositories.auth_repository import AuthRepository
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    SignupRequest,
    SignupResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger("app.auth")


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(AuthRepository(db))


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
def signup(
    payload: SignupRequest,
    service: AuthService = Depends(get_auth_service),
) -> SignupResponse:
    return service.signup(payload)


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
def login(
    request: Request,
    payload: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    request_id = getattr(request.state, "request_id", None)
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    email_digest = hash_email(str(payload.email))

    try:
        result = service.login(payload)
        log_event(
            logger,
            logging.INFO,
            "auth_login_success",
            request_id=request_id,
            user_id=str(result.user_id),
            org_id=str(result.org_id),
            email_hash=email_digest,
            ip=ip,
            user_agent=user_agent,
        )
        return result
    except HTTPException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            log_event(
                logger,
                logging.INFO,
                "auth_login_failure",
                request_id=request_id,
                reason="invalid_credentials",
                email_hash=email_digest,
                ip=ip,
                user_agent=user_agent,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        raise


@router.post("/refresh", response_model=RefreshResponse, status_code=status.HTTP_200_OK)
def refresh(
    request: Request,
    payload: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
) -> RefreshResponse:
    request_id = getattr(request.state, "request_id", None)
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        result = service.rotate_refresh_token(payload)
        claims = decode_access_token(result.access_token)
        log_event(
            logger,
            logging.INFO,
            "auth_refresh_success",
            request_id=request_id,
            user_id=claims.get("sub"),
            org_id=claims.get("org_id"),
            ip=ip,
            user_agent=user_agent,
        )
        return result
    except HTTPException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            log_event(
                logger,
                logging.INFO,
                "auth_refresh_failure",
                request_id=request_id,
                reason="invalid_refresh_token",
                ip=ip,
                user_agent=user_agent,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        raise
