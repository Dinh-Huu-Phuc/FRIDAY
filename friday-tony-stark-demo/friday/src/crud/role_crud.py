from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from friday.src.models.role import Role


def get_role_by_name(db: Session, name: str) -> Role | None:
    return db.execute(select(Role).where(Role.name == name)).scalar_one_or_none()
