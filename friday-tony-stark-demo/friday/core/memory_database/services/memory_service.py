from __future__ import annotations

from typing import Any
from uuid import UUID

from friday.core.memory_database.models import Memory
from friday.core.memory_database.repositories import MemoryRepository


class MemoryNotFoundError(LookupError):
    pass


class InvalidMemoryQueryError(ValueError):
    pass


class MemoryService:
    def __init__(self, repository: MemoryRepository) -> None:
        self._repository = repository

    @staticmethod
    def _normalize_identifier(value: str, *, field: str) -> str:
        normalized = " ".join(value.strip().split()).lower()
        if not normalized:
            raise InvalidMemoryQueryError(f"{field} cannot be blank.")
        return normalized

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
        return self._repository.list(
            subject=(
                self._normalize_identifier(subject, field="subject")
                if subject is not None
                else None
            ),
            memory_type=(
                self._normalize_identifier(memory_type, field="memory_type")
                if memory_type is not None
                else None
            ),
            include_inactive=include_inactive,
            include_expired=include_expired,
            limit=limit,
            offset=offset,
        )

    def relevant(
        self,
        *,
        subject: str | None,
        memory_type: str | None,
        limit: int,
    ) -> list[Memory]:
        if subject is None and memory_type is None:
            raise InvalidMemoryQueryError(
                "At least one of subject or memory_type is required."
            )
        return self.list(subject=subject, memory_type=memory_type, limit=limit)

    def get(self, memory_id: UUID) -> Memory:
        memory = self._repository.get(memory_id)
        if memory is None:
            raise MemoryNotFoundError("Memory not found.")
        return memory

    def upsert(self, values: dict[str, Any]) -> Memory:
        normalized = {
            **values,
            "subject": self._normalize_identifier(values["subject"], field="subject"),
            "memory_key": self._normalize_identifier(
                values["memory_key"],
                field="memory_key",
            ),
            "memory_type": self._normalize_identifier(
                values["memory_type"],
                field="memory_type",
            ),
            "memory_value": values["memory_value"].strip(),
        }
        if not normalized["memory_value"]:
            raise InvalidMemoryQueryError("memory_value cannot be blank.")
        return self._repository.upsert(normalized)

    def update(self, memory_id: UUID, values: dict[str, Any]) -> Memory:
        memory = self._require_any(memory_id)
        for field in ("memory_value", "memory_type", "importance", "confidence"):
            if field in values and values[field] is None:
                raise InvalidMemoryQueryError(f"{field} cannot be null.")
        if "memory_value" in values:
            values["memory_value"] = values["memory_value"].strip()
            if not values["memory_value"]:
                raise InvalidMemoryQueryError("memory_value cannot be blank.")
        if "memory_type" in values:
            values["memory_type"] = self._normalize_identifier(
                values["memory_type"],
                field="memory_type",
            )
        return self._repository.update(memory, values)

    def deactivate(self, memory_id: UUID) -> Memory:
        return self._repository.set_active(self._require_any(memory_id), active=False)

    def reactivate(self, memory_id: UUID) -> Memory:
        return self._repository.set_active(self._require_any(memory_id), active=True)

    def delete(self, memory_id: UUID) -> None:
        self._repository.delete(self._require_any(memory_id))

    def _require_any(self, memory_id: UUID) -> Memory:
        memory = self._repository.get_any(memory_id)
        if memory is None:
            raise MemoryNotFoundError("Memory not found.")
        return memory
