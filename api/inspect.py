from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Header
from fastapi.responses import StreamingResponse

from api.support import require_admin
from services.inspect_service import inspect_service


def create_router() -> APIRouter:
    router = APIRouter()

    @router.get("/api/inspect")
    async def get_inspect(authorization: str | None = Header(default=None)):
        require_admin(authorization)
        return {"inspect": inspect_service.get()}

    @router.post("/api/inspect/start")
    async def start_inspect(authorization: str | None = Header(default=None)):
        require_admin(authorization)
        return {"inspect": inspect_service.start()}

    @router.post("/api/inspect/stop")
    async def stop_inspect(authorization: str | None = Header(default=None)):
        require_admin(authorization)
        return {"inspect": inspect_service.stop()}

    @router.get("/api/inspect/events")
    async def inspect_events(token: str = ""):
        require_admin(f"Bearer {token}")

        async def stream():
            last = ""
            while True:
                payload = json.dumps(inspect_service.get(), ensure_ascii=False)
                if payload != last:
                    last = payload
                    yield f"data: {payload}\n\n"
                await asyncio.sleep(0.5)

        return StreamingResponse(stream(), media_type="text/event-stream")

    return router
