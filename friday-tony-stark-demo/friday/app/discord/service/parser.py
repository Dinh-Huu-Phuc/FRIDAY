"""Payload parser for Discord."""

from __future__ import annotations

from typing import Any, Mapping, TypeVar

from friday.app.discord.schemas.entities import (
    DiscordGuildEntity, DiscordMessageEntity, DiscordChannelEntity, DiscordThreadEntity
)

EntityT = TypeVar("EntityT")


class DiscordParser:
    """Convert raw payloads into typed Discord entities."""

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

    def parse_guild(self, payload: Mapping[str, Any]) -> DiscordGuildEntity:
        return self._build_entity(payload=payload, entity_cls=DiscordGuildEntity, default_kind="guild")

    def parse_message(self, payload: Mapping[str, Any]) -> DiscordMessageEntity:
        return self._build_entity(payload=payload, entity_cls=DiscordMessageEntity, default_kind="message")

    def parse_channel(self, payload: Mapping[str, Any]) -> DiscordChannelEntity:
        return self._build_entity(payload=payload, entity_cls=DiscordChannelEntity, default_kind="channel")

    def parse_thread(self, payload: Mapping[str, Any]) -> DiscordThreadEntity:
        return self._build_entity(payload=payload, entity_cls=DiscordThreadEntity, default_kind="thread")
