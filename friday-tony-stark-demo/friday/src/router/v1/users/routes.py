from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from friday.src.dependencies.auth import require_active_user
from friday.src.dependencies.database import get_db
from friday.src.models.user import User
from friday.src.schemas.users.responses import UserResponse
from friday.src.services.users.service import get_visible_user, list_visible_users


router = APIRouter()


@router.get("", response_model=list[UserResponse])
def list_users_route(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> list[User]:
    return list_visible_users(db, current_user=current_user, limit=limit, offset=offset)


@router.get("/{user_id}", response_model=UserResponse)
def get_user_route(
    user_id: int,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> User:
    return get_visible_user(db, current_user=current_user, user_id=user_id)
