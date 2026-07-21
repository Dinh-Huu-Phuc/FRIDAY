"""Low-level client for Facebook operations."""

from __future__ import annotations

from typing import Any, Mapping

from friday.app.common.browser import BrowserManager, TabOpenResult
from friday.app.facebook.config.settings import FacebookSettings
from friday.app.facebook.exceptions import (
    FacebookConfigurationError,
    FacebookWebhookSignatureError,
    FacebookWebhookVerificationError,
)
from friday.app.facebook.schemas.requests import (
    CheckMessagesRequest,
    CheckNotificationsRequest,
    GetPostDetailRequest,
    GetProfileRequest,
    PublishContentRequest,
    ReceiveWebhookRequest,
    SearchContentRequest,
    VerifyWebhookRequest,
)
from friday.app.facebook.service.store import FacebookWebhookStore
from friday.app.facebook.utils.helpers import (
    build_event_description,
    build_resource_url,
    classify_change_event,
    classify_messaging_event,
    coerce_timestamp_ms,
    is_valid_signature,
    normalize_identifier,
    serialize_payload,
)


class FacebookClient:
    """Thin client that prepares low-level payloads for Facebook."""

    def __init__(
        self,
        *,
        settings: FacebookSettings,
        store: FacebookWebhookStore,
        browser_manager: BrowserManager | None = None,
    ) -> None:
        self.settings = settings
        self.store = store
        self.browser_manager = browser_manager or BrowserManager()

    def open_homepage(self) -> TabOpenResult:
        return self.browser_manager.open_url(
            platform_name=self.settings.platform_name,
            url=self.settings.website_url,
        )

    def get_profile(self, request: GetProfileRequest) -> dict[str, object]:
        identifier = normalize_identifier(request.identifier or request.username or self.settings.platform_name)
        return {
            "id": identifier,
            "url": build_resource_url(self.settings.website_url, "page", identifier),
            "label": f"Facebook Page {identifier}",
            "description": "Mock profile payload prepared for service-level parsing.",
            "metadata": {
                "include_related": request.include_related,
                "lookup_username": request.username,
            },
        }

    def search_content(self, request: SearchContentRequest) -> list[dict[str, object]]:
        query_token = normalize_identifier(request.query or self.settings.platform_name)
        limit = max(1, min(request.limit, 10))
        return [
            {
                "id": f"post-{index}-{query_token}",
                "url": build_resource_url(
                    self.settings.website_url,
                    "post",
                    f"{query_token}-{index}",
                ),
                "label": f"Facebook Post {index}",
                "description": f"Search result for '{request.query}'.",
                "metadata": {
                    "query": request.query,
                    "filters": dict(request.filters),
                },
            }
            for index in range(1, limit + 1)
        ]

    def get_post_detail(self, request: GetPostDetailRequest) -> dict[str, object]:
        content_id = normalize_identifier(request.content_id or "post")
        return {
            "id": content_id,
            "url": build_resource_url(self.settings.website_url, "post", content_id),
            "label": f"Facebook Post {content_id}",
            "description": "Mock detail payload prepared for parser mapping.",
            "metadata": {
                "expand_comments": request.expand_comments,
            },
        }

    def publish_content(self, request: PublishContentRequest) -> dict[str, object]:
        draft_id = normalize_identifier(request.title or "draft")
        return {
            "id": f"draft-{draft_id}",
            "url": build_resource_url(self.settings.website_url, "post", f"draft-{draft_id}"),
            "label": request.title or "Facebook Draft",
            "description": request.body,
            "metadata": {
                "visibility": request.visibility,
                "attachments": list(request.attachments),
            },
        }

    def verify_webhook(self, request: VerifyWebhookRequest) -> dict[str, object]:
        if str(request.object_type or "").strip().lower() != self.settings.webhook_object:
            raise FacebookWebhookVerificationError("Unsupported webhook object for Facebook.")
        if str(request.mode or "").strip().lower() != "subscribe":
            raise FacebookWebhookVerificationError("Unsupported webhook subscribe mode.")
        if not self.settings.verify_token.strip():
            raise FacebookConfigurationError("FACEBOOK_VERIFY_TOKEN is not configured.")
        if request.verify_token != self.settings.verify_token:
            raise FacebookWebhookVerificationError("Facebook verify token does not match.")
        return {
            "verified": True,
            "challenge": request.challenge,
            "message": "Facebook webhook verified.",
        }

    def ingest_webhook(self, request: ReceiveWebhookRequest) -> dict[str, object]:
        payload = request.payload
        if str(payload.get("object") or "").strip().lower() != self.settings.webhook_object:
            raise FacebookWebhookVerificationError("Unsupported Facebook webhook payload.")

        if request.signature:
            if not self.settings.app_secret.strip():
                raise FacebookConfigurationError("FACEBOOK_APP_SECRET is required to validate signatures.")
            payload_bytes = request.raw_body.encode("utf-8") if request.raw_body else serialize_payload(payload)
            if not is_valid_signature(
                app_secret=self.settings.app_secret,
                payload_bytes=payload_bytes,
                signature=request.signature,
            ):
                raise FacebookWebhookSignatureError("Facebook webhook signature is invalid.")

        messages: list[dict[str, Any]] = []
        notifications: list[dict[str, Any]] = []
        events: list[dict[str, Any]] = []

        for entry in payload.get("entry", []):
            if not isinstance(entry, Mapping):
                continue
            page_id = str(entry.get("id") or self.settings.page_id or "").strip()
            entry_time = coerce_timestamp_ms(entry.get("time"))

            for messaging_event in entry.get("messaging", []):
                if not isinstance(messaging_event, Mapping):
                    continue
                event_type = classify_messaging_event(messaging_event)
                sender_id = str((messaging_event.get("sender") or {}).get("id") or "").strip()
                recipient_id = str((messaging_event.get("recipient") or {}).get("id") or "").strip()
                timestamp_ms = coerce_timestamp_ms(messaging_event.get("timestamp")) or entry_time
                message_payload = messaging_event.get("message")
                message_id = ""
                if isinstance(message_payload, Mapping):
                    message_id = str(message_payload.get("mid") or "").strip()
                event_id = normalize_identifier(message_id or f"{page_id}-{event_type}-{sender_id}-{timestamp_ms}")
                description = build_event_description(messaging_event)
                events.append(
                    {
                        "id": event_id,
                        "page_id": page_id,
                        "event_type": event_type,
                        "timestamp_ms": timestamp_ms,
                        "description": description,
                        "kind": "webhook_event",
                        "metadata": {"source": "messaging", "raw": dict(messaging_event)},
                    }
                )

                if event_type == "message":
                    text_value = ""
                    if isinstance(message_payload, Mapping):
                        text_value = str(message_payload.get("text") or "").strip()
                    messages.append(
                        {
                            "id": event_id,
                            "url": self.settings.website_url,
                            "label": f"Messenger message from {sender_id or 'unknown'}",
                            "sender_id": sender_id,
                            "recipient_id": recipient_id,
                            "text": text_value,
                            "description": description,
                            "conversation_id": sender_id or recipient_id,
                            "page_id": page_id,
                            "timestamp_ms": timestamp_ms,
                            "kind": "message",
                            "metadata": {
                                "source": "messenger_webhook",
                                "is_read": False,
                                "raw": dict(messaging_event),
                            },
                        }
                    )
                else:
                    notifications.append(
                        {
                            "id": event_id,
                            "url": self.settings.website_url,
                            "label": f"Messenger {event_type}",
                            "event_type": event_type,
                            "description": description,
                            "page_id": page_id,
                            "actor_id": sender_id or recipient_id,
                            "timestamp_ms": timestamp_ms,
                            "kind": "notification",
                            "metadata": {
                                "source": "messenger_webhook",
                                "raw": dict(messaging_event),
                            },
                        }
                    )

            for change in entry.get("changes", []):
                if not isinstance(change, Mapping):
                    continue
                event_type = classify_change_event(change)
                timestamp_ms = entry_time
                event_id = normalize_identifier(f"{page_id}-{event_type}-{timestamp_ms}")
                description = build_event_description(change)
                change_value = change.get("value")
                actor_id = ""
                if isinstance(change_value, Mapping):
                    actor_id = str(change_value.get("from") or "").strip()
                events.append(
                    {
                        "id": event_id,
                        "page_id": page_id,
                        "event_type": event_type,
                        "timestamp_ms": timestamp_ms,
                        "description": description,
                        "kind": "webhook_event",
                        "metadata": {"source": "changes", "raw": dict(change)},
                    }
                )
                notifications.append(
                    {
                        "id": event_id,
                        "url": self.settings.website_url,
                        "label": f"Facebook {event_type}",
                        "event_type": event_type,
                        "description": description,
                        "page_id": page_id,
                        "actor_id": actor_id,
                        "timestamp_ms": timestamp_ms,
                        "kind": "notification",
                        "metadata": {
                            "source": "page_change_webhook",
                            "raw": dict(change),
                        },
                    }
                )

        return {
            "messages": messages,
            "notifications": notifications,
            "events": events,
            "accepted": True,
            "message": "Facebook webhook accepted.",
        }

    def persist_webhook_records(
        self,
        *,
        messages: list[dict[str, Any]],
        notifications: list[dict[str, Any]],
        events: list[dict[str, Any]],
    ) -> None:
        self.store.append(
            messages=messages,
            notifications=notifications,
            events=events,
        )

    def list_messages(self, request: CheckMessagesRequest) -> list[dict[str, object]]:
        return self.store.list_messages(
            limit=request.limit,
            unread_only=request.unread_only,
            sender_id=request.sender_id,
        )

    def list_notifications(self, request: CheckNotificationsRequest) -> list[dict[str, object]]:
        return self.store.list_notifications(limit=request.limit, event_types=request.event_types)
