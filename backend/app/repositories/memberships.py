from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import OrgMembership


class MembershipRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_user_memberships(self, user_id) -> list[OrgMembership]:
        return list(
            self.db.scalars(
                select(OrgMembership).where(OrgMembership.user_id == user_id)
            ).all()
        )

    def get_membership(self, user_id, org_id) -> OrgMembership | None:
        return self.db.scalar(
            select(OrgMembership).where(
                OrgMembership.user_id == user_id,
                OrgMembership.org_id == org_id,
            )
        )

    def create_membership(self, membership: OrgMembership) -> OrgMembership:
        self.db.add(membership)
        return membership
