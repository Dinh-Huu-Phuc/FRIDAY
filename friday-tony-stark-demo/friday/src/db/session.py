from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from friday.src.db.database import get_engine


_session_local: sessionmaker[Session] | None = None


def get_session_factory() -> sessionmaker[Session]:
    global _session_local
    if _session_local is None:
        _session_local = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine(),
            expire_on_commit=False,
            future=True,
        )
    return _session_local
