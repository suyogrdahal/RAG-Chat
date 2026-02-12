from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserCreateRequest(BaseModel):
    email: EmailStr
    password_hash: str | None = None
    role: str = "admin"
    is_active: bool = True
    org_id: UUID | None = None


class UserUpdateRequest(BaseModel):
    email: EmailStr | None = None
    role: str | None = None
    is_active: bool | None = None
    org_id: UUID | None = None


class UserResponse(BaseModel):
    id: UUID
    org_id: UUID
    email: EmailStr
    role: str
    is_active: bool
