"""
Null — XAPI XML-RPC Client

Talks to XCP-ng's XAPI over HTTPS XML-RPC. Manages:
  - Session authentication (login_with_password / logout)
  - Arbitrary XAPI method calls with session ref
  - Connection state tracking per pool

XAPI protocol basics:
  1. Open HTTPS connection to https://<host>/
  2. Call session.login_with_password(user, password, client_id)
  3. Use returned session ref as first argument to all other calls
  4. Call session.logout(session_ref) when done

Reference: https://xapi-project.github.io/xen-api/
"""

import ssl
import xmlrpc.client
from typing import Any, Optional
from dataclasses import dataclass, field


@dataclass
class PoolConnection:
    """Represents an active (or cached) connection to one XCP-ng pool."""

    pool_id: int
    name: str
    host: str
    port: int = 443
    username: str = "root"
    password: str = ""
    verify_ssl: bool = False

    # Runtime state (not persisted)
    _session: Optional[str] = field(default=None, repr=False)
    _proxy: Optional[xmlrpc.client.ServerProxy] = field(default=None, repr=False)
    _connected: bool = field(default=False, repr=False)

    @property
    def url(self) -> str:
        return f"https://{self.host}:{self.port}/"

    @property
    def proxy(self) -> xmlrpc.client.ServerProxy:
        """Lazy-create the XML-RPC proxy."""
        if self._proxy is None:
            if self.verify_ssl:
                ctx = ssl.create_default_context()
            else:
                ctx = ssl._create_unverified_context()
            transport = xmlrpc.client.SafeTransport(context=ctx)
            self._proxy = xmlrpc.client.ServerProxy(self.url, transport=transport)
        return self._proxy

    def connect(self) -> None:
        """Authenticate with XAPI and store the session reference."""
        if self._connected and self._session:
            return  # already connected

        try:
            result = self.proxy.session.login_with_password(
                self.username, self.password, "null"
            )
            self._session = result["Value"]
            self._connected = True
        except Exception as e:
            self._connected = False
            self._session = None
            raise ConnectionError(
                f"Failed to connect to XCP-ng pool '{self.name}' at {self.url}: {e}"
            )

    def disconnect(self) -> None:
        """Log out of the XAPI session."""
        if self._session:
            try:
                self.proxy.session.logout(self._session)
            except Exception:
                pass  # best-effort cleanup
        self._session = None
        self._connected = False
        self._proxy = None  # force fresh proxy next time

    def call(self, method: str, *args) -> Any:
        """Call an arbitrary XAPI method.

        Args:
            method: Dotted method name, e.g. "VM.get_all_records" or "host.get_all"
            *args: Arguments to pass (session ref is auto-prepended when needed)

        Returns:
            The XAPI response value (typically a dict or list).
        """
        if not self._connected:
            self.connect()

        parts = method.split(".")
        obj = self.proxy
        for part in parts:
            obj = getattr(obj, part)

        try:
            return obj(self._session, *args)
        except Exception:
            # Session may have expired — reconnect once and retry
            self._connected = False
            self._session = None
            self.connect()
            obj = self.proxy
            for part in parts:
                obj = getattr(obj, part)
            return obj(self._session, *args)

    # ── Convenience: common XAPI queries ──────────────────────────

    def get_hosts(self) -> dict:
        """Return {ref: record} for all hosts in the pool."""
        return self.call("host.get_all_records")

    def get_vms(self) -> dict:
        """Return {ref: record} for all VMs (including templates, snapshots)."""
        return self.call("VM.get_all_records")

    def get_srs(self) -> dict:
        """Return {ref: record} for all Storage Repositories."""
        return self.call("SR.get_all_records")

    def get_networks(self) -> dict:
        """Return {ref: record} for all networks."""
        return self.call("network.get_all_records")

    def get_pool_info(self) -> dict:
        """Return pool master record."""
        pools = self.call("pool.get_all_records")
        return pools if pools else {}

    def get_tasks(self) -> dict:
        """Return {ref: record} for all tasks."""
        return self.call("task.get_all_records")

    def get_messages(self) -> dict:
        """Return {ref: record} for all system messages."""
        return self.call("message.get_all_records")

    def get_features(self) -> list:
        """Return list of supported feature names (for version detection)."""
        try:
            result = self.call("feature.get_all")
            features = []
            for ref in result:
                try:
                    r = self.call("feature.get_record", ref)
                    features.append(r)
                except Exception:
                    pass
            return features
        except Exception:
            return []

    # ── VM lifecycle ────────────────────────────────────────────

    def get_vm_record(self, vm_ref: str) -> dict:
        """Return full record for a single VM."""
        return self.call("VM.get_record", vm_ref)

    def get_vm_metrics(self, vm_ref: str) -> dict:
        """Return live metrics for a VM."""
        try:
            metrics_ref = self.call("VM.get_metrics", vm_ref)
            return self.call("VM_metrics.get_record", metrics_ref)
        except Exception:
            return {}

    def get_vm_guest_metrics(self, vm_ref: str) -> dict:
        """Return guest OS metrics (IP, OS, tools version)."""
        try:
            gm_ref = self.call("VM.get_guest_metrics", vm_ref)
            return self.call("VM_guest_metrics.get_record", gm_ref)
        except Exception:
            return {}

    def get_vm_vbds(self, vm_ref: str) -> list:
        """Return all virtual block devices (disks) for a VM."""
        try:
            vbd_refs = self.call("VM.get_VBDs", vm_ref)
            records = []
            for ref in vbd_refs:
                try:
                    records.append(self.call("VBD.get_record", ref))
                except Exception:
                    pass
            return records
        except Exception:
            return []

    def get_vm_vifs(self, vm_ref: str) -> list:
        """Return all virtual network interfaces for a VM."""
        try:
            vif_refs = self.call("VM.get_VIFs", vm_ref)
            records = []
            for ref in vif_refs:
                try:
                    records.append(self.call("VIF.get_record", ref))
                except Exception:
                    pass
            return records
        except Exception:
            return []

    def get_vm_consoles(self, vm_ref: str) -> list:
        """Return all consoles for a VM (typically VNC)."""
        try:
            console_refs = self.call("VM.get_consoles", vm_ref)
            records = []
            for ref in console_refs:
                try:
                    records.append(self.call("console.get_record", ref))
                except Exception:
                    pass
            return records
        except Exception:
            return []

    # ── VM actions ──────────────────────────────────────────────

    def vm_start(self, vm_ref: str, start_paused: bool = False, force: bool = False) -> str:
        """Start a VM. Returns task ref for async tracking."""
        return self.call("Async.VM.start", vm_ref, start_paused, force)

    def vm_shutdown(self, vm_ref: str) -> str:
        """Clean shutdown (ACPI)."""
        return self.call("Async.VM.clean_shutdown", vm_ref)

    def vm_reboot(self, vm_ref: str) -> str:
        """Clean reboot (ACPI)."""
        return self.call("Async.VM.clean_reboot", vm_ref)

    def vm_hard_reboot(self, vm_ref: str) -> str:
        """Force reboot (power cycle)."""
        return self.call("Async.VM.hard_reboot", vm_ref)

    def vm_hard_shutdown(self, vm_ref: str) -> str:
        """Force power off."""
        return self.call("Async.VM.hard_shutdown", vm_ref)

    def vm_pause(self, vm_ref: str) -> str:
        """Pause (freeze) a running VM."""
        return self.call("Async.VM.pause", vm_ref)

    def vm_unpause(self, vm_ref: str) -> str:
        """Unpause (resume from paused)."""
        return self.call("Async.VM.unpause", vm_ref)

    def vm_suspend(self, vm_ref: str) -> str:
        """Suspend to disk."""
        return self.call("Async.VM.suspend", vm_ref)

    def vm_resume(self, vm_ref: str, start_paused: bool = False, force: bool = False) -> str:
        """Resume from suspended state."""
        return self.call("Async.VM.resume", vm_ref, start_paused, force)

    def vm_migrate(
        self, vm_ref: str, dest_host_ref: str, options: dict | None = None
    ) -> str:
        """Live-migrate a VM to another host in the pool."""
        opts = options or {"live": "true"}
        return self.call("Async.VM.pool_migrate", vm_ref, dest_host_ref, opts)

    def vm_clone(self, vm_ref: str, new_name: str) -> str:
        """Fast-clone a VM."""
        return self.call("Async.VM.clone", vm_ref, new_name)

    def vm_snapshot(self, vm_ref: str, new_name: str) -> str:
        """Take a snapshot of a VM."""
        return self.call("Async.VM.snapshot", vm_ref, new_name)

    def vm_destroy(self, vm_ref: str) -> str:
        """Destroy a VM (and its disks)."""
        return self.call("Async.VM.destroy", vm_ref)

    def vm_set_name(self, vm_ref: str, name: str, description: str = "") -> str:
        """Set VM name and description."""
        self.call("VM.set_name_label", vm_ref, name)
        self.call("VM.set_name_description", vm_ref, description)
        return "ok"

    def vm_set_memory(
        self, vm_ref: str, static_min: int, static_max: int, dynamic_min: int, dynamic_max: int
    ) -> str:
        """Set VM memory limits (bytes)."""
        mem = {
            "static_min": str(static_min),
            "static_max": str(static_max),
            "dynamic_min": str(dynamic_min),
            "dynamic_max": str(dynamic_max),
        }
        return self.call("Async.VM.set_memory_limits", vm_ref, mem)

    def vm_set_vcpus(self, vm_ref: str, vcpus: int) -> str:
        """Set number of vCPUs."""
        self.call("VM.set_VCPUs_max", vm_ref, str(vcpus))
        self.call("VM.set_VCPUs_at_startup", vm_ref, str(vcpus))
        return "ok"

    # ── Template helpers ────────────────────────────────────────

    def get_templates(self) -> dict:
        """Return {ref: record} for all VM templates (is_a_template=true)."""
        all_vms = self.call("VM.get_all_records")
        return {
            ref: rec
            for ref, rec in all_vms.items()
            if rec.get("is_a_template", False)
        }

    # ── Host helpers ────────────────────────────────────────────

    def get_host_record(self, host_ref: str) -> dict:
        """Return record for a single host."""
        return self.call("host.get_record", host_ref)

    # ── Task helpers ────────────────────────────────────────────

    def get_task_record(self, task_ref: str) -> dict:
        """Get task status."""
        return self.call("task.get_record", task_ref)

    def wait_for_task(self, task_ref: str, timeout: int = 30) -> dict:
        """Poll a task until it completes or times out. Blocking."""
        import time

        deadline = time.time() + timeout
        while time.time() < deadline:
            task = self.get_task_record(task_ref)
            status = task.get("status", "pending")
            if status in ("success", "failure", "cancelled"):
                return task
            time.sleep(1)
        return {"status": "timeout", "task_ref": task_ref}

    # ── Storage helpers ──────────────────────────────────────────

    def get_sr_record(self, sr_ref: str) -> dict:
        """Get single SR record."""
        return self.call("SR.get_record", sr_ref)

    def get_vdi_record(self, vdi_ref: str) -> dict:
        """Get single VDI record."""
        return self.call("VDI.get_record", vdi_ref)

    def get_vbd_record(self, vbd_ref: str) -> dict:
        """Get single VBD record."""
        return self.call("VBD.get_record", vbd_ref)

    def get_sr_vdis(self, sr_ref: str) -> list:
        """List all VDIs in a storage repository."""
        try:
            vdi_refs = self.call("SR.get_VDIs", sr_ref)
            records = []
            for ref in vdi_refs:
                try:
                    records.append(self.call("VDI.get_record", ref))
                except Exception:
                    pass
            return records
        except Exception:
            return []

    def get_sr_pbds(self, sr_ref: str) -> list:
        """List all PBDs (host attachments) for an SR."""
        try:
            pbd_refs = self.call("SR.get_PBDs", sr_ref)
            records = []
            for ref in pbd_refs:
                try:
                    records.append(self.call("PBD.get_record", ref))
                except Exception:
                    pass
            return records
        except Exception:
            return []

    def sr_create(
        self, name: str, device_config: dict, sr_type: str = "ext",
        physical_size: int = 0, content_type: str = "user"
    ) -> str:
        """Create a new SR. Returns task ref."""
        return self.call(
            "Async.SR.create", self._session,  # need explicit session for create
            name, device_config, str(physical_size), "user",
            content_type, True, {}
        )

    def sr_forget(self, sr_ref: str) -> str:
        """Forget (unplug) an SR."""
        return self.call("Async.SR.forget", sr_ref)

    def sr_destroy(self, sr_ref: str) -> str:
        """Destroy an SR and all its VDIs."""
        return self.call("Async.SR.destroy", sr_ref)

    def vdi_create(
        self, sr_ref: str, name: str, virtual_size: int,
        vdi_type: str = "user", sharable: bool = False
    ) -> str:
        """Create a new VDI. Returns VDI ref."""
        return self.call(
            "VDI.create", name, sr_ref, str(virtual_size), vdi_type,
            sharable, {}, {}, {}
        )

    def vdi_destroy(self, vdi_ref: str) -> str:
        """Destroy a VDI. Returns task ref."""
        return self.call("Async.VDI.destroy", vdi_ref)

    def vdi_resize(self, vdi_ref: str, new_size: int) -> str:
        """Resize a VDI online. Returns task ref."""
        return self.call("Async.VDI.resize", vdi_ref, str(new_size))

    def vbd_create(self, vm_ref: str, vdi_ref: str, userdevice: str = "",
                   bootable: bool = False, mode: str = "RW",
                   vbd_type: str = "Disk") -> str:
        """Create a VBD (attach disk to VM). Returns VBD ref."""
        return self.call(
            "VBD.create", vm_ref, vdi_ref, userdevice, bootable, mode,
            vbd_type, {}, {}, {}
        )

    def vbd_destroy(self, vbd_ref: str) -> str:
        """Destroy a VBD (detach disk from VM). Returns task ref."""
        return self.call("Async.VBD.destroy", vbd_ref)

    def vbd_plug(self, vbd_ref: str) -> str:
        """Hot-plug a VBD."""
        return self.call("Async.VBD.plug", vbd_ref)

    def vbd_unplug(self, vbd_ref: str) -> str:
        """Hot-unplug a VBD."""
        return self.call("Async.VBD.unplug", vbd_ref)

    # ── Network helpers ──────────────────────────────────────────

    def get_network_record(self, net_ref: str) -> dict:
        """Get single network record."""
        return self.call("network.get_record", net_ref)

    def get_pif_record(self, pif_ref: str) -> dict:
        """Get single PIF record."""
        return self.call("PIF.get_record", pif_ref)

    def get_host_pifs(self, host_ref: str) -> list:
        """List all PIFs on a host."""
        try:
            pif_refs = self.call("host.get_PIFs", host_ref)
            records = []
            for ref in pif_refs:
                try:
                    records.append(self.call("PIF.get_record", ref))
                except Exception:
                    pass
            return records
        except Exception:
            return []

    def network_create(self, name: str, description: str = "",
                       mtu: int = 1500) -> str:
        """Create a new network (bridge). Returns network ref."""
        return self.call(
            "network.create", name, description, str(mtu), {}, {}
        )

    def network_destroy(self, net_ref: str) -> str:
        """Destroy a network. Returns task ref."""
        return self.call("Async.network.destroy", net_ref)

    def vlan_create(self, pif_ref: str, vlan_id: int, network_ref: str) -> str:
        """Create a VLAN on a PIF. Returns VLAN ref."""
        return self.call(
            "VLAN.create", pif_ref, str(vlan_id), network_ref
        )

    def bond_create(self, pif_refs: list, network_ref: str, mode: str = "active-backup") -> str:
        """Create a network bond. Returns bond ref."""
        return self.call(
            "Bond.create", network_ref, pif_refs, mode, {}
        )

    def vif_create(self, vm_ref: str, network_ref: str, device: str = "0",
                   mac: str = "", mtu: int = 1500) -> str:
        """Create a VIF (attach NIC to VM). Returns VIF ref."""
        return self.call(
            "VIF.create", vm_ref, network_ref, device, mac, str(mtu),
            {}, {}, {}, {}
        )

    def vif_destroy(self, vif_ref: str) -> str:
        """Destroy a VIF. Returns task ref."""
        return self.call("Async.VIF.destroy", vif_ref)

    def vif_plug(self, vif_ref: str) -> str:
        """Hot-plug a VIF."""
        return self.call("Async.VIF.plug", vif_ref)

    def vif_unplug(self, vif_ref: str) -> str:
        """Hot-unplug a VIF."""
        return self.call("Async.VIF.unplug", vif_ref)

    # ── PCI / GPU / USB Passthrough ──────────────────────────────

    def get_host_pcis(self, host_ref: str = None) -> list:
        """List all PCI devices (optionally per host)."""
        try:
            if host_ref:
                pci_refs = self.call("host.get_PCIs", host_ref)
            else:
                pci_refs = self.call("PCI.get_all")
            records = []
            for ref in pci_refs:
                try:
                    records.append(self.call("PCI.get_record", ref))
                except Exception:
                    pass
            return records
        except Exception:
            return []

    def get_vm_vgpus(self, vm_ref: str) -> list:
        """List vGPUs attached to a VM."""
        try:
            vgpu_refs = self.call("VM.get_VGPUs", vm_ref)
            records = []
            for ref in vgpu_refs:
                try:
                    records.append(self.call("VGPU.get_record", ref))
                except Exception:
                    pass
            return records
        except Exception:
            return []

    def get_gpu_groups(self) -> list:
        """List available GPU groups (for vGPU assignment)."""
        try:
            group_refs = self.call("GPU_group.get_all")
            records = []
            for ref in group_refs:
                try:
                    r = self.call("GPU_group.get_record", ref)
                    records.append(r)
                except Exception:
                    pass
            return records
        except Exception:
            return []

    def get_vgpu_types(self) -> list:
        """List available vGPU types (profiles)."""
        try:
            type_refs = self.call("VGPU_type.get_all")
            records = []
            for ref in type_refs:
                try:
                    records.append(self.call("VGPU_type.get_record", ref))
                except Exception:
                    pass
            return records
        except Exception:
            return []

    def vgpu_create(self, vm_ref: str, gpu_group_ref: str, vgpu_type_ref: str) -> str:
        """Create a vGPU and attach to VM. Returns VGPU ref."""
        return self.call("VGPU.create", vm_ref, gpu_group_ref, vgpu_type_ref, {}, {})

    def vgpu_destroy(self, vgpu_ref: str) -> str:
        """Destroy a vGPU. Returns task ref."""
        return self.call("Async.VGPU.destroy", vgpu_ref)

    def get_vm_vusbs(self, vm_ref: str) -> list:
        """List USB devices passed through to a VM (VUSBs)."""
        try:
            vusb_refs = self.call("VM.get_VUSBs", vm_ref)
            records = []
            for ref in vusb_refs:
                try:
                    records.append(self.call("VUSB.get_record", ref))
                except Exception:
                    pass
            return records
        except Exception:
            return []

    def get_host_pusbs(self, host_ref: str = None) -> list:
        """List physical USB devices available on host(s)."""
        try:
            if host_ref:
                pusb_refs = self.call("host.get_PUSBs", host_ref)
            else:
                pusb_refs = self.call("PUSB.get_all")
            records = []
            for ref in pusb_refs:
                try:
                    r = self.call("PUSB.get_record", ref)
                    records.append(r)
                except Exception:
                    pass
            return records
        except Exception:
            return []

    def get_usb_groups(self) -> list:
        """List USB groups for passthrough."""
        try:
            group_refs = self.call("USB_group.get_all")
            records = []
            for ref in group_refs:
                try:
                    records.append(self.call("USB_group.get_record", ref))
                except Exception:
                    pass
            return records
        except Exception:
            return []

    def vusb_create(self, vm_ref: str, usb_group_ref: str) -> str:
        """Create a VUSB (pass USB to VM). Returns VUSB ref."""
        return self.call("VUSB.create", vm_ref, usb_group_ref, {}, {})

    def vusb_destroy(self, vusb_ref: str) -> str:
        """Remove a VUSB from a VM. Returns task ref."""
        return self.call("Async.VUSB.destroy", vusb_ref)

    def vm_add_pci(self, vm_ref: str, pci_ref: str) -> str:
        """Add a PCI device to a VM's other-config (pci key)."""
        # XCP-ng PCI passthrough uses other-config:pci
        try:
            current = self.call("VM.get_other_config", vm_ref)
            existing = current.get("pci", "")
            new_pci = f"{existing},{pci_ref}" if existing else pci_ref
            self.call("VM.add_to_other_config", vm_ref, "pci", new_pci)
            return "ok"
        except Exception as e:
            raise Exception(f"PCI passthrough failed: {e}")

    def vm_remove_pci(self, vm_ref: str) -> str:
        """Remove all PCI passthrough from a VM."""
        try:
            self.call("VM.remove_from_other_config", vm_ref, "pci")
            return "ok"
        except Exception as e:
            raise Exception(f"Remove PCI failed: {e}")

    # ── Snapshot helpers ─────────────────────────────────────────

    def get_snapshots(self, vm_ref: str = None) -> dict:
        """Return {ref: record} for all snapshots, optionally filtered by VM."""
        all_vms = self.call("VM.get_all_records")
        snaps = {}
        for ref, rec in all_vms.items():
            if not rec.get("is_a_snapshot", False):
                continue
            if vm_ref and rec.get("snapshot_of", "") != vm_ref:
                continue
            snaps[ref] = rec
        return snaps

    def snapshot_create(self, vm_ref: str, name: str) -> str:
        """Take a snapshot of a VM. Returns task ref."""
        return self.call("Async.VM.snapshot", vm_ref, name)

    def snapshot_revert(self, snap_ref: str) -> str:
        """Revert a VM to a snapshot. Returns task ref."""
        return self.call("Async.VM.revert", snap_ref)

    def snapshot_destroy(self, snap_ref: str) -> str:
        """Delete a snapshot. Returns task ref."""
        return self.call("Async.VM.destroy", snap_ref)

    # ── Event helpers ────────────────────────────────────────────

    def event_register(self, classes: list = None) -> str:
        """Register for events. Returns a registration token."""
        classes = classes or ["*"]
        return self.call("event.register", classes)

    def event_next(self, reg_token: str) -> list:
        """Get the next batch of events. Blocks until events available."""
        return self.call("event.next", reg_token)

    def event_unregister(self, reg_token: str) -> None:
        """Unregister from events."""
        try:
            self.call("event.unregister", reg_token)
        except Exception:
            pass

    # ── Metrics helpers ──────────────────────────────────────────

    def get_host_metrics_snapshot(self) -> list:
        """Get current metrics for all hosts."""
        hosts = self.get_hosts()
        result = []
        for ref, rec in hosts.items():
            m = {}
            try:
                m_ref = self.call("host.get_metrics", ref)
                m = self.call("host_metrics.get_record", m_ref)
            except Exception:
                pass
            result.append({
                "host_ref": rec.get("uuid", ""),
                "host_name": rec.get("name_label", ""),
                "memory_total_mb": self._b2m(m.get("memory_total", "0")),
                "memory_free_mb": self._b2m(m.get("memory_free", "0")),
                "live": m.get("live", False),
            })
        return result

    def get_vm_metrics_snapshot(self) -> list:
        """Get current metrics for all running VMs."""
        vms = self.get_vms()
        result = []
        for ref, rec in vms.items():
            if rec.get("is_a_template") or rec.get("is_control_domain"):
                continue
            m = {}
            try:
                m_ref = self.call("VM.get_metrics", ref)
                m = self.call("VM_metrics.get_record", m_ref)
            except Exception:
                pass
            result.append({
                "vm_ref": rec.get("uuid", ""),
                "vm_name": rec.get("name_label", ""),
                "power_state": rec.get("power_state", ""),
                "memory_actual_mb": self._b2m(m.get("memory_actual", "0")),
                "vcpus_utilisation": m.get("VCPUs_utilisation", {}),
                "vcpus_number": m.get("VCPUs_number", "0"),
            })
        return result

    def get_vm_metrics_history(self, vm_ref: str) -> dict:
        """Get all available metrics for a VM (current snapshot only)."""
        try:
            metrics_ref = self.call("VM.get_metrics", vm_ref)
            return self.call("VM_metrics.get_record", metrics_ref)
        except Exception:
            return {}

    @staticmethod
    def _b2m(val) -> int:
        try: return int(int(val) / (1024 * 1024))
        except: return 0


# ── Pool registry (in-memory, built from DB on startup) ───────────

class PoolRegistry:
    """Thread-safe registry of active pool connections."""

    def __init__(self):
        self._pools: dict[int, PoolConnection] = {}

    def get(self, pool_id: int) -> Optional[PoolConnection]:
        return self._pools.get(pool_id)

    def register(self, conn: PoolConnection) -> None:
        self._pools[conn.pool_id] = conn

    def remove(self, pool_id: int) -> None:
        conn = self._pools.pop(pool_id, None)
        if conn:
            conn.disconnect()

    def list_all(self) -> list[PoolConnection]:
        return list(self._pools.values())

    def shutdown_all(self) -> None:
        for conn in self._pools.values():
            conn.disconnect()
        self._pools.clear()


# Global singleton — populated at startup from SQLite
pool_registry = PoolRegistry()
