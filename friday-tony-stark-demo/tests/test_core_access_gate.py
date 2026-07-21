from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool

from friday.core.db import (
    CoreAccessCredential,
    CoreAccessGate,
    CoreCredentialStore,
    CredentialAlreadyConfiguredError,
    InvalidPasswordError,
    PasswordConfirmationError,
)
from friday.src.db.base import Base
from friday.src.UI.routes import mount_web_ui_static, router


@pytest.fixture
def credential_store() -> CoreCredentialStore:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[CoreAccessCredential.__table__])
    return CoreCredentialStore(engine)


def test_setup_stores_only_a_hash_and_cannot_run_twice(
    credential_store: CoreCredentialStore,
) -> None:
    gate = CoreAccessGate(credential_store)
    password = "Friday-Private-2049"

    token = gate.setup(password, password)

    assert gate.is_unlocked(token)
    assert credential_store.verify(password)
    with credential_store._engine.connect() as connection:
        stored_hash = connection.execute(
            select(CoreAccessCredential.password_hash)
        ).scalar_one()
    assert password not in stored_hash
    with pytest.raises(CredentialAlreadyConfiguredError):
        gate.setup("Another-Password-2049", "Another-Password-2049")


def test_setup_rejects_mismatch_and_short_password(
    credential_store: CoreCredentialStore,
) -> None:
    gate = CoreAccessGate(credential_store)

    with pytest.raises(PasswordConfirmationError):
        gate.setup("Friday-Private-2049", "different")
    with pytest.raises(InvalidPasswordError):
        gate.setup("short", "short")
    assert not credential_store.is_configured()


def test_sessions_do_not_survive_a_new_gate_process(
    credential_store: CoreCredentialStore,
) -> None:
    first_process = CoreAccessGate(credential_store)
    token = first_process.setup("Friday-Private-2049", "Friday-Private-2049")

    restarted_process = CoreAccessGate(credential_store)

    assert first_process.is_unlocked(token)
    assert not restarted_process.is_unlocked(token)
    with pytest.raises(InvalidPasswordError):
        restarted_process.unlock("wrong-password")
    new_token = restarted_process.unlock("Friday-Private-2049")
    assert restarted_process.is_unlocked(new_token)


def test_ui_redirects_until_the_current_process_is_unlocked(
    credential_store: CoreCredentialStore,
    tmp_path,
) -> None:
    first_process = CoreAccessGate(credential_store)
    core_video = tmp_path / "FRIDAY.mp4"
    core_video.write_bytes(b"friday-video-test")
    clone_icon = tmp_path / "clone.svg"
    clone_icon.write_text("<svg></svg>", encoding="utf-8")
    app = FastAPI()
    app.include_router(router)

    with patch(
        "friday.src.UI.routes.get_core_access_gate",
        return_value=first_process,
    ), patch("friday.src.UI.routes.CORE_VIDEO_PATH", core_video), patch(
        "friday.src.UI.routes.CLONE_ICON_PATH", clone_icon
    ):
        client = TestClient(app)
        locked = client.get("/ui", follow_redirects=False)
        assert locked.status_code == 303
        assert locked.headers["location"] == "/ui/unlock"
        assert client.get("/ui/media/core-video").status_code == 401

        setup = client.post(
            "/ui/access/setup",
            json={
                "password": "Friday-Private-2049",
                "confirmation": "Friday-Private-2049",
            },
        )
        assert setup.status_code == 200
        assert setup.cookies.get("friday_core_session")
        ui = client.get("/ui")
        assert ui.status_code == 200
        assert 'value="orb"' in ui.text
        assert 'value="video"' in ui.text
        assert 'id="auto-sleep-minutes"' in ui.text
        assert 'id="apply-auto-sleep"' in ui.text
        assert 'id="mic-waveform"' in ui.text
        assert 'data-src="/ui/media/core-video?v=20260717"' in ui.text
        assert "/ui/static/vendor/katex/katex.min.css?v=0.17.0" in ui.text
        assert "/ui/static/vendor/katex/katex.min.js?v=0.17.0" in ui.text
        assert "/ui/static/vendor/katex/contrib/auto-render.min.js?v=0.17.0" in ui.text
        icon = client.get("/ui/assets/icons/clone.svg")
        assert icon.status_code == 200
        assert icon.headers["content-type"].startswith("image/svg+xml")
        assert icon.content == b"<svg></svg>"
        media = client.get("/ui/media/core-video")
        assert media.status_code == 200
        assert media.headers["content-type"] == "video/mp4"
        assert media.content == b"friday-video-test"

    restarted_process = CoreAccessGate(credential_store)
    with patch(
        "friday.src.UI.routes.get_core_access_gate",
        return_value=restarted_process,
    ):
        locked_after_restart = client.get("/ui", follow_redirects=False)
        assert locked_after_restart.status_code == 303


def test_chat_math_assets_are_served_by_the_ui_static_mount() -> None:
    app = FastAPI()
    mount_web_ui_static(app)
    client = TestClient(app)

    assert client.get("/ui/static/vendor/katex/katex.min.css").status_code == 200
    assert client.get("/ui/static/vendor/katex/katex.min.js").status_code == 200
    assert (
        client.get("/ui/static/vendor/katex/contrib/auto-render.min.js").status_code
        == 200
    )
    font = client.get("/ui/static/vendor/katex/fonts/KaTeX_Main-Regular.woff2")
    assert font.status_code == 200
    assert font.headers["content-type"] == "font/woff2"
    core_script = client.get("/ui/static/Core_UI/app.js")
    assert core_script.status_code == 200
    assert b"/api/v1/agent/stt" in core_script.content
    assert b"getUserMedia" in core_script.content
    assert b"AudioWorkletNode" in core_script.content
    assert b"mic-level-processor.js" in core_script.content
    worklet = client.get("/ui/static/Core_UI/mic-level-processor.js")
    assert worklet.status_code == 200
    assert b'registerProcessor("friday-mic-level"' in worklet.content
