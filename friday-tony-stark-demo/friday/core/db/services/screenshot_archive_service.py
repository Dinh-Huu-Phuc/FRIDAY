from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from friday.core.db.repositories import ScreenCaptureRepository
from friday.core.db.services.supabase_storage import SupabaseStorageClient

if TYPE_CHECKING:
    from friday.app.computer.schemas.entities import ScreenObservation


@dataclass(frozen=True, slots=True)
class ScreenshotArchiveResult:
    ok: bool
    capture_id: UUID | None = None
    uploaded: int = 0
    message: str = ""


def screenshot_cloud_enabled() -> bool:
    return os.getenv("FRIDAY_SCREENSHOT_CLOUD_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


class ScreenshotArchiveService:
    def __init__(
        self,
        *,
        repository: ScreenCaptureRepository | None = None,
        storage: SupabaseStorageClient | None = None,
        bucket: str | None = None,
    ) -> None:
        self.repository = repository
        self.storage = storage or SupabaseStorageClient()
        self.bucket = (
            bucket or os.getenv("SUPABASE_SCREENSHOT_BUCKET", "friday-screen-captures")
        ).strip()

    def archive(
        self,
        observation: ScreenObservation,
        *,
        user_question: str,
    ) -> ScreenshotArchiveResult:
        if not screenshot_cloud_enabled() or not self.storage.configured:
            return ScreenshotArchiveResult(False, message="Cloud archive is disabled.")

        images = observation.screen_images
        if not images:
            return ScreenshotArchiveResult(False, message="No monitor images to archive.")

        capture_id = uuid4()
        repository = self.repository or ScreenCaptureRepository()
        uploaded_assets: list[dict] = []
        uploaded_paths: list[Path] = []
        try:
            repository.create_pending(
                capture_id=capture_id,
                captured_at=observation.observed_at,
                user_question=user_question,
                active_window_title=observation.active_window_title,
                monitor_count=len(images),
            )
            date_prefix = observation.observed_at.astimezone(timezone.utc).strftime(
                "%Y/%m/%d"
            )
            for image in images:
                local_path = Path(
                    image.compressed_screenshot_path or image.screenshot_path
                ).resolve()
                object_path = (
                    f"{date_prefix}/{capture_id}/monitor-{image.monitor_index}.jpg"
                )
                self.storage.upload(
                    bucket=self.bucket,
                    object_path=object_path,
                    file_path=local_path,
                    content_type="image/jpeg",
                )
                uploaded_paths.append(local_path)
                uploaded_assets.append(
                    {
                        "id": uuid4(),
                        "capture_id": capture_id,
                        "monitor_index": image.monitor_index,
                        "is_active": image.is_active,
                        "screen_width": image.width,
                        "screen_height": image.height,
                        "storage_bucket": self.bucket,
                        "storage_path": object_path,
                        "original_filename": local_path.name,
                        "mime_type": "image/jpeg",
                        "byte_size": local_path.stat().st_size,
                        "sha256": hashlib.sha256(local_path.read_bytes()).hexdigest(),
                        "uploaded_at": datetime.now(timezone.utc),
                    }
                )
            repository.mark_uploaded(capture_id, uploaded_assets)
        except Exception as exc:
            try:
                repository.mark_failed(capture_id, f"{type(exc).__name__}: {exc}")
            except Exception:
                pass
            return ScreenshotArchiveResult(
                False,
                capture_id=capture_id,
                uploaded=len(uploaded_assets),
                message=f"Screenshot archive failed ({type(exc).__name__}).",
            )

        for local_path in uploaded_paths:
            local_path.unlink(missing_ok=True)
        return ScreenshotArchiveResult(
            True,
            capture_id=capture_id,
            uploaded=len(uploaded_assets),
            message="Screenshot images uploaded to Supabase.",
        )
