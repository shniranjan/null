"""
Snapshot Management Routes.

GET    /api/pools/{pool_id}/snapshots               — list all snapshots
GET    /api/pools/{pool_id}/snapshots?vm_ref=...    — snapshots for a specific VM
POST   /api/pools/{pool_id}/snapshots               — create snapshot
POST   /api/pools/{pool_id}/snapshots/{ref}/revert  — revert VM to snapshot
DELETE /api/pools/{pool_id}/snapshots/{ref}         — delete snapshot
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from auth import UserOut, get_current_user
from xapi.client import pool_registry

router = APIRouter(prefix="/api/pools/{pool_id}", tags=["snapshots"])


def _get_pool(pool_id: int):
    pc = pool_registry.get(pool_id)
    if not pc or not pc._connected:
        raise HTTPException(status_code=404, detail="Pool not found or not connected")
    return pc


def _mb(val) -> int:
    try: return int(int(val) / (1024 * 1024))
    except: return 0


@router.get("/snapshots")
async def list_snapshots(
    pool_id: int,
    vm_ref: str = Query(None, description="Filter by parent VM ref"),
    current_user: UserOut = Depends(get_current_user),
):
    pc = _get_pool(pool_id)
    try:
        snaps = pc.get_snapshots(vm_ref)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Build snapshot tree (parent-child relationships)
    result = []
    for ref, rec in snaps.items():
        snapshot_time = rec.get("snapshot_time", "")
        # XAPI snapshot_time is often a datetime
        if hasattr(snapshot_time, "value"):
            snapshot_time = snapshot_time.value

        result.append({
            "ref": rec.get("uuid", ""),
            "name_label": rec.get("name_label", ""),
            "name_description": rec.get("name_description", ""),
            "snapshot_of": rec.get("snapshot_of", ""),
            "snapshot_time": str(snapshot_time) if snapshot_time else "",
            "is_vmss_snapshot": rec.get("is_vmss_snapshot", False),
            "power_state_at_snapshot": rec.get("power_state", ""),
            "memory_static_max_mb": _mb(rec.get("memory_static_max", "0")),
            "VCPUs_at_startup": rec.get("VCPUs_at_startup", "0"),
            "tags": rec.get("tags", []),
            "children": [],  # populated below
        })

    # Build parent→children map
    uuid_to_snap = {}
    for s in result:
        uuid_to_snap[s["ref"]] = s

    # Find parent VM name for each snapshot
    for s in result:
        parent_ref = s["snapshot_of"]
        if parent_ref in uuid_to_snap:
            # This is a snapshot of another snapshot
            uuid_to_snap[parent_ref].setdefault("children", []).append(s["ref"])

    # Sort by time, newest first
    result.sort(key=lambda s: s["snapshot_time"], reverse=True)
    return {"total": len(result), "snapshots": result}


class SnapshotCreateRequest(BaseModel):
    vm_ref: str
    name_label: str

@router.post("/snapshots")
async def create_snapshot(
    pool_id: int, body: SnapshotCreateRequest,
    current_user: UserOut = Depends(get_current_user),
):
    pc = _get_pool(pool_id)
    try:
        task_ref = pc.snapshot_create(body.vm_ref, body.name_label)
        return {"status": "ok", "task_ref": task_ref}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/snapshots/{snap_ref:path}/revert")
async def revert_snapshot(pool_id: int, snap_ref: str,
                          current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        task_ref = pc.snapshot_revert(snap_ref)
        return {"status": "ok", "task_ref": task_ref}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.delete("/snapshots/{snap_ref:path}")
async def delete_snapshot(pool_id: int, snap_ref: str,
                          current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        task_ref = pc.snapshot_destroy(snap_ref)
        return {"status": "ok", "task_ref": task_ref}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
