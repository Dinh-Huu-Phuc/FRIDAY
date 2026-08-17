from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Select, or_, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from friday.core.memory_database.models import Memory


class MemoryRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def _visible_statement(
        statement: Select,
        *,
        include_inactive: bool,
        include_expired: bool,
    ) -> Select:
        if not include_inactive:
            statement = statement.where(Memory.is_active.is_(True))
        if not include_expired:
            statement = statement.where(
                or_(
                    Memory.expires_at.is_(None),
                    Memory.expires_at > datetime.now(timezone.utc),
                )
            )
        return statement

    def list(
        self,
        *,
        subject: str | None = None,
        memory_type: str | None = None,
        include_inactive: bool = False,
        include_expired: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Memory]:
        statement = select(Memory)
        if subject is not None:
            statement = statement.where(Memory.subject == subject)
        if memory_type is not None:
            statement = statement.where(Memory.memory_type == memory_type)
        statement = self._visible_statement(
            statement,
            include_inactive=include_inactive,
            include_expired=include_expired,
        )
        statement = statement.order_by(
            Memory.importance.desc(),
            Memory.updated_at.desc(),
        ).limit(limit).offset(offset)
        return list(self._db.execute(statement).scalars().all())

    def get(
        self,
        memory_id: UUID,
        *,
        include_inactive: bool = False,
        include_expired: bool = False,
    ) -> Memory | None:
        statement = self._visible_statement(
            select(Memory).where(Memory.id == memory_id),
            include_inactive=include_inactive,
            include_expired=include_expired,
        )
        return self._db.execute(statement).scalar_one_or_none()

    def get_any(self, memory_id: UUID) -> Memory | None:
        return self._db.get(Memory, memory_id)

    def upsert(self, values: dict[str, Any]) -> Memory:
        now = datetime.now(timezone.utc)
        insert_values = {
            **values,
            "id": uuid4(),
            "created_at": now,
            "updated_at": now,
            "is_active": True,
        }
        update_values = {
            "memory_value": values["memory_value"],
            "memory_type": values["memory_type"],
            "importance": values["importance"],
            "confidence": values["confidence"],
            "source_message_id": values.get("source_message_id"),
            "expires_at": values.get("expires_at"),
            "updated_at": now,
            "is_active": True,
        }
        dialect_name = self._db.get_bind().dialect.name
        if dialect_name == "postgresql":
            statement = postgresql_insert(Memory).values(**insert_values)
            statement = statement.on_conflict_do_update(
                index_elements=["subject", "memory_key"],
                set_=update_values,
            )
            self._db.execute(statement)
        elif dialect_name == "sqlite":
            statement = sqlite_insert(Memory).values(**insert_values)
            statement = statement.on_conflict_do_update(
                index_elements=["subject", "memory_key"],
                set_=update_values,
            )
            self._db.execute(statement)
        else:
            existing = self._db.execute(
                select(Memory).where(
                    Memory.subject == values["subject"],
                    Memory.memory_key == values["memory_key"],
                )
            ).scalar_one_or_none()
            if existing is None:
                self._db.add(Memory(**insert_values))
            else:
                for field, value in update_values.items():
                    setattr(existing, field, value)

        self._db.commit()
        memory = self._db.execute(
            select(Memory).where(
                Memory.subject == values["subject"],
                Memory.memory_key == values["memory_key"],
            )
        ).scalar_one()
        self._db.refresh(memory)
        return memory

    def update(self, memory: Memory, values: dict[str, Any]) -> Memory:
        for field, value in values.items():
            setattr(memory, field, value)
        memory.updated_at = datetime.now(timezone.utc)
        self._db.add(memory)
        self._db.commit()
        self._db.refresh(memory)
        return memory

    def set_active(self, memory: Memory, *, active: bool) -> Memory:
        return self.update(memory, {"is_active": active})

    def delete(self, memory: Memory) -> None:
        self._db.delete(memory)
        self._db.commit()
