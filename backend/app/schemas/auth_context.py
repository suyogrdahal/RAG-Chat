from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class AuthContext(BaseModel):
    user_id: UUID
    org_id: UUID
    role: str
