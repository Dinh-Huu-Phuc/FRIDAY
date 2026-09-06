from __future__ import annotations

from dataclasses import dataclass, field

from friday.app.perception.world.schemas import WorldRelation, WorldSnapshot


@dataclass(slots=True)
class WorldState:
    """Current relations and lifecycle metadata, guarded by the WorldModel lock."""

    relations: dict[tuple[str, str, str], WorldRelation] = field(default_factory=dict)
    last_updated_at: float = 0.0
    camera_status: str = "idle"


def summarize_world(
    snapshot: WorldSnapshot,
    *,
    now: float,
    question: str = "",
    max_chars: int = 2400,
    max_entities: int = 8,
    max_events: int = 6,
) -> str:
    """Bounded prompt context; image-relative locations are never invented desks."""
    if not snapshot.entities or max_chars <= 0:
        return ""
    max_chars = min(max_chars, 4000)
    question = question.casefold()
    entities = sorted(
        snapshot.entities,
        key=lambda entity: (
            entity.label.casefold() not in question,
            entity.presence.value != "visible",
            -entity.last_seen_at,
            entity.entity_id,
        ),
    )[: min(16, max(1, max_entities))]
    selected = {entity.entity_id for entity in entities}
    lines = [
        f"Current world (camera {snapshot.camera_status}; positions are image-relative):"
    ]
    for entity in entities:
        presence = {
            "visible": "visible",
            "occluded": "temporarily not visible (occluded)",
            "absent": "not currently visible",
            "unknown": "visibility unknown (camera interrupted)",
        }[entity.presence.value]
        age = max(0, int(now - entity.last_seen_at))
        line = (
            f"- {entity.entity_id} ({entity.label}): {presence}; last seen at "
            f"{entity.last_known_position}, {age}s ago; confidence {entity.confidence:.2f}."
        )
        if entity.last_relation_summary:
            line += f" Last relation: {entity.last_relation_summary}."
        lines.append(line)
    if len(snapshot.entities) > len(entities):
        lines.append(
            f"- {len(snapshot.entities) - len(entities)} other remembered entities omitted."
        )
    for relation in snapshot.relations:
        if relation.subject_entity_id in selected:
            lines.append(
                f"- {relation.subject_entity_id}: {relation.relation_type} ({relation.hand_reference or relation.object_entity_id})."
            )
    events = [event for event in snapshot.recent_events if event.entity_id in selected]
    if events and max_events > 0:
        lines.append("Recent history:")
        for event in events[-min(12, max_events) :]:
            lines.append(
                f"- {max(0, int(now - event.occurred_at))}s ago: {event.description}"
            )
    result = "\n".join(lines)
    if len(result) <= max_chars:
        return result
    marker = "\n[World context truncated]"
    return result[: max(0, max_chars - len(marker))] + marker[:max_chars]
