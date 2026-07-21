from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote

import httpx


class SupabaseStorageClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        service_role_key: str | None = None,
        timeout: float = 20.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("SUPABASE_URL", "")).strip().rstrip("/")
        self.service_role_key = (
            service_role_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        ).strip()
        self.timeout = timeout
        self.client = client

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.service_role_key)

    def upload(
        self,
        *,
        bucket: str,
        object_path: str,
        file_path: Path,
        content_type: str,
    ) -> None:
        if not self.configured:
            raise RuntimeError("Supabase screenshot storage is not configured.")
        endpoint = (
            f"{self.base_url}/storage/v1/object/"
            f"{quote(bucket, safe='')}/{quote(object_path, safe='/')}"
        )
        headers = {
            "Authorization": f"Bearer {self.service_role_key}",
            "apikey": self.service_role_key,
            "Content-Type": content_type,
            "x-upsert": "false",
        }
        if self.client is not None:
            response = self.client.post(
                endpoint,
                headers=headers,
                content=file_path.read_bytes(),
            )
            response.raise_for_status()
            return
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                endpoint,
                headers=headers,
                content=file_path.read_bytes(),
            )
            response.raise_for_status()
