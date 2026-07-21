from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from friday.src.models.admin_account import AdminAccount


def get_admin_account(db: Session, admin_id: int) -> AdminAccount | None:
    return db.get(AdminAccount, admin_id)


def get_admin_by_username(db: Session, username: str) -> AdminAccount | None:
    return db.execute(select(AdminAccount).where(AdminAccount.username == username)).scalar_one_or_none()


def list_admin_accounts(db: Session) -> list[AdminAccount]:
    return list(db.execute(select(AdminAccount).order_by(AdminAccount.id)).scalars().all())


def create_admin_account(
    db: Session,
    *,
    username: str,
    password_hash: str,
    display_name: str | None,
    role: str = "admin",
) -> AdminAccount:
    admin = AdminAccount(
        username=username,
        password_hash=password_hash,
        display_name=display_name,
        role=role,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


def update_admin_last_login(db: Session, admin: AdminAccount, when: datetime) -> AdminAccount:
    admin.last_login_at = when
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin
