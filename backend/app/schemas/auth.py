from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    org_name: str = Field(min_length=1)
    org_slug: str | None = None
    email: EmailStr
    password: str = Field(min_length=8)


class SignupResponse(BaseModel):
    org_id: UUID | None = None
    user_id: UUID | None = None
    message: str = "Signup successful"


class LoginRequest(BaseModel):
    org_slug: str | None = Field(default=None, min_length=1)
    org_id: UUID | None = None
    email: EmailStr
    password: str = Field(min_length=8)


class LoginResponse(BaseModel):
    org_id: UUID
    user_id: UUID
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=16)


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
