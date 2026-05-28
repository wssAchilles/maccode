from __future__ import annotations

from fastapi import APIRouter, WebSocket

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/stream")
async def stream(websocket: WebSocket) -> None:
    await websocket.accept()
    report = websocket.app.state.runtime.get_realtime_report()
    await websocket.send_json({"type": "frame_report", "data": report})
    await websocket.close()
