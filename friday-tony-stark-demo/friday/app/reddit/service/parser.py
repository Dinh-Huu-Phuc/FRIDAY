"""Payload parser for Reddit."""

from __future__ import annotations

from typing import Any, Mapping, TypeVar

from friday.app.reddit.schemas.entities import (
    RedditSubredditEntity, RedditPostEntity, RedditCommentEntity, RedditThreadEntity
)

EntityT = TypeVar("EntityT")


class RedditParser:
    """Convert raw payloads into typed Reddit entities."""

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

    def parse_subreddit(self, payload: Mapping[str, Any]) -> RedditSubredditEntity:
        return self._build_entity(payload=payload, entity_cls=RedditSubredditEntity, default_kind="subreddit")

    def parse_post(self, payload: Mapping[str, Any]) -> RedditPostEntity:
        return self._build_entity(payload=payload, entity_cls=RedditPostEntity, default_kind="post")

    def parse_comment(self, payload: Mapping[str, Any]) -> RedditCommentEntity:
        return self._build_entity(payload=payload, entity_cls=RedditCommentEntity, default_kind="comment")

    def parse_thread(self, payload: Mapping[str, Any]) -> RedditThreadEntity:
        return self._build_entity(payload=payload, entity_cls=RedditThreadEntity, default_kind="thread")
