from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from friday.src.config.settings import get_settings


_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is not None:
        return _engine

    database_url = get_settings().database_url
    if not database_url:
        raise RuntimeError("PostgreSQL DATABASE_URL is not configured.")

    _engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=1800,
        future=True,
    )
    return _engine
