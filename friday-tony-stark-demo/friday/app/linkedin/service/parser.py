"""Payload parser for LinkedIn."""

from __future__ import annotations

from typing import Any, Mapping, TypeVar

from friday.app.linkedin.schemas.entities import (
    LinkedInProfileEntity, LinkedInPostEntity, LinkedInCompanyPageEntity, LinkedInCommentEntity
)

EntityT = TypeVar("EntityT")


class LinkedInParser:
    """Convert raw payloads into typed LinkedIn entities."""

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

    def parse_profile(self, payload: Mapping[str, Any]) -> LinkedInProfileEntity:
        return self._build_entity(payload=payload, entity_cls=LinkedInProfileEntity, default_kind="profile")

    def parse_post(self, payload: Mapping[str, Any]) -> LinkedInPostEntity:
        return self._build_entity(payload=payload, entity_cls=LinkedInPostEntity, default_kind="post")

    def parse_company_page(self, payload: Mapping[str, Any]) -> LinkedInCompanyPageEntity:
        return self._build_entity(payload=payload, entity_cls=LinkedInCompanyPageEntity, default_kind="company_page")

    def parse_comment(self, payload: Mapping[str, Any]) -> LinkedInCommentEntity:
        return self._build_entity(payload=payload, entity_cls=LinkedInCommentEntity, default_kind="comment")
