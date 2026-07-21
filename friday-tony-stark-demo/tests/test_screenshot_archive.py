from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy import create_engine, select

from friday.app.computer.schemas.entities import ScreenImage, ScreenObservation
from friday.core.db.models import ScreenCaptureAsset, ScreenCaptureRecord
from friday.core.db.repositories import ScreenCaptureRepository
from friday.core.db.services.screenshot_archive_service import ScreenshotArchiveService
from friday.core.db.services.supabase_storage import SupabaseStorageClient
from friday.src.db.base import Base


class FakeStorage:
    configured = True

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.uploads = []

    def upload(self, **kwargs) -> None:
        if self.fail:
            raise RuntimeError("upload failed")
        self.uploads.append(kwargs)


def _observation(tmp_path: Path, count: int = 2) -> ScreenObservation:
    images = []
    for index in range(1, count + 1):
        raw = tmp_path / f"monitor-{index}.png"
        jpeg = tmp_path / f"monitor-{index}.jpg"
        raw.write_bytes(b"raw")
        jpeg.write_bytes(f"jpeg-{index}".encode())
        images.append(
            ScreenImage(
                monitor_index=index,
                screenshot_path=str(raw),
                compressed_screenshot_path=str(jpeg),
                is_active=index == 1,
                left=0,
                top=0,
                width=1920,
                height=1080,
            )
        )
    return ScreenObservation(
        observed_at=datetime.now(timezone.utc),
        screenshot_path=images[0].screenshot_path,
        compressed_screenshot_path=images[0].compressed_screenshot_path,
        active_window_title="Editor",
        screen_width=1920,
        screen_height=1080,
        capture_scope="all",
        screen_images=images,
    )


def _repository(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'archive.db'}")
    Base.metadata.create_all(
        engine,
        tables=[ScreenCaptureRecord.__table__, ScreenCaptureAsset.__table__],
    )
    return engine, ScreenCaptureRepository(engine)


def test_successful_archive_records_metadata_then_removes_local_jpegs(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("FRIDAY_SCREENSHOT_CLOUD_ENABLED", "true")
    engine, repository = _repository(tmp_path)
    storage = FakeStorage()
    observation = _observation(tmp_path)
    service = ScreenshotArchiveService(
        repository=repository,
        storage=storage,
        bucket="private-captures",
    )

    result = service.archive(observation, user_question="Inspect every screen")

    assert result.ok is True
    assert result.uploaded == 2
    assert len(storage.uploads) == 2
    assert all(
        not Path(image.compressed_screenshot_path).exists()
        for image in observation.screen_images
    )
    with engine.connect() as connection:
        status = connection.execute(
            select(ScreenCaptureRecord.status)
        ).scalar_one()
        assets = connection.execute(select(ScreenCaptureAsset.id)).scalars().all()
    assert status == "uploaded"
    assert len(assets) == 2


def test_failed_archive_keeps_local_jpeg_and_marks_record_failed(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("FRIDAY_SCREENSHOT_CLOUD_ENABLED", "true")
    engine, repository = _repository(tmp_path)
    observation = _observation(tmp_path, count=1)
    service = ScreenshotArchiveService(
        repository=repository,
        storage=FakeStorage(fail=True),
    )

    result = service.archive(observation, user_question="What am I viewing?")

    assert result.ok is False
    assert Path(observation.screen_images[0].compressed_screenshot_path).exists()
    with engine.connect() as connection:
        status, error_message = connection.execute(
            select(ScreenCaptureRecord.status, ScreenCaptureRecord.error_message)
        ).one()
    assert status == "failed"
    assert "upload failed" in error_message


def test_storage_client_uses_private_service_role_upload_endpoint(tmp_path) -> None:
    jpeg = tmp_path / "capture.jpg"
    jpeg.write_bytes(b"jpeg-data")
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        storage = SupabaseStorageClient(
            base_url="https://project.supabase.co",
            service_role_key="secret-service-role",
            client=client,
        )
        storage.upload(
            bucket="private bucket",
            object_path="2026/07/18/monitor-1.jpg",
            file_path=jpeg,
            content_type="image/jpeg",
        )

    request = requests[0]
    assert request.url.raw_path.decode().endswith(
        "/storage/v1/object/private%20bucket/2026/07/18/monitor-1.jpg"
    )
    assert request.headers["authorization"] == "Bearer secret-service-role"
    assert request.content == b"jpeg-data"
