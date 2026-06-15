"""
Metrics & Performance Routes.

GET /api/pools/{pool_id}/metrics/hosts      — host metrics snapshot
GET /api/pools/{pool_id}/metrics/vms        — VM metrics snapshot
GET /api/pools/{pool_id}/metrics/dashboard  — combined dashboard metrics
"""

from fastapi import APIRouter, Depends, HTTPException

from app.auth import UserOut, get_current_user
from app.xapi.client import pool_registry

router = APIRouter(prefix="/api/pools/{pool_id}/metrics", tags=["metrics"])


def _get_pool(pool_id: int):
    pc = pool_registry.get(pool_id)
    if not pc or not pc._connected:
        raise HTTPException(status_code=404, detail="Pool not found or not connected")
    return pc


@router.get("/hosts")
async def host_metrics(pool_id: int, current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        metrics = pc.get_host_metrics_snapshot()
        return {"total": len(metrics), "hosts": metrics}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/vms")
async def vm_metrics(pool_id: int, current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        metrics = pc.get_vm_metrics_snapshot()
        return {"total": len(metrics), "vms": metrics}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/dashboard")
async def dashboard_metrics(pool_id: int, current_user: UserOut = Depends(get_current_user)):
    """Combined overview for the dashboard."""
    pc = _get_pool(pool_id)
    try:
        hosts = pc.get_host_metrics_snapshot()
        vm_metrics = pc.get_vm_metrics_snapshot()
        host_list = pc.get_hosts()

        # Count VMs by power state
        vm_states = {"Running": 0, "Halted": 0, "Paused": 0, "Suspended": 0}
        vms = pc.get_vms()
        for ref, rec in vms.items():
            if rec.get("is_a_template") or rec.get("is_control_domain"):
                continue
            state = rec.get("power_state", "Halted")
            vm_states[state] = vm_states.get(state, 0) + 1

        # Pool info
        pool_info = pc.get_pool_info()

        return {
            "pool": {
                "name": pc.name,
                "host_count": len(host_list),
            },
            "hosts": hosts,
            "vm_summary": {
                "total": sum(vm_states.values()),
                **vm_states,
            },
            "vm_metrics": vm_metrics,
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
