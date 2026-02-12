from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session


def scoped_get(db: Session, model, org_id, resource_id):
    return db.scalar(
        select(model).where(
            model.id == resource_id,
            model.org_id == org_id,
        )
    )
