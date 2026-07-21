"""Payload parser for TikTok."""

from __future__ import annotations

from typing import Any, Mapping, TypeVar

from friday.app.tiktok.schemas.entities import (
    TikTokProfileEntity, TikTokVideoEntity, TikTokShortEntity, TikTokCommentEntity
)

EntityT = TypeVar("EntityT")


class TikTokParser:
    """Convert raw payloads into typed TikTok entities."""

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

    def parse_profile(self, payload: Mapping[str, Any]) -> TikTokProfileEntity:
        return self._build_entity(payload=payload, entity_cls=TikTokProfileEntity, default_kind="profile")

    def parse_video(self, payload: Mapping[str, Any]) -> TikTokVideoEntity:
        return self._build_entity(payload=payload, entity_cls=TikTokVideoEntity, default_kind="video")

    def parse_short(self, payload: Mapping[str, Any]) -> TikTokShortEntity:
        return self._build_entity(payload=payload, entity_cls=TikTokShortEntity, default_kind="short")

    def parse_comment(self, payload: Mapping[str, Any]) -> TikTokCommentEntity:
        return self._build_entity(payload=payload, entity_cls=TikTokCommentEntity, default_kind="comment")
