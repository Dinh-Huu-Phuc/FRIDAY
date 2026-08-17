from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from friday.core.memory_database.models import Memory
from friday.src.db.base import Base
from friday.src.dependencies.database import get_db
from friday.src.router.v1.memories.routes import router


@pytest.fixture
def memory_api() -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Memory.__table__])
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    def override_get_db() -> Generator[Session, None, None]:
        with session_factory() as db:
            yield db

    app = FastAPI()
    app.include_router(router, prefix="/memories")
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, session_factory
    engine.dispose()


def _birthday_payload(**overrides) -> dict:
    payload = {
        "subject": "FRIDAY",
        "memory_key": "official_birthday",
        "memory_value": "15/04/2026",
        "memory_type": "identity",
        "importance": 1.0,
        "confidence": 1.0,
    }
    payload.update(overrides)
    return payload


def test_upsert_replaces_conflicting_memory_without_creating_a_duplicate(
    memory_api,
) -> None:
    client, session_factory = memory_api

    first = client.post("/memories", json=_birthday_payload())
    second = client.post(
        "/memories",
        json=_birthday_payload(
            subject="  friday  ",
            memory_key=" OFFICIAL_BIRTHDAY ",
            memory_value="April 15, 2026",
            confidence=0.95,
        ),
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["memory_value"] == "April 15, 2026"
    assert second.json()["confidence"] == 0.95
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(Memory)) == 1


def test_request_validation_rejects_scores_and_client_user_id(memory_api) -> None:
    client, _ = memory_api

    invalid_score = client.post(
        "/memories",
        json=_birthday_payload(importance=1.1),
    )
    injected_owner = client.post(
        "/memories",
        json=_birthday_payload(user_id="not-accepted"),
    )

    assert invalid_score.status_code == 422
    assert injected_owner.status_code == 422


def test_inactive_and_expired_memories_are_hidden_by_default(memory_api) -> None:
    client, _ = memory_api
    expired_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    active = client.post("/memories", json=_birthday_payload()).json()
    expired = client.post(
        "/memories",
        json=_birthday_payload(
            memory_key="temporary_fact",
            expires_at=expired_at.isoformat(),
        ),
    ).json()
    deactivated = client.post(f"/memories/{active['id']}/deactivate")

    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False
    assert client.get("/memories").json() == []
    assert client.get(f"/memories/{active['id']}").status_code == 404
    assert client.get(f"/memories/{expired['id']}").status_code == 404

    all_rows = client.get(
        "/memories?include_inactive=true&include_expired=true"
    ).json()
    assert {row["id"] for row in all_rows} == {active["id"], expired["id"]}


def test_memory_can_be_reactivated_updated_and_deleted(memory_api) -> None:
    client, _ = memory_api
    created = client.post("/memories", json=_birthday_payload()).json()

    client.post(f"/memories/{created['id']}/deactivate")
    reactivated = client.post(f"/memories/{created['id']}/reactivate")
    updated = client.patch(
        f"/memories/{created['id']}",
        json={"memory_value": "15 April 2026", "importance": 0.9},
    )
    deleted = client.delete(f"/memories/{created['id']}")

    assert reactivated.status_code == 200
    assert reactivated.json()["is_active"] is True
    assert updated.status_code == 200
    assert updated.json()["memory_value"] == "15 April 2026"
    assert updated.json()["importance"] == 0.9
    assert deleted.status_code == 200
    assert deleted.json() == {"ok": True, "memory_id": created["id"]}
    assert client.get(f"/memories/{created['id']}").status_code == 404


def test_relevant_endpoint_filters_by_normalized_subject_or_type(memory_api) -> None:
    client, _ = memory_api
    client.post("/memories", json=_birthday_payload())
    client.post(
        "/memories",
        json={
            "subject": "boss",
            "memory_key": "preferred_name",
            "memory_value": "Phuc",
            "memory_type": "preference",
        },
    )

    missing_filter = client.get("/memories/relevant")
    by_subject = client.get("/memories/relevant?subject= FRIDAY ")
    by_type = client.get("/memories/relevant?memory_type=preference")

    assert missing_filter.status_code == 422
    assert [row["memory_key"] for row in by_subject.json()] == [
        "official_birthday"
    ]
    assert [row["memory_key"] for row in by_type.json()] == ["preferred_name"]


def test_patch_rejects_empty_or_null_required_updates(memory_api) -> None:
    client, _ = memory_api
    created = client.post("/memories", json=_birthday_payload()).json()

    assert client.patch(f"/memories/{created['id']}", json={}).status_code == 422
    assert (
        client.patch(
            f"/memories/{created['id']}",
            json={"memory_value": None},
        ).status_code
        == 422
    )
