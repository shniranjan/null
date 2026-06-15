"""
Real-time XAPI Event Stream via WebSocket.

WS /api/pools/{pool_id}/events

Clients connect via WebSocket to receive live XAPI events.
Events are polled from XAPI via event.next() and forwarded as JSON.

Messages sent to client:
  {"type": "event", "class": "VM", "operation": "mod", "ref": "...", "timestamp": "..."}
  {"type": "connected", "pool_name": "..."}
  {"type": "error", "message": "..."}

Supports optional class filter via query param: ?classes=VM,host
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect

from app.auth import UserOut, get_current_user
from app.xapi.client import pool_registry

router = APIRouter(prefix="/api/pools/{pool_id}", tags=["events"])


def _get_pool(pool_id: int):
    pc = pool_registry.get(pool_id)
    if not pc or not pc._connected:
        raise HTTPException(status_code=404, detail="Pool not found or not connected")
    return pc


@router.websocket("/events")
async def event_stream(
    websocket: WebSocket,
    pool_id: int,
    classes: Optional[str] = Query(None),
):
    """WebSocket endpoint for real-time XAPI events."""
    await websocket.accept()

    pc = pool_registry.get(pool_id)
    if pc is None or not pc._connected:
        await websocket.send_json({"type": "error", "message": "Pool not connected"})
        await websocket.close()
        return

    class_list = classes.split(",") if classes else ["*"]

    # Send initial connection confirmation
    await websocket.send_json({
        "type": "connected",
        "pool_name": pc.name,
        "pool_id": pool_id,
        "classes": class_list,
    })

    # Register for XAPI events
    reg_token = None
    try:
        reg_token = pc.event_register(class_list)

        while True:
            try:
                # Check for client messages (ping/pong, unsubscribe)
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                    msg = json.loads(data)
                    if msg.get("action") == "unsubscribe":
                        break
                except asyncio.TimeoutError:
                    pass

                # Poll XAPI events
                events = pc.event_next(reg_token)
                now = datetime.now(timezone.utc).isoformat()

                for evt in events:
                    await websocket.send_json({
                        "type": "event",
                        "class": evt.get("class", ""),
                        "operation": evt.get("operation", ""),
                        "ref": evt.get("ref", ""),
                        "obj_uuid": evt.get("obj_uuid", ""),
                        "timestamp": now,
                    })

            except WebSocketDisconnect:
                break
            except Exception as e:
                await websocket.send_json({"type": "error", "message": str(e)})
                await asyncio.sleep(5)  # Backoff before retry

    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})

    finally:
        if reg_token:
            pc.event_unregister(reg_token)
        try:
            await websocket.close()
        except Exception:
            pass
