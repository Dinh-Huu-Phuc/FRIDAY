"""Payload parser for X."""

from __future__ import annotations

from typing import Any, Mapping, TypeVar

from friday.app.x.schemas.entities import (
    XAccountEntity, XTweetEntity, XThreadEntity, XReplyEntity
)

EntityT = TypeVar("EntityT")


class XParser:
    """Convert raw payloads into typed X entities."""

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

    def parse_account(self, payload: Mapping[str, Any]) -> XAccountEntity:
        return self._build_entity(payload=payload, entity_cls=XAccountEntity, default_kind="account")

    def parse_tweet(self, payload: Mapping[str, Any]) -> XTweetEntity:
        return self._build_entity(payload=payload, entity_cls=XTweetEntity, default_kind="tweet")

    def parse_thread(self, payload: Mapping[str, Any]) -> XThreadEntity:
        return self._build_entity(payload=payload, entity_cls=XThreadEntity, default_kind="thread")

    def parse_reply(self, payload: Mapping[str, Any]) -> XReplyEntity:
        return self._build_entity(payload=payload, entity_cls=XReplyEntity, default_kind="reply")
