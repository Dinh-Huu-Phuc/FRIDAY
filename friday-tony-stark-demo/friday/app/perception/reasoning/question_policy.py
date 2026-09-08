from __future__ import annotations

import re
from dataclasses import dataclass, replace
from enum import Enum

from friday.app.perception.reasoning.schemas import GemmaVisionOutput
from friday.app.perception.scene.schemas import (
    ObjectDepthTrend,
    ObjectMotionState,
    ObjectRelationType,
    TemporalSceneSnapshot,
)
from friday.app.perception.world import WorldPresence, WorldSnapshot
from friday.app.perception.world.world_state import summarize_world

MIN_CONFIDENCE = 0.8
MAX_OBSERVATION_AGE = 2.0


class QuestionKind(str, Enum):
    CURRENT_SCENE = "current_scene"
    CURRENT_RELATION = "current_relation"
    HISTORY = "historical"
    SEMANTIC = "semantic"


@dataclass(frozen=True, slots=True)
class CameraQuestion:
    kind: QuestionKind
    operation: str = ""
    target: str = ""


def classify_camera_question(question: str) -> CameraQuestion:
    q = re.sub(r"[^a-z0-9]+", " ", question.lower()).strip()
    q = re.sub(r"^(?:friday )?(?:please )?", "", q)
    if re.search(
        r"\b(?:where did i (?:leave|put|place)|last (?:seen|known|saw)|earlier|previously|history|remember|what (?:has )?changed)\b",
        q,
    ):
        return CameraQuestion(QuestionKind.HISTORY)
    if re.fullmatch(
        r"what (?:objects (?:can|do) you see|can you see|do you see)(?: (?:on|through|in) (?:the )?(?:camera|webcam))?",
        q,
    ):
        return CameraQuestion(QuestionKind.CURRENT_SCENE, "objects")
    location = re.fullmatch(
        r"where is (?:the |my |that )?([a-z ]+?)(?: (?:on|in) (?:the )?camera)?", q
    )
    if location:
        return CameraQuestion(QuestionKind.CURRENT_SCENE, "location", location[1])
    if re.fullmatch(
        r"(?:what am i holding|is the person holding (?:something|anything))(?: (?:right now|on camera))?",
        q,
    ):
        return CameraQuestion(QuestionKind.CURRENT_RELATION, "holding")
    if re.fullmatch(
        r"is (?:the person|someone) (?:on camera )?moving(?: (?:right now|on camera))?",
        q,
    ):
        return CameraQuestion(QuestionKind.CURRENT_RELATION, "moving")
    if re.fullmatch(r"is (?:someone|anyone|the person) approaching (?:the )?camera", q):
        return CameraQuestion(QuestionKind.CURRENT_RELATION, "approaching")
    return CameraQuestion(QuestionKind.SEMANTIC)


def current_scene_context(scene: TemporalSceneSnapshot | None, *, now: float) -> str:
    if scene is None or scene.status != "ready":
        return "No current structured scene is available."
    objects = [
        obj
        for obj in scene.visible_objects
        if 0 <= now - obj.last_seen_at <= MAX_OBSERVATION_AGE
    ]
    if not objects:
        return "No recent structured observations; use the image for visible evidence."
    lines = [
        f"{obj.label}: {obj.position}, motion {obj.motion.value}, confidence {obj.confidence:.2f}"
        for obj in objects[:8]
    ]
    return (
        "Current detector observations (not semantic actions): " + "; ".join(lines)
    )[:800]


def historical_context(world: WorldSnapshot, question: str, *, now: float) -> str:
    entities = tuple(
        entity
        for entity in world.entities
        if re.search(
            r"\b" + re.escape(entity.label.casefold()) + r"s?\b", question.casefold()
        )
    )
    if not entities and re.search(
        r"\b(?:what (?:has )?changed|history|earlier|previously)\b", question.casefold()
    ):
        entities = world.entities
    if not entities:
        return "No remembered entity matches the named object. Ask which object if the question is ambiguous."
    selected = {entity.entity_id for entity in entities}
    relevant = replace(
        world,
        entities=entities,
        relations=tuple(r for r in world.relations if r.subject_entity_id in selected),
        recent_events=tuple(e for e in world.recent_events if e.entity_id in selected),
    )
    return summarize_world(relevant, now=now, question=question, max_chars=2400)


def structured_answer(
    question: CameraQuestion,
    scene: TemporalSceneSnapshot | None,
    *,
    now: float,
    world: WorldSnapshot | None = None,
) -> GemmaVisionOutput | None:
    """Positive, fresh evidence only. Missing relations never prove a negative.

    Track motion is image-relative, not action recognition. Hands do not carry
    owner identity, so holding answers deliberately do not assign an owner.
    """
    if not question.operation or scene is None or scene.status != "ready":
        return None
    if not 0 <= now - scene.observed_at <= MAX_OBSERVATION_AGE:
        return None
    visible = scene.visible_objects
    reliable = {
        obj.track_id: obj
        for obj in visible
        if obj.confidence >= MIN_CONFIDENCE
        and 0 <= now - obj.last_seen_at <= MAX_OBSERVATION_AGE
    }
    if question.operation == "objects" and reliable:
        labels = sorted({obj.label for obj in reliable.values()})
        return GemmaVisionOutput(
            answer="I can confidently detect: " + ", ".join(labels[:12]) + ".",
            confidence=min(obj.confidence for obj in reliable.values()),
            uncertainty="This lists detected classes, not every possible object in view.",
        )
    if question.operation == "location":
        matches = [obj for obj in visible if obj.label.casefold() == question.target]
        if len(matches) == 1 and matches[0].track_id in reliable:
            obj = matches[0]
            return GemmaVisionOutput(
                answer=f"The detected {obj.label} is at {obj.position} of the camera image.",
                confidence=obj.confidence,
            )
    people = [obj for obj in visible if obj.label == "person"]
    if (
        question.operation == "moving"
        and len(people) == 1
        and people[0].track_id in reliable
    ):
        person = people[0]
        if person.motion == ObjectMotionState.MOVING:
            return GemmaVisionOutput(
                "The tracked person is moving in the camera image.",
                confidence=person.confidence,
            )
        if person.motion == ObjectMotionState.STATIONARY:
            return GemmaVisionOutput(
                "The tracked person's position is stationary. This does not rule out hand or body movements.",
                confidence=person.confidence,
            )
    if question.operation == "approaching":
        approaching = [
            obj
            for obj in reliable.values()
            if obj.label == "person" and obj.depth_trend == ObjectDepthTrend.APPROACHING
        ]
        if approaching:
            return GemmaVisionOutput(
                "A tracked person appears to be approaching the camera, based on their increasing size in the image.",
                confidence=min(obj.confidence for obj in approaching),
            )
    if question.operation == "holding" and len(people) <= 1:
        held = {
            reliable[relation.track_id].label
            for relation in scene.relations
            if relation.relation_type == ObjectRelationType.HELD_BY_HAND
            and relation.confidence >= MIN_CONFIDENCE
            and relation.track_id in reliable
        }
        if isinstance(world, WorldSnapshot):
            entities = {entity.entity_id: entity for entity in world.entities}
            for relation in world.relations:
                entity = entities.get(relation.subject_entity_id)
                if (
                    relation.relation_type == ObjectRelationType.HELD_BY_HAND.value
                    and relation.confidence >= MIN_CONFIDENCE
                    and 0 <= now - relation.last_updated_at <= MAX_OBSERVATION_AGE
                    and entity is not None
                    and entity.presence == WorldPresence.VISIBLE
                    and entity.confidence >= MIN_CONFIDENCE
                    and entity.active_track_id in reliable
                ):
                    held.add(entity.label)
        if held:
            return GemmaVisionOutput(
                "I detect "
                + ", ".join(sorted(held))
                + " held by a hand in view. I cannot verify whose hand it is.",
                confidence=MIN_CONFIDENCE,
                uncertainty="The hand relation does not establish the person's identity or ownership.",
            )
    return None
