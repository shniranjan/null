"""
Storage Management Routes — SR, VDI, VBD, PBD.

GET    /api/pools/{pool_id}/storage/srs          — list SRs
GET    /api/pools/{pool_id}/storage/srs/{ref}    — SR detail
GET    /api/pools/{pool_id}/storage/srs/{ref}/vdis — list VDIs in SR
POST   /api/pools/{pool_id}/storage/srs/{ref}/forget — forget SR
POST   /api/pools/{pool_id}/storage/srs/{ref}/destroy — destroy SR
POST   /api/pools/{pool_id}/storage/vdis         — create VDI
POST   /api/pools/{pool_id}/storage/vdis/{ref}/destroy — destroy VDI
POST   /api/pools/{pool_id}/storage/vdis/{ref}/resize  — resize VDI
POST   /api/pools/{pool_id}/storage/vbds         — attach VDI to VM (create VBD)
POST   /api/pools/{pool_id}/storage/vbds/{ref}/destroy — detach VBD
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.auth import UserOut, get_current_user
from app.database import get_db
from app.xapi.client import pool_registry

router = APIRouter(prefix="/api/pools/{pool_id}/storage", tags=["storage"])


def _get_pool(pool_id: int):
    pc = pool_registry.get(pool_id)
    if not pc or not pc._connected:
        raise HTTPException(status_code=404, detail="Pool not found or not connected")
    return pc


def _mb(val) -> int:
    try: return int(int(val) / (1024 * 1024))
    except: return 0


# ══════════════════════════════════════════════════════════════════════
# SR LISTING
# ══════════════════════════════════════════════════════════════════════

@router.get("/srs")
async def list_srs(pool_id: int, current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        srs = pc.get_srs()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

    result = []
    for ref, rec in srs.items():
        result.append({
            "ref": rec.get("uuid", ""),
            "name_label": rec.get("name_label", ""),
            "name_description": rec.get("name_description", ""),
            "type": rec.get("type", ""),
            "content_type": rec.get("content_type", ""),
            "physical_size": _mb(rec.get("physical_size", "0")),
            "physical_utilisation": _mb(rec.get("physical_utilisation", "0")),
            "virtual_allocation": _mb(rec.get("virtual_allocation", "0")),
            "shared": rec.get("shared", False),
            "clustered": rec.get("clustered", False),
            "VDIs": len(rec.get("VDIs", [])),
            "PBDs": len(rec.get("PBDs", [])),
        })

    result.sort(key=lambda s: s["name_label"].lower())
    return {"total": len(result), "srs": result}


# ══════════════════════════════════════════════════════════════════════
# SR DETAIL
# ══════════════════════════════════════════════════════════════════════

@router.get("/srs/{sr_ref:path}")
async def get_sr_detail(pool_id: int, sr_ref: str,
                        current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        rec = pc.get_sr_record(sr_ref)
        pbds = pc.get_sr_pbds(sr_ref)
        vdis = pc.get_sr_vdis(sr_ref)

        enriched_pbds = []
        for pbd in pbds:
            host_name = ""
            host_ref = pbd.get("host", "")
            if host_ref and host_ref != "OpaqueRef:NULL":
                try:
                    h = pc.call("host.get_record", host_ref)
                    host_name = h.get("name_label", "")
                except Exception:
                    pass
            enriched_pbds.append({
                "ref": pbd.get("uuid", ""),
                "host": host_ref,
                "host_name": host_name,
                "currently_attached": pbd.get("currently_attached", False),
                "device_config": pbd.get("device_config", {}),
            })

        return {
            "ref": rec.get("uuid", ""),
            "name_label": rec.get("name_label", ""),
            "name_description": rec.get("name_description", ""),
            "type": rec.get("type", ""),
            "content_type": rec.get("content_type", ""),
            "physical_size_mb": _mb(rec.get("physical_size", "0")),
            "physical_utilisation_mb": _mb(rec.get("physical_utilisation", "0")),
            "virtual_allocation_mb": _mb(rec.get("virtual_allocation", "0")),
            "shared": rec.get("shared", False),
            "clustered": rec.get("clustered", False),
            "sm_config": rec.get("sm_config", {}),
            "other_config": rec.get("other_config", {}),
            "vdi_count": len(vdis),
            "pbds": enriched_pbds,
            "vdis": [{
                "ref": v.get("uuid", ""),
                "name_label": v.get("name_label", ""),
                "virtual_size_mb": _mb(v.get("virtual_size", "0")),
                "physical_utilisation_mb": _mb(v.get("physical_utilisation", "0")),
                "type": v.get("type", ""),
                "sharable": v.get("sharable", False),
                "read_only": v.get("read_only", False),
                "managed": v.get("managed", True),
                "is_a_snapshot": v.get("is_a_snapshot", False),
                "tags": v.get("tags", []),
            } for v in vdis],
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


# ══════════════════════════════════════════════════════════════════════
# SR ACTIONS
# ══════════════════════════════════════════════════════════════════════

@router.post("/srs/{sr_ref:path}/forget")
async def sr_forget(pool_id: int, sr_ref: str,
                    current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        task_ref = pc.sr_forget(sr_ref)
        return {"status": "ok", "task_ref": task_ref}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.post("/srs/{sr_ref:path}/destroy")
async def sr_destroy(pool_id: int, sr_ref: str,
                     current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        task_ref = pc.sr_destroy(sr_ref)
        return {"status": "ok", "task_ref": task_ref}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


# ══════════════════════════════════════════════════════════════════════
# VDI OPERATIONS
# ══════════════════════════════════════════════════════════════════════

class VDICreateRequest(BaseModel):
    name_label: str
    sr_ref: str
    virtual_size_mb: int
    vdi_type: str = "user"
    sharable: bool = False

class VDIResizeRequest(BaseModel):
    new_size_mb: int

@router.post("/vdis")
async def create_vdi(pool_id: int, body: VDICreateRequest,
                     current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        vdi_ref = pc.vdi_create(
            body.sr_ref, body.name_label,
            body.virtual_size_mb * 1024 * 1024,
            body.vdi_type, body.sharable,
        )
        return {"status": "ok", "vdi_ref": vdi_ref}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.post("/vdis/{vdi_ref:path}/destroy")
async def destroy_vdi(pool_id: int, vdi_ref: str,
                      current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        task_ref = pc.vdi_destroy(vdi_ref)
        return {"status": "ok", "task_ref": task_ref}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.post("/vdis/{vdi_ref:path}/resize")
async def resize_vdi(pool_id: int, vdi_ref: str, body: VDIResizeRequest,
                     current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        task_ref = pc.vdi_resize(vdi_ref, body.new_size_mb * 1024 * 1024)
        return {"status": "ok", "task_ref": task_ref}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


# ══════════════════════════════════════════════════════════════════════
# VBD OPERATIONS (attach/detach disks to VMs)
# ══════════════════════════════════════════════════════════════════════

class VBDCreateRequest(BaseModel):
    vm_ref: str
    vdi_ref: str
    userdevice: str = ""
    bootable: bool = False
    mode: str = "RW"
    vbd_type: str = "Disk"

@router.post("/vbds")
async def attach_disk(pool_id: int, body: VBDCreateRequest,
                      current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        vbd_ref = pc.vbd_create(
            body.vm_ref, body.vdi_ref, body.userdevice,
            body.bootable, body.mode, body.vbd_type,
        )
        return {"status": "ok", "vbd_ref": vbd_ref}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.post("/vbds/{vbd_ref:path}/destroy")
async def detach_disk(pool_id: int, vbd_ref: str,
                      current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        task_ref = pc.vbd_destroy(vbd_ref)
        return {"status": "ok", "task_ref": task_ref}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
