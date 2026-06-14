/**
 * Null — Snapshots Page
 *
 * Lists all snapshots across the pool.
 * Filter by VM, create new snapshots, revert, delete.
 */

import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";

export default function SnapshotsPage() {
  const [pools, setPools] = useState([]);
  const [selectedPool, setSelectedPool] = useState(null);
  const [snapshots, setSnapshots] = useState([]);
  const [vms, setVms] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({ vm_ref: "", name_label: "" });

  useEffect(() => {
    api.get("/pools").then((data) => {
      setPools(data);
      const c = data.find((p) => p.status === "connected");
      if (c) setSelectedPool(c.id);
    }).catch(() => {});
  }, []);

  // Load VMs for snapshot target selector
  useEffect(() => {
    if (!selectedPool) return;
    api.get(`/pools/${selectedPool}/vms?power_state=Running`)
      .then((d) => setVms(d.vms))
      .catch(() => {});
  }, [selectedPool]);

  const fetchSnaps = useCallback(async () => {
    if (!selectedPool) return;
    setLoading(true);
    setError("");
    try {
      const data = await api.get(`/pools/${selectedPool}/snapshots`);
      setSnapshots(data.snapshots);
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }, [selectedPool]);

  useEffect(() => { fetchSnaps(); }, [fetchSnaps]);

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await api.post(`/pools/${selectedPool}/snapshots`, createForm);
      setShowCreate(false);
      setCreateForm({ vm_ref: "", name_label: "" });
      fetchSnaps();
    } catch (err) { alert(`Snapshot failed: ${err.message}`); }
  };

  const doRevert = async (ref) => {
    if (!confirm("Revert to this snapshot? This will replace the current VM state.")) return;
    try {
      await api.post(`/pools/${selectedPool}/snapshots/${encodeURIComponent(ref)}/revert`);
      fetchSnaps();
    } catch (err) { alert(`Revert failed: ${err.message}`); }
  };

  const doDelete = async (ref) => {
    if (!confirm("Delete this snapshot? This cannot be undone.")) return;
    try {
      await api.delete(`/pools/${selectedPool}/snapshots/${encodeURIComponent(ref)}`);
      fetchSnaps();
    } catch (err) { alert(`Delete failed: ${err.message}`); }
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h2>Snapshots</h2>
          <p className="page-desc">VM snapshots, schedules, and protection policies</p>
        </div>
        <button className="btn-primary" onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? "Cancel" : "+ Take Snapshot"}
        </button>
      </div>

      {/* Toolbar */}
      <div className="toolbar">
        <select value={selectedPool || ""} onChange={(e) => setSelectedPool(Number(e.target.value))} className="field-select">
          <option value="">Select pool...</option>
          {pools.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <button className="btn-secondary" onClick={fetchSnaps} disabled={loading}>↻ Refresh</button>
      </div>

      {error && <div className="error-banner"><span>{error}</span></div>}

      {/* Create form */}
      {showCreate && (
        <div className="card">
          <h3>Take Snapshot</h3>
          <form onSubmit={handleCreate} className="pool-form">
            <label className="field">
              <span>Target VM *</span>
              <select value={createForm.vm_ref} onChange={(e) => setCreateForm({...createForm, vm_ref: e.target.value})} required className="field-select">
                <option value="">Select VM...</option>
                {vms.map((v) => <option key={v.ref} value={v.ref}>{v.name_label}</option>)}
              </select>
            </label>
            <label className="field">
              <span>Snapshot Name *</span>
              <input type="text" value={createForm.name_label} onChange={(e) => setCreateForm({...createForm, name_label: e.target.value})} placeholder="e.g., pre-upgrade-2026-06-01" required />
            </label>
            <button type="submit" className="btn-primary">Create Snapshot</button>
          </form>
        </div>
      )}

      {/* Snapshots table */}
      {loading && <p className="muted">Loading snapshots...</p>}
      {!loading && snapshots.length === 0 && !error && (
        <div className="card empty-state"><p>No snapshots found. Create one above.</p></div>
      )}

      {snapshots.length > 0 && (
        <div className="card" style={{ padding: 0, overflow: "auto" }}>
          <table className="data-table">
            <thead><tr><th>Name</th><th>VM</th><th>Taken At</th><th>vCPUs</th><th>RAM (MB)</th><th>Parent</th><th>Actions</th></tr></thead>
            <tbody>
              {snapshots.map((s) => (
                <tr key={s.ref}>
                  <td><strong>{s.name_label}</strong></td>
                  <td className="muted"><code style={{fontSize:"0.7rem"}}>{s.snapshot_of}</code></td>
                  <td className="muted">{s.snapshot_time?.slice(0, 19) || "—"}</td>
                  <td>{s.VCPUs_at_startup}</td>
                  <td>{s.memory_static_max_mb}</td>
                  <td>{s.children?.length || 0} children</td>
                  <td>
                    <div className="actions-cell">
                      <button className="btn-small" onClick={() => doRevert(s.ref)} title="Revert to this snapshot">↩ Revert</button>
                      <button className="btn-small btn-danger" onClick={() => doDelete(s.ref)}>✕</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
