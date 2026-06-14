/**
 * Null — VM Detail Page
 *
 * Shows full VM info with tabs:
 *  - Overview: power state, CPU/RAM, guest info, actions
 *  - Disks: VBD list with sizes, types, boot flag
 *  - Network: VIF list with MAC, IP, network name
 *  - Actions: lifecycle buttons, memory/vCPU editing
 */

import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";

const STATE_COLORS = { Running: "green", Halted: "muted", Paused: "orange", Suspended: "orange" };

export default function VMDetail({ poolId, vmRef, onNavigate }) {
  const [vm, setVm] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("overview");
  const [actionBusy, setActionBusy] = useState(false);

  const fetchVM = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api.get(
        `/pools/${poolId}/vms/${encodeURIComponent(vmRef)}`
      );
      setVm(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [poolId, vmRef]);

  useEffect(() => { fetchVM(); }, [fetchVM]);

  const doAction = async (action, label) => {
    setActionBusy(true);
    try {
      await api.post(`/pools/${poolId}/vms/${encodeURIComponent(vmRef)}/${action}`);
      setTimeout(fetchVM, 1500);
    } catch (err) {
      alert(`${label} failed: ${err.message}`);
    } finally {
      setActionBusy(false);
    }
  };

  if (loading) return <div className="page"><p className="muted">Loading VM details...</p></div>;
  if (error) return <div className="page"><div className="error-banner">{error}</div></div>;
  if (!vm) return <div className="page"><p className="muted">VM not found.</p></div>;

  const isRunning = vm.power_state === "Running";
  const isHalted = vm.power_state === "Halted";

  return (
    <div className="page">
      {/* Header */}
      <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <button className="btn-back" onClick={() => onNavigate("vms")}>← Back to VMs</button>
          <h2 style={{ marginTop: "0.5rem" }}>
            <span className="state-icon" style={{ color: `var(--${STATE_COLORS[vm.power_state] || "muted"})`, fontSize: "1.2rem" }}>
              {isRunning ? "●" : isHalted ? "○" : "⏸"}
            </span>{" "}
            {vm.name_label}
          </h2>
          {vm.name_description && <p className="page-desc">{vm.name_description}</p>}
        </div>
        <div className="action-group">
          {isHalted && <button className="btn-primary" onClick={() => doAction("start", "Start")} disabled={actionBusy}>▶ Start</button>}
          {isRunning && <button className="btn-secondary" onClick={() => doAction("shutdown", "Shutdown")} disabled={actionBusy}>⏹ Shutdown</button>}
          {isRunning && <button className="btn-secondary" onClick={() => doAction("reboot", "Reboot")} disabled={actionBusy}>↻ Reboot</button>}
          {isRunning && <button className="btn-secondary" onClick={() => doAction("force-shutdown", "Force off")} disabled={actionBusy}>⏻ Force Off</button>}
          {isRunning && <button className="btn-secondary" onClick={() => onNavigate("vm-console", vmRef)}>▤ Console</button>}
          {vm.power_state === "Paused" && <button className="btn-primary" onClick={() => doAction("unpause", "Unpause")} disabled={actionBusy}>▶ Resume</button>}
          {vm.power_state === "Suspended" && <button className="btn-primary" onClick={() => doAction("resume", "Resume")} disabled={actionBusy}>▶ Resume</button>}
        </div>
      </div>

      {/* Tabs */}
      <div className="tabs">
        {["overview", "disks", "network", "passthrough", "metrics"].map((t) => (
          <button
            key={t}
            className={`tab-item ${tab === t ? "active" : ""}`}
            onClick={() => setTab(t)}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* Tab: Overview */}
      {tab === "overview" && (
        <div className="detail-grid">
          <div className="card">
            <h3>General</h3>
            <InfoRow label="Power State" value={vm.power_state} badge />
            <InfoRow label="UUID" value={vm.ref} mono />
            <InfoRow label="Template" value={vm.is_a_template ? "Yes" : "No"} />
            <InfoRow label="Snapshot" value={vm.is_a_snapshot ? "Yes" : "No"} />
            <InfoRow label="Tags" value={vm.tags?.join(", ") || "—"} />
          </div>

          <div className="card">
            <h3>Resources</h3>
            <InfoRow label="vCPUs" value={`${vm.VCPUs_max} (${vm.VCPUs_at_startup} at startup)`} />
            <InfoRow label="RAM (dynamic)" value={`${vm.memory_dynamic_min_mb}–${vm.memory_dynamic_max_mb} MB`} />
            <InfoRow label="RAM (static)" value={`${vm.memory_static_min_mb}–${vm.memory_static_max_mb} MB`} />
            <InfoRow label="Boot Policy" value={vm.HVM_boot_policy || vm.PV_bootloader || "—"} />
          </div>

          <div className="card">
            <h3>Guest OS</h3>
            <InfoRow label="OS" value={vm.guest_metrics?.os_version?.name || vm.os_version?.name || "Unknown"} />
            <InfoRow label="PV Drivers" value={vm.guest_metrics?.PV_drivers_version?.major ? `v${vm.guest_metrics.PV_drivers_version.major}.${vm.guest_metrics.PV_drivers_version.minor || 0}` : "Not installed"} />
            <InfoRow label="Drivers Up to Date" value={vm.guest_metrics?.PV_drivers_up_to_date ? "Yes" : "No"} />
            <InfoRow label="Guest Memory" value={vm.guest_metrics?.memory ? `${vm.guest_metrics.memory} MB` : "—"} />
          </div>

          <div className="card">
            <h3>Host</h3>
            <InfoRow label="Resident On" value={vm.resident_on_name || "—"} />
            <InfoRow label="Affinity" value={vm.affinity || "—"} />
            <InfoRow label="Platform" value={JSON.stringify(vm.platform) !== "{}" ? JSON.stringify(vm.platform) : "—"} />
          </div>
        </div>
      )}

      {/* Tab: Disks */}
      {tab === "disks" && (
        <div className="card" style={{ padding: 0, overflow: "auto" }}>
          <table className="data-table">
            <thead>
              <tr><th>Device</th><th>Name</th><th>Size (MB)</th><th>Physical (MB)</th><th>Type</th><th>Bootable</th><th>Mode</th><th>Attached</th></tr>
            </thead>
            <tbody>
              {vm.vbds?.map((vbd, i) => (
                <tr key={vbd.ref || i}>
                  <td><code>{vbd.userdevice || vbd.device}</code></td>
                  <td>{vbd.vdi?.name_label || "—"}</td>
                  <td>{vbd.vdi?.virtual_size || "—"}</td>
                  <td>{vbd.vdi?.physical_utilisation || "—"}</td>
                  <td>{vbd.type === "Disk" ? "Disk" : "CD"}</td>
                  <td>{vbd.bootable ? "✓" : "—"}</td>
                  <td>{vbd.mode}</td>
                  <td><span className={`badge ${vbd.currently_attached ? "connected" : "disconnected"}`}>{vbd.currently_attached ? "Yes" : "No"}</span></td>
                </tr>
              ))}
              {(!vm.vbds || vm.vbds.length === 0) && (
                <tr><td colSpan="8" className="muted" style={{ textAlign: "center", padding: "2rem" }}>No disks attached.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab: Network */}
      {tab === "network" && (
        <div className="card" style={{ padding: 0, overflow: "auto" }}>
          <table className="data-table">
            <thead>
              <tr><th>Device</th><th>MAC</th><th>Network</th><th>MTU</th><th>IPv4</th><th>IPv6</th><th>Attached</th></tr>
            </thead>
            <tbody>
              {vm.vifs?.map((vif, i) => (
                <tr key={vif.ref || i}>
                  <td><code>eth{vif.device}</code></td>
                  <td><code>{vif.MAC}</code></td>
                  <td>{vif.network?.name_label || "—"}</td>
                  <td>{vif.MTU}</td>
                  <td><code>{vif.ipv4_addresses || "—"}</code></td>
                  <td><code>{vif.ipv6_addresses || "—"}</code></td>
                  <td><span className={`badge ${vif.currently_attached ? "connected" : "disconnected"}`}>{vif.currently_attached ? "Yes" : "No"}</span></td>
                </tr>
              ))}
              {(!vm.vifs || vm.vifs.length === 0) && (
                <tr><td colSpan="7" className="muted" style={{ textAlign: "center", padding: "2rem" }}>No network interfaces.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab: Passthrough — GPU, USB, PCI */}
      {tab === "passthrough" && (
        <PassthroughTab poolId={poolId} vmRef={vmRef} vmName={vm.name_label} />
      )}

      {/* Tab: Metrics */}
      {tab === "metrics" && (
        <div className="detail-grid">
          <div className="card">
            <h3>VM Metrics</h3>
            <InfoRow label="Memory Actual" value={`${vm.metrics?.memory_actual || 0} MB`} />
            <InfoRow label="vCPU Utilisation" value={vm.metrics?.vcpus_utilisation ? JSON.stringify(vm.metrics.vcpus_utilisation) : "—"} />
          </div>
          <div className="card">
            <h3>Guest Disks</h3>
            {vm.guest_metrics?.disks && Object.keys(vm.guest_metrics.disks).length > 0 ? (
              Object.entries(vm.guest_metrics.disks).map(([k, v]) => (
                <InfoRow key={k} label={k} value={typeof v === "object" ? JSON.stringify(v) : String(v)} />
              ))
            ) : (
              <p className="muted">No guest disk metrics available. Install Xen guest tools in the VM.</p>
            )}
          </div>
        </div>
      )}

      {/* Danger Zone */}
      <div className="card danger-zone">
        <h3>Danger Zone</h3>
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          {isHalted && (
            <button className="btn-danger" onClick={() => { if (confirm(`Destroy VM "${vm.name_label}"? This cannot be undone.`)) doAction("destroy", "Destroy"); }}>
              ⚠ Destroy VM
            </button>
          )}
          <button className="btn-secondary" onClick={() => onNavigate("vm-clone", vmRef)}>
            ⧉ Clone VM
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Passthrough Tab Component ──────────────────────────────────────

function PassthroughTab({ poolId, vmRef, vmName }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [subtab, setSubTab] = useState("gpu");
  const [availablePcis, setAvailablePcis] = useState([]);
  const [pciForm, setPciForm] = useState({ pci_ref: "" });

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.get(`/pools/${poolId}/vms/${encodeURIComponent(vmRef)}/passthrough`),
      api.get(`/pools/${poolId}/passthrough/pcis`).catch(() => ({ pcis: [] })),
    ])
      .then(([d, p]) => { setData(d); setAvailablePcis(p.pcis || []); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [poolId, vmRef]);

  const refresh = async () => {
    setLoading(true);
    try {
      const d = await api.get(`/pools/${poolId}/vms/${encodeURIComponent(vmRef)}/passthrough`);
      setData(d);
    } catch (e) { /* ignore */ }
    finally { setLoading(false); }
  };

  const detach = async (endpoint, ref, label) => {
    if (!confirm(`${label}?`)) return;
    try {
      await api.delete(`/pools/${poolId}/vms/${encodeURIComponent(vmRef)}/passthrough/${endpoint}/${encodeURIComponent(ref)}`);
      refresh();
    } catch (err) { alert(`${label} failed: ${err.message}`); }
  };

  const addPci = async (e) => {
    e.preventDefault();
    try {
      await api.post(`/pools/${poolId}/vms/${encodeURIComponent(vmRef)}/passthrough/pci`, pciForm);
      setPciForm({ pci_ref: "" });
      refresh();
    } catch (err) { alert(`PCI passthrough failed: ${err.message}`); }
  };

  if (loading) return <p className="muted">Loading passthrough devices...</p>;
  if (!data) return <p className="muted">Could not load passthrough info.</p>;

  const gpus = data.vgpus || [];
  const usbs = data.vusbs || [];
  const pcis = data.pcis || [];

  return (
    <>
      <div className="tabs" style={{ marginBottom: "0.75rem" }}>
        {["gpu","usb","pci"].map((t) => (
          <button key={t} className={`tab-item ${subtab === t ? "active" : ""}`} onClick={() => setSubTab(t)}>
            {t === "gpu" ? `GPU (${gpus.length})` : t === "usb" ? `USB (${usbs.length})` : `PCI (${pcis.length})`}
          </button>
        ))}
      </div>

      {/* GPU / vGPU */}
      {subtab === "gpu" && (
        <div className="card">
          <h3>vGPU Devices</h3>
          {gpus.length === 0 && <p className="muted">No vGPUs attached. GPU passthrough requires NVIDIA vGPU or AMD MxGPU support on the host.</p>}
          {gpus.map((g, i) => (
            <div key={i} className="info-row" style={{ justifyContent: "space-between" }}>
              <span>
                {g.type_info?.model_name || g.type || "vGPU"}
                {g.type_info?.vendor_name && <span className="muted"> ({g.type_info.vendor_name})</span>}
              </span>
              <div style={{ display: "flex", gap: "0.3rem" }}>
                <span className={`badge ${g.currently_attached ? "connected" : "disconnected"}`}>{g.currently_attached ? "Attached" : "Detached"}</span>
                <button className="btn-small btn-danger" onClick={() => detach("vgpu", g.ref, "Detach vGPU")}>✕</button>
              </div>
            </div>
          ))}
          <p className="muted" style={{ marginTop: "0.75rem", fontSize: "0.78rem" }}>
            To attach a new vGPU, use the <strong>Settings → GPU</strong> section of the VM properties in XenCenter/XO, then refresh this page.
          </p>
        </div>
      )}

      {/* USB */}
      {subtab === "usb" && (
        <div className="card">
          <h3>USB Passthrough</h3>
          {usbs.length === 0 && <p className="muted">No USB devices passed through.</p>}
          {usbs.map((u, i) => (
            <div key={i} className="info-row" style={{ justifyContent: "space-between" }}>
              <span>
                {u.usb_info?.pusb?.product_name || u.usb_info?.name_label || "USB Device"}
                {u.usb_info?.pusb?.vendor_name && <span className="muted"> ({u.usb_info.pusb.vendor_name})</span>}
              </span>
              <div style={{ display: "flex", gap: "0.3rem" }}>
                <span className={`badge ${u.currently_attached ? "connected" : "disconnected"}`}>{u.currently_attached ? "Attached" : "Detached"}</span>
                <button className="btn-small btn-danger" onClick={() => detach("usb", u.ref, "Detach USB")}>✕</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* PCI */}
      {subtab === "pci" && (
        <div className="card">
          <h3>PCI Passthrough</h3>
          {pcis.length === 0 && <p className="muted">No PCI devices passed through.</p>}
          {pcis.map((p, i) => (
            <div key={i} className="info-row" style={{ justifyContent: "space-between" }}>
              <span>
                {p.info?.device_name || p.ref}
                {p.info?.vendor_name && <span className="muted"> — {p.info.vendor_name}</span>}
                {p.info?.pci_id && <span className="muted"> [{p.info.pci_id}]</span>}
              </span>
              <div style={{ display: "flex", gap: "0.3rem" }}>
                <button className="btn-small btn-danger" onClick={async () => {
                  if (!confirm("Remove all PCI passthrough?")) return;
                  try {
                    await api.delete(`/pools/${poolId}/vms/${encodeURIComponent(vmRef)}/passthrough/pci`);
                    refresh();
                  } catch (err) { alert(err.message); }
                }}>Remove All</button>
              </div>
            </div>
          ))}

          {/* Add PCI form */}
          {availablePcis.length > 0 && (
            <form onSubmit={addPci} style={{ marginTop: "1rem", padding: "0.75rem", background: "var(--bg-hover)", borderRadius: "var(--radius)" }}>
              <h4 style={{ fontSize: "0.88rem", marginBottom: "0.5rem" }}>Add PCI Device</h4>
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <select value={pciForm.pci_ref} onChange={(e) => setPciForm({ pci_ref: e.target.value })} className="field-select" style={{ flex: 1 }} required>
                  <option value="">Select PCI device...</option>
                  {availablePcis.map((d) => (
                    <option key={d.ref} value={d.ref}>
                      {d.device_name} — {d.vendor_name} [{d.pci_id}]
                    </option>
                  ))}
                </select>
                <button type="submit" className="btn-primary">Attach</button>
              </div>
              <p className="muted" style={{ fontSize: "0.7rem", marginTop: "0.35rem" }}>
                ⚠ VM must be halted to attach/detach PCI devices. Reboot required after changes.
              </p>
            </form>
          )}
        </div>
      )}
    </>
  );
}

// ── Info Row Component ──────────────────────────────────────────────

function InfoRow({ label, value, badge, mono }) {
  return (
    <div className="info-row">
      <span className="muted">{label}</span>
      <span>
        {badge && value ? (
          <span className={`badge ${value.toLowerCase()}`}>{value}</span>
        ) : mono ? (
          <code style={{ fontSize: "0.7rem" }}>{value}</code>
        ) : (
          value || "—"
        )}
      </span>
    </div>
  );
}
