"""
VM Management Routes — full lifecycle for virtual machines.

GET    /api/pools/{pool_id}/vms               — list VMs
GET    /api/pools/{pool_id}/vms/{ref}         — VM detail (disks, NICs, metrics)
POST   /api/pools/{pool_id}/vms               — create VM
POST   /api/pools/{pool_id}/vms/{ref}/start   — start
POST   /api/pools/{pool_id}/vms/{ref}/shutdown — clean shutdown
POST   /api/pools/{pool_id}/vms/{ref}/reboot  — clean reboot
POST   /api/pools/{pool_id}/vms/{ref}/force-reboot  — hard reboot
POST   /api/pools/{pool_id}/vms/{ref}/force-shutdown — hard power off
POST   /api/pools/{pool_id}/vms/{ref}/pause   — pause
POST   /api/pools/{pool_id}/vms/{ref}/unpause — unpause
POST   /api/pools/{pool_id}/vms/{ref}/suspend — suspend to disk
POST   /api/pools/{pool_id}/vms/{ref}/resume  — resume
POST   /api/pools/{pool_id}/vms/{ref}/migrate — live migrate
POST   /api/pools/{pool_id}/vms/{ref}/clone   — fast clone
POST   /api/pools/{pool_id}/vms/{ref}/destroy — destroy VM
GET    /api/pools/{pool_id}/vms/{ref}/console — get VNC console info
GET    /api/pools/{pool_id}/templates          — list templates
GET    /api/pools/{pool_id}/hosts              — list hosts
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from auth import UserOut, get_current_user
from database import get_db
from xapi.client import pool_registry

router = APIRouter(prefix="/api/pools/{pool_id}", tags=["vms"])


# ── Helpers ──────────────────────────────────────────────────────────

def _get_pool(pool_id: int):
    """Get pool connection or raise 404."""
    pc = pool_registry.get(pool_id)
    if pc is None or not pc._connected:
        raise HTTPException(status_code=404, detail="Pool not found or not connected")
    return pc


def _log(conn, user: UserOut, pool_id: int, pool_name: str, action: str,
         target_type: str = "", target_name: str = "", target_ref: str = "",
         details: str = ""):
    """Write to audit log."""
    try:
        db = get_db()
        db.execute(
            """INSERT INTO audit_log
               (user_id, username, pool_id, pool_name, action, target_type, target_name, target_ref, details, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user.id, user.username, pool_id, pool_name, action,
             target_type, target_name, target_ref, details,
             datetime.now(timezone.utc).isoformat()),
        )
        db.commit()
        db.close()
    except Exception:
        pass  # audit log is best-effort


def _simplify_vm(record: dict) -> dict:
    """Extract key fields from a VM record for list display."""
    return {
        "ref": record.get("uuid", ""),
        "name_label": record.get("name_label", ""),
        "name_description": record.get("name_description", ""),
        "power_state": record.get("power_state", ""),
        "VCPUs_max": record.get("VCPUs_max", "0"),
        "memory_static_max": _bytes_to_mb(record.get("memory_static_max", "0")),
        "memory_dynamic_max": _bytes_to_mb(record.get("memory_dynamic_max", "0")),
        "is_a_template": record.get("is_a_template", False),
        "is_a_snapshot": record.get("is_a_snapshot", False),
        "is_control_domain": record.get("is_control_domain", False),
        "resident_on": record.get("resident_on", ""),
        "affinity": record.get("affinity", ""),
        "os_version": record.get("os_version", {}).get("name", "") if record.get("os_version") else "",
        "tags": record.get("tags", []),
    }


def _bytes_to_mb(val) -> int:
    try:
        return int(int(val) / (1024 * 1024))
    except (ValueError, TypeError):
        return 0


# ── Models ───────────────────────────────────────────────────────────

class VMCreateRequest(BaseModel):
    name_label: str
    name_description: str = ""
    template_ref: str               # OpaqueRef of template
    vcpus: int = 2
    memory_mb: int = 2048
    install_repository: str = ""    # ISO SR ref or URL for network install

class VMMigrateRequest(BaseModel):
    dest_host_ref: str
    live: bool = True

class VMSetMemoryRequest(BaseModel):
    static_min_mb: int
    static_max_mb: int
    dynamic_min_mb: int
    dynamic_max_mb: int

class VMSetVCPUsRequest(BaseModel):
    vcpus: int

class VMSetNameRequest(BaseModel):
    name_label: str
    name_description: str = ""


# ══════════════════════════════════════════════════════════════════════
# VM LISTING
# ══════════════════════════════════════════════════════════════════════

@router.get("/vms")
async def list_vms(
    pool_id: int,
    power_state: Optional[str] = Query(None, description="Filter: Running, Halted, Suspended, Paused"),
    search: Optional[str] = Query(None, description="Search in name_label"),
    include_templates: bool = Query(False),
    current_user: UserOut = Depends(get_current_user),
):
    """List all VMs in the pool. Filters out templates and control domain by default."""
    pc = _get_pool(pool_id)
    try:
        all_vms = pc.get_vms()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

    vms = []
    for ref, rec in all_vms.items():
        # Skip templates unless requested
        if not include_templates and rec.get("is_a_template"):
            continue
        # Skip control domain (dom0)
        if rec.get("is_control_domain"):
            continue
        # Skip snapshots (they're listed separately)
        if rec.get("is_a_snapshot"):
            continue

        # Filter by power state
        if power_state and rec.get("power_state", "").lower() != power_state.lower():
            continue

        # Filter by search term
        if search and search.lower() not in rec.get("name_label", "").lower():
            continue

        vms.append(_simplify_vm(rec))

    # Sort by name
    vms.sort(key=lambda v: v["name_label"].lower())
    return {"total": len(vms), "vms": vms}


# ══════════════════════════════════════════════════════════════════════
# VM DETAIL
# ══════════════════════════════════════════════════════════════════════

@router.get("/vms/{vm_ref:path}")
async def get_vm_detail(
    pool_id: int,
    vm_ref: str,
    current_user: UserOut = Depends(get_current_user),
):
    """Get full VM detail including disks, NICs, and metrics."""
    pc = _get_pool(pool_id)
    try:
        rec = pc.get_vm_record(vm_ref)
        metrics = pc.get_vm_metrics(vm_ref)
        guest = pc.get_vm_guest_metrics(vm_ref)
        vbds = pc.get_vm_vbds(vm_ref)
        vifs = pc.get_vm_vifs(vm_ref)

        # Enrich VBDs with VDI info
        enriched_vbds = []
        for vbd in vbds:
            vdi_ref = vbd.get("VDI", "")
            vdi_info = {}
            if vdi_ref and vdi_ref != "OpaqueRef:NULL":
                try:
                    vdi_rec = pc.call("VDI.get_record", vdi_ref)
                    vdi_info = {
                        "name_label": vdi_rec.get("name_label", ""),
                        "virtual_size": _bytes_to_mb(vdi_rec.get("virtual_size", "0")),
                        "physical_utilisation": _bytes_to_mb(vdi_rec.get("physical_utilisation", "0")),
                        "type": vdi_rec.get("type", ""),
                        "sharable": vdi_rec.get("sharable", False),
                        "read_only": vdi_rec.get("read_only", False),
                        "managed": vdi_rec.get("managed", True),
                        "SR": vdi_rec.get("SR", ""),
                    }
                except Exception:
                    pass
            enriched_vbds.append({
                "ref": vbd.get("uuid", ""),
                "device": vbd.get("device", ""),
                "userdevice": vbd.get("userdevice", ""),
                "bootable": vbd.get("bootable", False),
                "mode": vbd.get("mode", ""),
                "type": vbd.get("type", ""),
                "currently_attached": vbd.get("currently_attached", False),
                "vdi": vdi_info,
            })

        # Enrich VIFs with network info
        enriched_vifs = []
        for vif in vifs:
            net_ref = vif.get("network", "")
            net_info = {}
            if net_ref:
                try:
                    net_rec = pc.call("network.get_record", net_ref)
                    net_info = {
                        "name_label": net_rec.get("name_label", ""),
                        "bridge": net_rec.get("bridge", ""),
                        "MTU": net_rec.get("MTU", "1500"),
                    }
                except Exception:
                    pass
            enriched_vifs.append({
                "ref": vif.get("uuid", ""),
                "device": vif.get("device", ""),
                "MAC": vif.get("MAC", ""),
                "MTU": vif.get("MTU", "1500"),
                "currently_attached": vif.get("currently_attached", True),
                "network": net_info,
                "ipv4_addresses": guest.get("networks", {}).get(f"{vif.get('device', '')}/ipv4/0", "")
                    if guest else "",
                "ipv6_addresses": guest.get("networks", {}).get(f"{vif.get('device', '')}/ipv6/0", "")
                    if guest else "",
            })

        # Get host name if VM is resident
        host_name = ""
        resident_on = rec.get("resident_on", "")
        if resident_on and resident_on != "OpaqueRef:NULL":
            try:
                host_rec = pc.call("host.get_record", resident_on)
                host_name = host_rec.get("name_label", "")
            except Exception:
                pass

        return {
            "ref": rec.get("uuid", ""),
            "name_label": rec.get("name_label", ""),
            "name_description": rec.get("name_description", ""),
            "power_state": rec.get("power_state", ""),
            "VCPUs_max": rec.get("VCPUs_max", "0"),
            "VCPUs_at_startup": rec.get("VCPUs_at_startup", "0"),
            "memory_static_max_mb": _bytes_to_mb(rec.get("memory_static_max", "0")),
            "memory_dynamic_max_mb": _bytes_to_mb(rec.get("memory_dynamic_max", "0")),
            "memory_static_min_mb": _bytes_to_mb(rec.get("memory_static_min", "0")),
            "memory_dynamic_min_mb": _bytes_to_mb(rec.get("memory_dynamic_min", "0")),
            "is_a_template": rec.get("is_a_template", False),
            "is_a_snapshot": rec.get("is_a_snapshot", False),
            "resident_on": resident_on,
            "resident_on_name": host_name,
            "affinity": rec.get("affinity", ""),
            "os_version": rec.get("os_version", {}),
            "platform": rec.get("platform", {}),
            "HVM_boot_policy": rec.get("HVM_boot_policy", ""),
            "PV_bootloader": rec.get("PV_bootloader", ""),
            "PV_kernel": rec.get("PV_kernel", ""),
            "tags": rec.get("tags", []),
            "vbds": enriched_vbds,
            "vifs": enriched_vifs,
            "metrics": {
                "vcpus_utilisation": metrics.get("VCPUs_utilisation", {}),
                "memory_actual": _bytes_to_mb(metrics.get("memory_actual", "0")),
            } if metrics else {},
            "guest_metrics": {
                "os_version": guest.get("os_version", {}),
                "PV_drivers_version": guest.get("PV_drivers_version", {}),
                "PV_drivers_up_to_date": guest.get("PV_drivers_up_to_date", False),
                "memory": guest.get("memory", {}),
                "disks": guest.get("disks", {}),
            } if guest else {},
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


# ══════════════════════════════════════════════════════════════════════
# VM LIFECYCLE ACTIONS
# ══════════════════════════════════════════════════════════════════════

@router.post("/vms/{vm_ref:path}/start")
async def vm_start(pool_id: int, vm_ref: str, current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        task_ref = pc.vm_start(vm_ref)
        _log(pc, current_user, pool_id, pc.name, "vm.start", "VM", vm_ref=vm_ref)
        return {"status": "ok", "task_ref": task_ref}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.post("/vms/{vm_ref:path}/shutdown")
async def vm_shutdown(pool_id: int, vm_ref: str, current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        task_ref = pc.vm_shutdown(vm_ref)
        _log(pc, current_user, pool_id, pc.name, "vm.shutdown", "VM", vm_ref=vm_ref)
        return {"status": "ok", "task_ref": task_ref}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.post("/vms/{vm_ref:path}/reboot")
async def vm_reboot(pool_id: int, vm_ref: str, current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        task_ref = pc.vm_reboot(vm_ref)
        _log(pc, current_user, pool_id, pc.name, "vm.reboot", "VM", vm_ref=vm_ref)
        return {"status": "ok", "task_ref": task_ref}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.post("/vms/{vm_ref:path}/force-reboot")
async def vm_force_reboot(pool_id: int, vm_ref: str, current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        task_ref = pc.vm_hard_reboot(vm_ref)
        _log(pc, current_user, pool_id, pc.name, "vm.force_reboot", "VM", vm_ref=vm_ref)
        return {"status": "ok", "task_ref": task_ref}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.post("/vms/{vm_ref:path}/force-shutdown")
async def vm_force_shutdown(pool_id: int, vm_ref: str, current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        task_ref = pc.vm_hard_shutdown(vm_ref)
        _log(pc, current_user, pool_id, pc.name, "vm.force_shutdown", "VM", vm_ref=vm_ref)
        return {"status": "ok", "task_ref": task_ref}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.post("/vms/{vm_ref:path}/pause")
async def vm_pause(pool_id: int, vm_ref: str, current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        task_ref = pc.vm_pause(vm_ref)
        _log(pc, current_user, pool_id, pc.name, "vm.pause", "VM", vm_ref=vm_ref)
        return {"status": "ok", "task_ref": task_ref}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.post("/vms/{vm_ref:path}/unpause")
async def vm_unpause(pool_id: int, vm_ref: str, current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        task_ref = pc.vm_unpause(vm_ref)
        _log(pc, current_user, pool_id, pc.name, "vm.unpause", "VM", vm_ref=vm_ref)
        return {"status": "ok", "task_ref": task_ref}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.post("/vms/{vm_ref:path}/suspend")
async def vm_suspend(pool_id: int, vm_ref: str, current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        task_ref = pc.vm_suspend(vm_ref)
        _log(pc, current_user, pool_id, pc.name, "vm.suspend", "VM", vm_ref=vm_ref)
        return {"status": "ok", "task_ref": task_ref}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.post("/vms/{vm_ref:path}/resume")
async def vm_resume(pool_id: int, vm_ref: str, current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        task_ref = pc.vm_resume(vm_ref)
        _log(pc, current_user, pool_id, pc.name, "vm.resume", "VM", vm_ref=vm_ref)
        return {"status": "ok", "task_ref": task_ref}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.post("/vms/{vm_ref:path}/migrate")
async def vm_migrate(
    pool_id: int, vm_ref: str,
    body: VMMigrateRequest,
    current_user: UserOut = Depends(get_current_user),
):
    pc = _get_pool(pool_id)
    try:
        opts = {"live": "true"} if body.live else {}
        task_ref = pc.vm_migrate(vm_ref, body.dest_host_ref, opts)
        _log(pc, current_user, pool_id, pc.name, "vm.migrate", "VM",
             vm_ref=vm_ref, details=f"to host {body.dest_host_ref}")
        return {"status": "ok", "task_ref": task_ref}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.post("/vms/{vm_ref:path}/clone")
async def vm_clone(
    pool_id: int, vm_ref: str,
    body: VMSetNameRequest,
    current_user: UserOut = Depends(get_current_user),
):
    pc = _get_pool(pool_id)
    try:
        task_ref = pc.vm_clone(vm_ref, body.name_label)
        _log(pc, current_user, pool_id, pc.name, "vm.clone", "VM",
             vm_ref=vm_ref, details=f"new name: {body.name_label}")
        return {"status": "ok", "task_ref": task_ref}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.post("/vms/{vm_ref:path}/destroy")
async def vm_destroy(pool_id: int, vm_ref: str, current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        # Get name before destroying for audit
        rec = pc.get_vm_record(vm_ref)
        name = rec.get("name_label", vm_ref)
        task_ref = pc.vm_destroy(vm_ref)
        _log(pc, current_user, pool_id, pc.name, "vm.destroy", "VM", target_name=name, vm_ref=vm_ref)
        return {"status": "ok", "task_ref": task_ref}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

# ══════════════════════════════════════════════════════════════════════
# VM CONFIGURATION
# ══════════════════════════════════════════════════════════════════════

@router.put("/vms/{vm_ref:path}/name")
async def vm_set_name(
    pool_id: int, vm_ref: str,
    body: VMSetNameRequest,
    current_user: UserOut = Depends(get_current_user),
):
    pc = _get_pool(pool_id)
    try:
        pc.vm_set_name(vm_ref, body.name_label, body.name_description)
        _log(pc, current_user, pool_id, pc.name, "vm.rename", "VM",
             vm_ref=vm_ref, details=f"renamed to {body.name_label}")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.put("/vms/{vm_ref:path}/memory")
async def vm_set_memory(
    pool_id: int, vm_ref: str,
    body: VMSetMemoryRequest,
    current_user: UserOut = Depends(get_current_user),
):
    pc = _get_pool(pool_id)
    try:
        task_ref = pc.vm_set_memory(
            vm_ref,
            body.static_min_mb * 1024 * 1024,
            body.static_max_mb * 1024 * 1024,
            body.dynamic_min_mb * 1024 * 1024,
            body.dynamic_max_mb * 1024 * 1024,
        )
        _log(pc, current_user, pool_id, pc.name, "vm.set_memory", "VM",
             vm_ref=vm_ref, details=f"{body.dynamic_max_mb}MB")
        return {"status": "ok", "task_ref": task_ref}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.put("/vms/{vm_ref:path}/vcpus")
async def vm_set_vcpus(
    pool_id: int, vm_ref: str,
    body: VMSetVCPUsRequest,
    current_user: UserOut = Depends(get_current_user),
):
    pc = _get_pool(pool_id)
    try:
        pc.vm_set_vcpus(vm_ref, body.vcpus)
        _log(pc, current_user, pool_id, pc.name, "vm.set_vcpus", "VM",
             vm_ref=vm_ref, details=f"{body.vcpus} vCPUs")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

# ══════════════════════════════════════════════════════════════════════
# CONSOLE
# ══════════════════════════════════════════════════════════════════════

@router.get("/vms/{vm_ref:path}/console")
async def get_vm_console(
    pool_id: int, vm_ref: str,
    current_user: UserOut = Depends(get_current_user),
):
    """Get VNC console connection info for a VM."""
    pc = _get_pool(pool_id)
    try:
        consoles = pc.get_vm_consoles(vm_ref)
        result = []
        for c in consoles:
            protocol = c.get("protocol", "rfb")
            location = c.get("location", "")
            # location format: "host:port" or just "port"
            result.append({
                "protocol": protocol,
                "location": location,
                "uuid": c.get("uuid", ""),
                "other_config": c.get("other_config", {}),
            })
        return {"consoles": result}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


# ══════════════════════════════════════════════════════════════════════
# TEMPLATES
# ══════════════════════════════════════════════════════════════════════

@router.get("/templates")
async def list_templates(
    pool_id: int,
    current_user: UserOut = Depends(get_current_user),
):
    """List VM templates available in the pool."""
    pc = _get_pool(pool_id)
    try:
        templates = pc.get_templates()
        result = []
        for ref, rec in templates.items():
            result.append({
                "ref": rec.get("uuid", ""),
                "name_label": rec.get("name_label", ""),
                "name_description": rec.get("name_description", ""),
                "VCPUs_max": rec.get("VCPUs_max", "0"),
                "memory_static_max": _bytes_to_mb(rec.get("memory_static_max", "0")),
                "HVM_boot_policy": rec.get("HVM_boot_policy", ""),
                "os_version": rec.get("os_version", {}),
                "tags": rec.get("tags", []),
            })
        result.sort(key=lambda t: t["name_label"].lower())
        return {"total": len(result), "templates": result}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


# ══════════════════════════════════════════════════════════════════════
# HOSTS
# ══════════════════════════════════════════════════════════════════════

@router.get("/hosts")
async def list_hosts(
    pool_id: int,
    current_user: UserOut = Depends(get_current_user),
):
    """List hosts in the pool (for migration target selection, etc.)."""
    pc = _get_pool(pool_id)
    try:
        hosts = pc.get_hosts()
        result = []
        for ref, rec in hosts.items():
            metrics = {}
            try:
                m_ref = pc.call("host.get_metrics", ref)
                m_rec = pc.call("host_metrics.get_record", m_ref)
                metrics = {
                    "memory_total": _bytes_to_mb(m_rec.get("memory_total", "0")),
                    "memory_free": _bytes_to_mb(m_rec.get("memory_free", "0")),
                    "live": m_rec.get("live", False),
                }
            except Exception:
                pass

            result.append({
                "ref": rec.get("uuid", ""),
                "name_label": rec.get("name_label", ""),
                "address": rec.get("address", ""),
                "enabled": rec.get("enabled", False),
                "is_master": False,  # Will be set below
                "cpu_info": rec.get("cpu_info", {}).get("cpu_count", "0"),
                "metrics": metrics,
                "software_version": rec.get("software_version", {}),
            })

        # Mark the pool master
        pool_info = pc.get_pool_info()
        if pool_info:
            master_ref = list(pool_info.values())[0].get("master", "")
            for h in result:
                # Match by opaque ref stored in resident_on style
                for ref, rec in hosts.items():
                    if rec.get("uuid") == h["ref"] and ref == master_ref:
                        h["is_master"] = True
                        break

        result.sort(key=lambda h: h["name_label"].lower())
        return {"total": len(result), "hosts": result}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


# ══════════════════════════════════════════════════════════════════════
# TASK STATUS (for polling async operations)
# ══════════════════════════════════════════════════════════════════════

@router.get("/tasks/{task_ref:path}")
async def get_task_status(
    pool_id: int, task_ref: str,
    current_user: UserOut = Depends(get_current_user),
):
    """Get the status of an async task."""
    pc = _get_pool(pool_id)
    try:
        task = pc.get_task_record(task_ref)
        return {
            "ref": task.get("uuid", task_ref),
            "name_label": task.get("name_label", ""),
            "status": task.get("status", "unknown"),
            "progress": task.get("progress", 0),
            "error_info": task.get("error_info", []),
            "created": task.get("created", ""),
            "finished": task.get("finished", ""),
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


# ══════════════════════════════════════════════════════════════════════
# VM TAGS
# ══════════════════════════════════════════════════════════════════════

class VMTagRequest(BaseModel):
    tag: str

@router.post("/vms/{vm_ref:path}/tags/add")
async def vm_add_tag(pool_id: int, vm_ref: str, body: VMTagRequest,
                     current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        pc.call("VM.add_tags", vm_ref, body.tag)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.post("/vms/{vm_ref:path}/tags/remove")
async def vm_remove_tag(pool_id: int, vm_ref: str, body: VMTagRequest,
                        current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        pc.call("VM.remove_tags", vm_ref, body.tag)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


# ══════════════════════════════════════════════════════════════════════
# VM EXPORT PROFILE
# ══════════════════════════════════════════════════════════════════════

@router.get("/vms/{vm_ref:path}/profile")
async def export_vm_profile(pool_id: int, vm_ref: str,
                            current_user: UserOut = Depends(get_current_user)):
    """Export a VM's configuration as a JSON profile for re-import."""
    pc = _get_pool(pool_id)
    try:
        rec = pc.get_vm_record(vm_ref)
        vbds = pc.get_vm_vbds(vm_ref)
        vifs = pc.get_vm_vifs(vm_ref)

        profile = {
            "version": "1.0",
            "exported_at": str(datetime.now(timezone.utc).isoformat()),
            "vm": {
                "name_label": rec.get("name_label", ""),
                "name_description": rec.get("name_description", ""),
                "VCPUs_max": rec.get("VCPUs_max", "1"),
                "VCPUs_at_startup": rec.get("VCPUs_at_startup", "1"),
                "memory_static_max": rec.get("memory_static_max", "0"),
                "memory_dynamic_max": rec.get("memory_dynamic_max", "0"),
                "memory_static_min": rec.get("memory_static_min", "0"),
                "memory_dynamic_min": rec.get("memory_dynamic_min", "0"),
                "platform": rec.get("platform", {}),
                "HVM_boot_policy": rec.get("HVM_boot_policy", ""),
                "tags": rec.get("tags", []),
                "os_version": rec.get("os_version", {}),
            },
            "disks": [{
                "userdevice": vbd.get("userdevice", ""),
                "bootable": vbd.get("bootable", False),
                "mode": vbd.get("mode", "RW"),
                "type": vbd.get("type", "Disk"),
            } for vbd in vbds],
            "nics": [{
                "device": vif.get("device", ""),
                "mac": vif.get("MAC", ""),
                "mtu": vif.get("MTU", "1500"),
            } for vif in vifs],
        }
        return profile
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
