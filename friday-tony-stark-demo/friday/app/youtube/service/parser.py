"""Payload parser for YouTube."""

from __future__ import annotations

from typing import Any, Mapping, TypeVar

from friday.app.youtube.schemas.entities import (
    YouTubeChannelEntity, YouTubeVideoEntity, YouTubePlaylistEntity, YouTubeCommentEntity
)

EntityT = TypeVar("EntityT")


class YouTubeParser:
    """Convert raw payloads into typed YouTube entities."""

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

    def parse_channel(self, payload: Mapping[str, Any]) -> YouTubeChannelEntity:
        return self._build_entity(payload=payload, entity_cls=YouTubeChannelEntity, default_kind="channel")

    def parse_video(self, payload: Mapping[str, Any]) -> YouTubeVideoEntity:
        return self._build_entity(payload=payload, entity_cls=YouTubeVideoEntity, default_kind="video")

    def parse_playlist(self, payload: Mapping[str, Any]) -> YouTubePlaylistEntity:
        return self._build_entity(payload=payload, entity_cls=YouTubePlaylistEntity, default_kind="playlist")

    def parse_comment(self, payload: Mapping[str, Any]) -> YouTubeCommentEntity:
        return self._build_entity(payload=payload, entity_cls=YouTubeCommentEntity, default_kind="comment")
