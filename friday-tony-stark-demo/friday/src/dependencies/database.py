from __future__ import annotations

from collections.abc import Generator

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from friday.src.db.session import get_session_factory


def get_db() -> Generator[Session, None, None]:
    try:
        session_factory = get_session_factory()
        db = session_factory()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database is unavailable: {exc}",
        ) from exc
    try:
        yield db
    finally:
        db.close()
