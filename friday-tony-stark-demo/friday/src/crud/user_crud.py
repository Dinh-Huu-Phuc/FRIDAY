from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from friday.src.models.user import User


def get_user(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.execute(select(User).where(User.username == username)).scalar_one_or_none()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.execute(select(User).where(User.email == email)).scalar_one_or_none()


def get_user_by_username_or_email(db: Session, value: str) -> User | None:
    return db.execute(select(User).where(or_(User.username == value, User.email == value))).scalar_one_or_none()


def list_users(db: Session, limit: int = 50, offset: int = 0) -> list[User]:
    return list(db.execute(select(User).order_by(User.id).limit(limit).offset(offset)).scalars().all())


def create_user(db: Session, *, username: str, email: str, password_hash: str, full_name: str | None, role_id: int | None) -> User:
    user = User(username=username, email=email, password_hash=password_hash, full_name=full_name, role_id=role_id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_last_login(db: Session, user: User, when: datetime) -> User:
    user.last_login_at = when
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_quotas(
    db: Session,
    user: User,
    *,
    free_question_limit_daily: int | None = None,
    api_key_question_limit_daily: int | None = None,
    is_active: bool | None = None,
) -> User:
    if free_question_limit_daily is not None:
        user.free_question_limit_daily = free_question_limit_daily
    if api_key_question_limit_daily is not None:
        user.api_key_question_limit_daily = api_key_question_limit_daily
    if is_active is not None:
        user.is_active = is_active
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
