"""
Device Passthrough Routes — PCI, GPU (vGPU), USB.

GET    /api/pools/{pool_id}/passthrough/pcis           — list PCI devices
GET    /api/pools/{pool_id}/passthrough/gpu-groups     — list GPU groups
GET    /api/pools/{pool_id}/passthrough/vgpu-types     — list vGPU profiles
GET    /api/pools/{pool_id}/passthrough/pusbs          — list physical USB devices
GET    /api/pools/{pool_id}/vms/{ref}/passthrough      — get VM's passthrough devices
POST   /api/pools/{pool_id}/vms/{ref}/passthrough/vgpu — attach vGPU to VM
DELETE /api/pools/{pool_id}/vms/{ref}/passthrough/vgpu/{vref} — detach vGPU
POST   /api/pools/{pool_id}/vms/{ref}/passthrough/usb  — attach USB to VM
DELETE /api/pools/{pool_id}/vms/{ref}/passthrough/usb/{vref}  — detach USB
POST   /api/pools/{pool_id}/vms/{ref}/passthrough/pci  — add PCI passthrough
DELETE /api/pools/{pool_id}/vms/{ref}/passthrough/pci  — remove PCI passthrough
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.auth import UserOut, get_current_user
from app.xapi.client import pool_registry

router = APIRouter(prefix="/api/pools/{pool_id}", tags=["passthrough"])


def _get_pool(pool_id: int):
    pc = pool_registry.get(pool_id)
    if not pc or not pc._connected:
        raise HTTPException(status_code=404, detail="Pool not found or not connected")
    return pc


# ══════════════════════════════════════════════════════════════════════
# AVAILABLE DEVICES (pool-wide)
# ══════════════════════════════════════════════════════════════════════

@router.get("/passthrough/pcis")
async def list_pcis(pool_id: int, current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        pcis = pc.get_host_pcis()
        result = []
        for p in pcis:
            result.append({
                "ref": p.get("uuid", ""),
                "device_name": p.get("device_name", ""),
                "vendor_name": p.get("vendor_name", ""),
                "pci_id": p.get("pci_id", ""),
                "class_name": p.get("class_name", ""),
                "host": p.get("host", ""),
            })
        return {"total": len(result), "pcis": result}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/passthrough/gpu-groups")
async def list_gpu_groups(pool_id: int, current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        groups = pc.get_gpu_groups()
        result = []
        for g in groups:
            result.append({
                "ref": g.get("uuid", ""),
                "name_label": g.get("name_label", ""),
                "name_description": g.get("name_description", ""),
                "VGPU_types": g.get("VGPU_types", []),
                "PGPUs": g.get("PGPUs", []),
                "enabled": g.get("enabled", False),
            })
        return {"total": len(result), "gpu_groups": result}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/passthrough/vgpu-types")
async def list_vgpu_types(pool_id: int, current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        types = pc.get_vgpu_types()
        result = []
        for t in types:
            result.append({
                "ref": t.get("uuid", ""),
                "model_name": t.get("model_name", ""),
                "vendor_name": t.get("vendor_name", ""),
                "framebuffer_size": t.get("framebuffer_size", "0"),
                "max_heads": t.get("max_heads", "0"),
                "max_resolution": t.get("max_resolution", ""),
                "supported_on_PGPUs": t.get("supported_on_PGPUs", []),
                "enabled": t.get("enabled", False),
            })
        return {"total": len(result), "vgpu_types": result}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/passthrough/pusbs")
async def list_pusbs(pool_id: int, current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        pusbs = pc.get_host_pusbs()
        result = []
        for u in pusbs:
            result.append({
                "ref": u.get("uuid", ""),
                "vendor_name": u.get("vendor_name", ""),
                "product_name": u.get("product_name", ""),
                "serial": u.get("serial", ""),
                "vendor_id": u.get("vendor_id", ""),
                "product_id": u.get("product_id", ""),
                "host": u.get("host", ""),
            })
        return {"total": len(result), "pusbs": result}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


# ══════════════════════════════════════════════════════════════════════
# VM PASSTHROUGH STATUS
# ══════════════════════════════════════════════════════════════════════

@router.get("/vms/{vm_ref:path}/passthrough")
async def get_vm_passthrough(pool_id: int, vm_ref: str,
                             current_user: UserOut = Depends(get_current_user)):
    """Get all passthrough devices currently attached to a VM."""
    pc = _get_pool(pool_id)
    try:
        # vGPUs
        vgpus = pc.get_vm_vgpus(vm_ref)
        vgpu_list = []
        for v in vgpus:
            gpu_type_info = {}
            try:
                if v.get("type"):
                    gt = pc.call("VGPU_type.get_record", v["type"])
                    gpu_type_info = {
                        "model_name": gt.get("model_name", ""),
                        "vendor_name": gt.get("vendor_name", ""),
                    }
            except Exception:
                pass
            vgpu_list.append({
                "ref": v.get("uuid", ""),
                "GPU_group": v.get("GPU_group", ""),
                "type": v.get("type", ""),
                "currently_attached": v.get("currently_attached", False),
                "type_info": gpu_type_info,
            })

        # VUSBs (USB passthrough)
        vusbs = pc.get_vm_vusbs(vm_ref)
        vusb_list = []
        for v in vusbs:
            usb_info = {}
            try:
                if v.get("USB_group"):
                    ug = pc.call("USB_group.get_record", v["USB_group"])
                    pusb_info = {}
                    if ug.get("PUSBs"):
                        try:
                            pu = pc.call("PUSB.get_record", ug["PUSBs"][0])
                            pusb_info = {
                                "vendor_name": pu.get("vendor_name", ""),
                                "product_name": pu.get("product_name", ""),
                            }
                        except Exception:
                            pass
                    usb_info = {
                        "name_label": ug.get("name_label", ""),
                        "name_description": ug.get("name_description", ""),
                        "pusb": pusb_info,
                    }
            except Exception:
                pass
            vusb_list.append({
                "ref": v.get("uuid", ""),
                "USB_group": v.get("USB_group", ""),
                "currently_attached": v.get("currently_attached", False),
                "usb_info": usb_info,
            })

        # PCI passthrough (other-config:pci)
        pci_list = []
        try:
            other = pc.call("VM.get_other_config", vm_ref)
            pci_str = other.get("pci", "")
            if pci_str:
                for token in pci_str.split(","):
                    token = token.strip()
                    if token:
                        # Try to get PCI device info
                        pci_info = {}
                        try:
                            pci_rec = pc.call("PCI.get_record", token)
                            pci_info = {
                                "device_name": pci_rec.get("device_name", ""),
                                "vendor_name": pci_rec.get("vendor_name", ""),
                                "pci_id": pci_rec.get("pci_id", ""),
                            }
                        except Exception:
                            pass
                        pci_list.append({"ref": token, "info": pci_info})
        except Exception:
            pass

        return {
            "vgpus": vgpu_list,
            "vusbs": vusb_list,
            "pcis": pci_list,
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


# ══════════════════════════════════════════════════════════════════════
# ACTIONS
# ══════════════════════════════════════════════════════════════════════

class VGPUAttachRequest(BaseModel):
    gpu_group_ref: str
    vgpu_type_ref: str

class USBPassRequest(BaseModel):
    usb_group_ref: str

class PCIPassRequest(BaseModel):
    pci_ref: str


@router.post("/vms/{vm_ref:path}/passthrough/vgpu")
async def attach_vgpu(pool_id: int, vm_ref: str, body: VGPUAttachRequest,
                      current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        vgpu_ref = pc.vgpu_create(vm_ref, body.gpu_group_ref, body.vgpu_type_ref)
        return {"status": "ok", "vgpu_ref": vgpu_ref}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.delete("/vms/{vm_ref:path}/passthrough/vgpu/{vgpu_ref:path}")
async def detach_vgpu(pool_id: int, vm_ref: str, vgpu_ref: str,
                      current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        task_ref = pc.vgpu_destroy(vgpu_ref)
        return {"status": "ok", "task_ref": task_ref}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/vms/{vm_ref:path}/passthrough/usb")
async def attach_usb(pool_id: int, vm_ref: str, body: USBPassRequest,
                     current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        vusb_ref = pc.vusb_create(vm_ref, body.usb_group_ref)
        return {"status": "ok", "vusb_ref": vusb_ref}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.delete("/vms/{vm_ref:path}/passthrough/usb/{vusb_ref:path}")
async def detach_usb(pool_id: int, vm_ref: str, vusb_ref: str,
                     current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        task_ref = pc.vusb_destroy(vusb_ref)
        return {"status": "ok", "task_ref": task_ref}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/vms/{vm_ref:path}/passthrough/pci")
async def add_pci_passthrough(pool_id: int, vm_ref: str, body: PCIPassRequest,
                              current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        pc.vm_add_pci(vm_ref, body.pci_ref)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.delete("/vms/{vm_ref:path}/passthrough/pci")
async def remove_pci_passthrough(pool_id: int, vm_ref: str,
                                 current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        pc.vm_remove_pci(vm_ref)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
