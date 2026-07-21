from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class AgentResponse(BaseModel):
    data: dict[str, Any]
