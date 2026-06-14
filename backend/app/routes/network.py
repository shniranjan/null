"""
Network Management Routes — Network, VLAN, Bond, PIF, VIF.

GET    /api/pools/{pool_id}/network/networks    — list networks
GET    /api/pools/{pool_id}/network/networks/{ref} — network detail
POST   /api/pools/{pool_id}/network/networks    — create network
POST   /api/pools/{pool_id}/network/networks/{ref}/destroy — destroy
GET    /api/pools/{pool_id}/network/hosts/{ref}/pifs — list PIFs
POST   /api/pools/{pool_id}/network/bonds       — create bond
POST   /api/pools/{pool_id}/network/vlans       — create VLAN
POST   /api/pools/{pool_id}/network/vifs        — attach NIC to VM
POST   /api/pools/{pool_id}/network/vifs/{ref}/destroy — detach NIC
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from auth import UserOut, get_current_user
from xapi.client import pool_registry

router = APIRouter(prefix="/api/pools/{pool_id}/network", tags=["network"])


def _get_pool(pool_id: int):
    pc = pool_registry.get(pool_id)
    if not pc or not pc._connected:
        raise HTTPException(status_code=404, detail="Pool not found or not connected")
    return pc


# ══════════════════════════════════════════════════════════════════════
# NETWORK LISTING
# ══════════════════════════════════════════════════════════════════════

@router.get("/networks")
async def list_networks(pool_id: int, current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        nets = pc.get_networks()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

    result = []
    for ref, rec in nets.items():
        result.append({
            "ref": rec.get("uuid", ""),
            "name_label": rec.get("name_label", ""),
            "name_description": rec.get("name_description", ""),
            "bridge": rec.get("bridge", ""),
            "MTU": rec.get("MTU", "1500"),
            "VIFs": len(rec.get("VIFs", [])),
            "PIFs": len(rec.get("PIFs", [])),
            "other_config": rec.get("other_config", {}),
            "default_locking_mode": rec.get("default_locking_mode", ""),
            "tags": rec.get("tags", []),
        })

    result.sort(key=lambda n: n["name_label"].lower())
    return {"total": len(result), "networks": result}


# ══════════════════════════════════════════════════════════════════════
# NETWORK DETAIL
# ══════════════════════════════════════════════════════════════════════

@router.get("/networks/{net_ref:path}")
async def get_network_detail(pool_id: int, net_ref: str,
                             current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        rec = pc.get_network_record(net_ref)

        # Get VIFs on this network
        vifs = []
        for vif_ref in rec.get("VIFs", []):
            try:
                vif = pc.call("VIF.get_record", vif_ref)
                vifs.append({
                    "ref": vif.get("uuid", ""),
                    "device": vif.get("device", ""),
                    "MAC": vif.get("MAC", ""),
                    "MTU": vif.get("MTU", "1500"),
                    "currently_attached": vif.get("currently_attached", True),
                    "VM": vif.get("VM", ""),
                })
            except Exception:
                pass

        # Get PIFs on this network
        pifs = []
        for pif_ref in rec.get("PIFs", []):
            try:
                pif = pc.call("PIF.get_record", pif_ref)
                host_name = ""
                host_ref = pif.get("host", "")
                if host_ref and host_ref != "OpaqueRef:NULL":
                    try:
                        h = pc.call("host.get_record", host_ref)
                        host_name = h.get("name_label", "")
                    except Exception:
                        pass
                pifs.append({
                    "ref": pif.get("uuid", ""),
                    "device": pif.get("device", ""),
                    "MAC": pif.get("MAC", ""),
                    "MTU": pif.get("MTU", "1500"),
                    "VLAN": pif.get("VLAN", "-1"),
                    "physical": pif.get("physical", False),
                    "currently_attached": pif.get("currently_attached", True),
                    "host_name": host_name,
                    "IP": pif.get("IP", ""),
                    "netmask": pif.get("netmask", ""),
                })
            except Exception:
                pass

        return {
            "ref": rec.get("uuid", ""),
            "name_label": rec.get("name_label", ""),
            "name_description": rec.get("name_description", ""),
            "bridge": rec.get("bridge", ""),
            "MTU": rec.get("MTU", "1500"),
            "default_locking_mode": rec.get("default_locking_mode", ""),
            "other_config": rec.get("other_config", {}),
            "tags": rec.get("tags", []),
            "vifs": vifs,
            "pifs": pifs,
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


# ══════════════════════════════════════════════════════════════════════
# NETWORK ACTIONS
# ══════════════════════════════════════════════════════════════════════

class NetworkCreateRequest(BaseModel):
    name_label: str
    name_description: str = ""
    mtu: int = 1500

@router.post("/networks")
async def create_network(pool_id: int, body: NetworkCreateRequest,
                         current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        net_ref = pc.network_create(body.name_label, body.name_description, body.mtu)
        return {"status": "ok", "network_ref": net_ref}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.post("/networks/{net_ref:path}/destroy")
async def destroy_network(pool_id: int, net_ref: str,
                          current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        task_ref = pc.network_destroy(net_ref)
        return {"status": "ok", "task_ref": task_ref}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


# ══════════════════════════════════════════════════════════════════════
# PIFs (Physical Interfaces)
# ══════════════════════════════════════════════════════════════════════

@router.get("/hosts/{host_ref:path}/pifs")
async def list_host_pifs(pool_id: int, host_ref: str,
                         current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        pifs = pc.get_host_pifs(host_ref)
        result = []
        for p in pifs:
            result.append({
                "ref": p.get("uuid", ""),
                "device": p.get("device", ""),
                "MAC": p.get("MAC", ""),
                "MTU": p.get("MTU", "1500"),
                "VLAN": p.get("VLAN", "-1"),
                "physical": p.get("physical", False),
                "currently_attached": p.get("currently_attached", True),
                "network": p.get("network", ""),
                "IP": p.get("IP", ""),
                "netmask": p.get("netmask", ""),
                "gateway": p.get("gateway", ""),
                "DNS": p.get("DNS", ""),
                "bond_master_of": p.get("bond_master_of", []),
                "bond_slave_of": p.get("bond_slave_of", ""),
            })
        return {"total": len(result), "pifs": result}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


# ══════════════════════════════════════════════════════════════════════
# VLAN
# ══════════════════════════════════════════════════════════════════════

class VLANCreateRequest(BaseModel):
    pif_ref: str
    vlan_id: int
    network_ref: str

@router.post("/vlans")
async def create_vlan(pool_id: int, body: VLANCreateRequest,
                      current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        vlan_ref = pc.vlan_create(body.pif_ref, body.vlan_id, body.network_ref)
        return {"status": "ok", "vlan_ref": vlan_ref}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


# ══════════════════════════════════════════════════════════════════════
# BOND
# ══════════════════════════════════════════════════════════════════════

class BondCreateRequest(BaseModel):
    pif_refs: list[str]
    network_ref: str
    mode: str = "active-backup"

@router.post("/bonds")
async def create_bond(pool_id: int, body: BondCreateRequest,
                      current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        bond_ref = pc.bond_create(body.pif_refs, body.network_ref, body.mode)
        return {"status": "ok", "bond_ref": bond_ref}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


# ══════════════════════════════════════════════════════════════════════
# VIF (Virtual Interfaces — NIC attach/detach)
# ══════════════════════════════════════════════════════════════════════

class VIFCreateRequest(BaseModel):
    vm_ref: str
    network_ref: str
    device: str = "0"
    mac: str = ""
    mtu: int = 1500

@router.post("/vifs")
async def attach_nic(pool_id: int, body: VIFCreateRequest,
                     current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        vif_ref = pc.vif_create(
            body.vm_ref, body.network_ref, body.device, body.mac, body.mtu
        )
        return {"status": "ok", "vif_ref": vif_ref}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.post("/vifs/{vif_ref:path}/destroy")
async def detach_nic(pool_id: int, vif_ref: str,
                     current_user: UserOut = Depends(get_current_user)):
    pc = _get_pool(pool_id)
    try:
        task_ref = pc.vif_destroy(vif_ref)
        return {"status": "ok", "task_ref": task_ref}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
