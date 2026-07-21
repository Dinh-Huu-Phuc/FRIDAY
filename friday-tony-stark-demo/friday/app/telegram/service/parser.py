"""Payload parser for Telegram."""

from __future__ import annotations

from typing import Any, Mapping, TypeVar

from friday.app.telegram.schemas.entities import (
    TelegramChatEntity, TelegramMessageEntity, TelegramChannelEntity
)

EntityT = TypeVar("EntityT")


class TelegramParser:
    """Convert raw payloads into typed Telegram entities."""

    def _build_entity(
        self,
        *,
        payload: Mapping[str, Any],
        entity_cls: type[EntityT],
        default_kind: str,
    ) -> EntityT:
        identifier = str(payload.get("id") or default_kind).strip() or default_kind
        return entity_cls(
            id=identifier,
            url=str(payload.get("url") or "").strip(),
            label=str(payload.get("label") or identifier).strip(),
            description=str(payload.get("description") or "").strip(),
            kind=str(payload.get("kind") or default_kind).strip() or default_kind,
            metadata=dict(payload.get("metadata") or {}),
        )

    def parse_chat(self, payload: Mapping[str, Any]) -> TelegramChatEntity:
        return self._build_entity(payload=payload, entity_cls=TelegramChatEntity, default_kind="chat")

    def parse_message(self, payload: Mapping[str, Any]) -> TelegramMessageEntity:
        return self._build_entity(payload=payload, entity_cls=TelegramMessageEntity, default_kind="message")

    def parse_channel(self, payload: Mapping[str, Any]) -> TelegramChannelEntity:
        return self._build_entity(payload=payload, entity_cls=TelegramChannelEntity, default_kind="channel")
