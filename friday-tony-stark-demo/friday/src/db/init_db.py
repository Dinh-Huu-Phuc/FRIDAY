from __future__ import annotations

from sqlalchemy.orm import Session

from friday.src.crud.role_crud import get_role_by_name
from friday.src.models.role import Role


DEFAULT_ROLES = ("admin", "user", "developer")


def seed_default_roles(db: Session) -> None:
    for role_name in DEFAULT_ROLES:
        if get_role_by_name(db, role_name) is None:
            db.add(Role(name=role_name, description=f"Default {role_name} role"))
    db.commit()
