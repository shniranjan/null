"""
Health check endpoints.

GET /api/health        — backend is running
GET /api/health/xcpng  — test connection to a pool
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from auth import UserOut, get_current_user
from xapi.client import pool_registry

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
async def health_check():
    return {
        "status": "ok",
        "service": "Null",
        "version": "0.1.0",
    }


@router.get("/xcpng")
async def xcpng_health(
    pool_id: int = Query(..., description="Pool ID to test"),
    current_user: UserOut = Depends(get_current_user),
):
    """Test connectivity to a specific XCP-ng pool."""
    pc = pool_registry.get(pool_id)
    if pc is None:
        raise HTTPException(status_code=404, detail="Pool not found or not connected")

    try:
        hosts = pc.get_hosts()
        return {
            "status": "connected",
            "host_count": len(hosts),
            "hosts": {
                ref: {
                    "name_label": h.get("name_label", ""),
                    "address": h.get("address", ""),
                    "enabled": h.get("enabled", False),
                }
                for ref, h in hosts.items()
            },
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
