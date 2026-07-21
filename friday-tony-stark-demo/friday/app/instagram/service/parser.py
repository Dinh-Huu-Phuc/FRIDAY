"""Payload parser for Instagram."""

from __future__ import annotations

from typing import Any, Mapping, TypeVar

from friday.app.instagram.schemas.entities import (
    InstagramProfileEntity, InstagramPostEntity, InstagramReelEntity, InstagramStoryEntity, InstagramCommentEntity
)

EntityT = TypeVar("EntityT")


class InstagramParser:
    """Convert raw payloads into typed Instagram entities."""

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

    def parse_profile(self, payload: Mapping[str, Any]) -> InstagramProfileEntity:
        return self._build_entity(payload=payload, entity_cls=InstagramProfileEntity, default_kind="profile")

    def parse_post(self, payload: Mapping[str, Any]) -> InstagramPostEntity:
        return self._build_entity(payload=payload, entity_cls=InstagramPostEntity, default_kind="post")

    def parse_reel(self, payload: Mapping[str, Any]) -> InstagramReelEntity:
        return self._build_entity(payload=payload, entity_cls=InstagramReelEntity, default_kind="reel")

    def parse_story(self, payload: Mapping[str, Any]) -> InstagramStoryEntity:
        return self._build_entity(payload=payload, entity_cls=InstagramStoryEntity, default_kind="story")

    def parse_comment(self, payload: Mapping[str, Any]) -> InstagramCommentEntity:
        return self._build_entity(payload=payload, entity_cls=InstagramCommentEntity, default_kind="comment")
