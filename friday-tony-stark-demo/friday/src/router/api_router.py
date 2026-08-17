from __future__ import annotations

from fastapi import APIRouter

from friday.src.router.v1.agent.routes import router as agent_router
from friday.src.router.v1.computer.routes import router as computer_router
from friday.src.router.v1.browser_bridge.routes import router as browser_bridge_router
from friday.src.router.v1.health.routes import router as health_router
from friday.src.router.v1.launcher.routes import router as launcher_router
from friday.src.router.v1.memories.routes import router as memories_router
from friday.src.router.v1.rag.routes import router as rag_router
from friday.src.router.v1.runtime.routes import router as runtime_router
from friday.src.router.v1.spatial.routes import router as spatial_router


api_router = APIRouter()
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(agent_router, prefix="/agent", tags=["agent"])
api_router.include_router(computer_router, prefix="/computer", tags=["computer"])
api_router.include_router(browser_bridge_router, prefix="/browser-bridge", tags=["browser-bridge"])
api_router.include_router(launcher_router, prefix="/launcher", tags=["launcher"])
api_router.include_router(memories_router, prefix="/memories", tags=["memories"])
api_router.include_router(runtime_router, prefix="/runtime", tags=["runtime"])
api_router.include_router(rag_router, prefix="/rag", tags=["rag"])
api_router.include_router(spatial_router, prefix="/spatial", tags=["spatial"])
