from __future__ import annotations

import os

import httpx


def _error_payload(exc: Exception) -> dict[str, object]:
    return {"ok": False, "error": str(exc)}


def _api_base_url() -> str:
    return os.getenv("FRIDAY_SPATIAL_API_BASE_URL", "http://127.0.0.1:8001/api/v1/spatial").rstrip("/")


def _request(method: str, path: str, *, json: dict[str, object] | None = None) -> dict[str, object]:
    with httpx.Client(timeout=5.0) as client:
        response = client.request(method, f"{_api_base_url()}{path}", json=json)
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {"data": payload}


def enable_spatial_mode() -> dict[str, object]:
    """Enable FRIDAY Spatial Control mode through the Spatial API."""
    try:
        return {"ok": True, "state": _request("POST", "/start", json={"mode": "hand_tracking"})}
    except Exception as exc:
        return _error_payload(exc)


def disable_spatial_mode() -> dict[str, object]:
    """Disable Spatial Control mode through the Spatial API."""
    try:
        return {"ok": True, "state": _request("POST", "/stop")}
    except Exception as exc:
        return _error_payload(exc)


def get_spatial_status() -> dict[str, object]:
    """Return the current Spatial Control session state from the Spatial API."""
    try:
        return {"ok": True, "status": _request("GET", "/status")}
    except Exception as exc:
        return _error_payload(exc)


def set_spatial_mode(mode: str) -> dict[str, object]:
    """Change the active Spatial Control mode through the Spatial API."""
    try:
        return {"ok": True, "state": _request("POST", "/mode", json={"mode": mode})}
    except Exception as exc:
        return _error_payload(exc)


def load_spatial_model(model_id: str) -> dict[str, object]:
    """Record a requested model load for the spatial scene renderer."""
    try:
        return {"ok": True, "model_id": model_id, "action": "load_model"}
    except Exception as exc:
        return _error_payload(exc)


def trigger_exploded_view(model_id: str) -> dict[str, object]:
    """Request an exploded-view transition for a spatial model."""
    try:
        return {"ok": True, "model_id": model_id, "action": "explode_model"}
    except Exception as exc:
        return _error_payload(exc)


def reset_spatial_scene() -> dict[str, object]:
    """Request the pageClient spatial scene to reset to its default state."""
    try:
        return {"ok": True, "action": "reset_scene"}
    except Exception as exc:
        return _error_payload(exc)
