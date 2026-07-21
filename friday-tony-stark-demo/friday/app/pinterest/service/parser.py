"""Payload parser for Pinterest."""

from __future__ import annotations

from typing import Any, Mapping, TypeVar

from friday.app.pinterest.schemas.entities import (
    PinterestProfileEntity, PinterestPinEntity, PinterestBoardEntity, PinterestCommentEntity
)

EntityT = TypeVar("EntityT")


class PinterestParser:
    """Convert raw payloads into typed Pinterest entities."""

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

    def parse_profile(self, payload: Mapping[str, Any]) -> PinterestProfileEntity:
        return self._build_entity(payload=payload, entity_cls=PinterestProfileEntity, default_kind="profile")

    def parse_pin(self, payload: Mapping[str, Any]) -> PinterestPinEntity:
        return self._build_entity(payload=payload, entity_cls=PinterestPinEntity, default_kind="pin")

    def parse_board(self, payload: Mapping[str, Any]) -> PinterestBoardEntity:
        return self._build_entity(payload=payload, entity_cls=PinterestBoardEntity, default_kind="board")

    def parse_comment(self, payload: Mapping[str, Any]) -> PinterestCommentEntity:
        return self._build_entity(payload=payload, entity_cls=PinterestCommentEntity, default_kind="comment")
