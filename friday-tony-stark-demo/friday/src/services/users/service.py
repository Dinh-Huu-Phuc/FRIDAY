from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from friday.src.crud.user_crud import get_user, list_users
from friday.src.models.user import User


def list_visible_users(db: Session, *, current_user: User, limit: int = 50, offset: int = 0) -> list[User]:
    if current_user.role is None or current_user.role.name != "admin":
        return [current_user]
    return list_users(db, limit=limit, offset=offset)


def get_visible_user(db: Session, *, current_user: User, user_id: int) -> User:
    if current_user.role is None or current_user.role.name != "admin":
        if current_user.id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot view another user.")
        return current_user
    user = get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user
