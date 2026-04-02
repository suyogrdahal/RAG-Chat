from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import Organization


class OrgRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, org_id) -> Organization | None:
        return self.db.get(Organization, org_id)
