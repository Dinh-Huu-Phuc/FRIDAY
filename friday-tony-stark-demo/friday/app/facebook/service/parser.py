"""Payload parser for Facebook."""

from __future__ import annotations

from typing import Any, Mapping, TypeVar

from friday.app.facebook.schemas.entities import (
    FacebookCommentEntity,
    FacebookMessageEntity,
    FacebookNotificationEntity,
    FacebookPageEntity,
    FacebookPostEntity,
    FacebookReactionEntity,
    FacebookWebhookEventEntity,
)

EntityT = TypeVar("EntityT")


class FacebookParser:
    """Convert raw payloads into typed Facebook entities."""

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

    def parse_page(self, payload: Mapping[str, Any]) -> FacebookPageEntity:
        return self._build_entity(payload=payload, entity_cls=FacebookPageEntity, default_kind="page")

    def parse_post(self, payload: Mapping[str, Any]) -> FacebookPostEntity:
        return self._build_entity(payload=payload, entity_cls=FacebookPostEntity, default_kind="post")

    def parse_comment(self, payload: Mapping[str, Any]) -> FacebookCommentEntity:
        return self._build_entity(payload=payload, entity_cls=FacebookCommentEntity, default_kind="comment")

    def parse_reaction(self, payload: Mapping[str, Any]) -> FacebookReactionEntity:
        return self._build_entity(payload=payload, entity_cls=FacebookReactionEntity, default_kind="reaction")

    def parse_message(self, payload: Mapping[str, Any]) -> FacebookMessageEntity:
        identifier = str(payload.get("id") or "message").strip() or "message"
        return FacebookMessageEntity(
            id=identifier,
            url=str(payload.get("url") or "").strip(),
            label=str(payload.get("label") or identifier).strip(),
            sender_id=str(payload.get("sender_id") or "").strip(),
            recipient_id=str(payload.get("recipient_id") or "").strip(),
            text=str(payload.get("text") or "").strip(),
            description=str(payload.get("description") or "").strip(),
            conversation_id=str(payload.get("conversation_id") or "").strip(),
            page_id=str(payload.get("page_id") or "").strip(),
            timestamp_ms=int(payload.get("timestamp_ms") or 0),
            kind=str(payload.get("kind") or "message").strip() or "message",
            metadata=dict(payload.get("metadata") or {}),
        )

    def parse_notification(self, payload: Mapping[str, Any]) -> FacebookNotificationEntity:
        identifier = str(payload.get("id") or "notification").strip() or "notification"
        return FacebookNotificationEntity(
            id=identifier,
            url=str(payload.get("url") or "").strip(),
            label=str(payload.get("label") or identifier).strip(),
            event_type=str(payload.get("event_type") or "notification").strip() or "notification",
            description=str(payload.get("description") or "").strip(),
            page_id=str(payload.get("page_id") or "").strip(),
            actor_id=str(payload.get("actor_id") or "").strip(),
            timestamp_ms=int(payload.get("timestamp_ms") or 0),
            kind=str(payload.get("kind") or "notification").strip() or "notification",
            metadata=dict(payload.get("metadata") or {}),
        )

    def parse_webhook_event(self, payload: Mapping[str, Any]) -> FacebookWebhookEventEntity:
        identifier = str(payload.get("id") or "webhook-event").strip() or "webhook-event"
        return FacebookWebhookEventEntity(
            id=identifier,
            page_id=str(payload.get("page_id") or "").strip(),
            event_type=str(payload.get("event_type") or "event").strip() or "event",
            timestamp_ms=int(payload.get("timestamp_ms") or 0),
            description=str(payload.get("description") or "").strip(),
            kind=str(payload.get("kind") or "webhook_event").strip() or "webhook_event",
            metadata=dict(payload.get("metadata") or {}),
        )
