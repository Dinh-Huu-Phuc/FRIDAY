from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable
from uuid import UUID

from sqlalchemy import insert, update
from sqlalchemy.engine import Engine

from friday.core.db.models import ScreenCaptureAsset, ScreenCaptureRecord
from friday.src.db.database import get_engine


class ScreenCaptureRepository:
    def __init__(self, engine: Engine | None = None) -> None:
        self._engine = engine or get_engine()

    def create_pending(
        self,
        *,
        capture_id: UUID,
        captured_at: datetime,
        user_question: str,
        active_window_title: str,
        monitor_count: int,
    ) -> None:
        with self._engine.begin() as connection:
            connection.execute(
                insert(ScreenCaptureRecord).values(
                    id=capture_id,
                    captured_at=captured_at,
                    user_question=user_question,
                    active_window_title=active_window_title,
                    monitor_count=monitor_count,
                    status="pending",
                )
            )

    def mark_uploaded(
        self,
        capture_id: UUID,
        assets: Iterable[dict],
    ) -> None:
        now = datetime.now(timezone.utc)
        with self._engine.begin() as connection:
            connection.execute(insert(ScreenCaptureAsset), list(assets))
            connection.execute(
                update(ScreenCaptureRecord)
                .where(ScreenCaptureRecord.id == capture_id)
                .values(status="uploaded", error_message=None, updated_at=now)
            )

    def mark_failed(self, capture_id: UUID, error_message: str) -> None:
        with self._engine.begin() as connection:
            connection.execute(
                update(ScreenCaptureRecord)
                .where(ScreenCaptureRecord.id == capture_id)
                .values(
                    status="failed",
                    error_message=error_message[:2000],
                    updated_at=datetime.now(timezone.utc),
                )
            )
