from __future__ import annotations

from typing import Any


def ok_response(data: Any = None, message: str = "ok") -> dict[str, Any]:
    return {"ok": True, "message": message, "data": data}
