/**
 * Null — Network Page
 *
 * Network list → click → detail with VIFs, PIFs
 * Create network, attach NIC to VM
 */

import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";

export default function NetworkPage({ onNavigate }) {
  const [pools, setPools] = useState([]);
  const [selectedPool, setSelectedPool] = useState(null);
  const [networks, setNetworks] = useState([]);
  const [selectedNet, setSelectedNet] = useState(null);
  const [netDetail, setNetDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({ name_label: "", name_description: "", mtu: 1500 });

  useEffect(() => {
    api.get("/pools").then((data) => {
      setPools(data);
      const c = data.find((p) => p.status === "connected");
      if (c) setSelectedPool(c.id);
    }).catch(() => {});
  }, []);

  const fetchNets = useCallback(async () => {
    if (!selectedPool) return;
    setLoading(true);
    setError("");
    try {
      const data = await api.get(`/pools/${selectedPool}/network/networks`);
      setNetworks(data.networks);
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }, [selectedPool]);

  useEffect(() => { fetchNets(); setSelectedNet(null); setNetDetail(null); }, [fetchNets]);

  const viewNet = async (ref) => {
    setSelectedNet(ref);
    setDetailLoading(true);
    try {
      const data = await api.get(`/pools/${selectedPool}/network/networks/${encodeURIComponent(ref)}`);
      setNetDetail(data);
    } catch (err) { setError(err.message); }
    finally { setDetailLoading(false); }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await api.post(`/pools/${selectedPool}/network/networks`, createForm);
      setShowCreate(false);
      setCreateForm({ name_label: "", name_description: "", mtu: 1500 });
      fetchNets();
    } catch (err) { alert(`Create failed: ${err.message}`); }
  };

  const destroyNet = async (ref) => {
    if (!confirm("Destroy this network? This will affect all attached VMs.")) return;
    try {
      await api.post(`/pools/${selectedPool}/network/networks/${encodeURIComponent(ref)}/destroy`);
      fetchNets();
    } catch (err) { alert(`Destroy failed: ${err.message}`); }
  };

  return (
    <div className="page">
      <div className="page-header">
        <h2>Networking</h2>
        <p className="page-desc">Networks, VLANs, bonds, and virtual interfaces</p>
      </div>

      {/* Toolbar */}
      <div className="toolbar">
        <select value={selectedPool || ""} onChange={(e) => setSelectedPool(Number(e.target.value))} className="field-select">
          <option value="">Select pool...</option>
          {pools.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button className="btn-primary" onClick={() => setShowCreate(!showCreate)}>
            {showCreate ? "Cancel" : "+ New Network"}
          </button>
          <button className="btn-secondary" onClick={fetchNets} disabled={loading}>↻</button>
        </div>
      </div>

      {error && <div className="error-banner"><span>{error}</span></div>}

      {/* Create form */}
      {showCreate && (
        <div className="card">
          <h3>Create Network</h3>
          <form onSubmit={handleCreate} className="pool-form">
            <div className="form-row">
              <label className="field"><span>Name *</span><input type="text" value={createForm.name_label} onChange={(e) => setCreateForm({...createForm, name_label: e.target.value})} required /></label>
              <label className="field"><span>MTU</span><input type="number" value={createForm.mtu} onChange={(e) => setCreateForm({...createForm, mtu: parseInt(e.target.value)})} /></label>
            </div>
            <label className="field"><span>Description</span><input type="text" value={createForm.name_description} onChange={(e) => setCreateForm({...createForm, name_description: e.target.value})} /></label>
            <button type="submit" className="btn-primary">Create</button>
          </form>
        </div>
      )}

      {!selectedNet && (
        <>
          {loading && <p className="muted">Loading networks...</p>}
          {!loading && networks.length === 0 && <div className="card empty-state"><p>No networks found.</p></div>}

          <div className="detail-grid">
            {networks.map((net) => (
              <div key={net.ref} className="card sr-card" onClick={() => viewNet(net.ref)} style={{ cursor: "pointer" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <h3 style={{ border: "none", padding: 0, margin: 0 }}>{net.name_label}</h3>
                    <span className="muted" style={{ fontSize: "0.75rem" }}>Bridge: {net.bridge}</span>
                  </div>
                </div>
                <div style={{ display: "flex", gap: "1rem", marginTop: "0.5rem", fontSize: "0.8rem" }}>
                  <span className="muted">MTU {net.MTU}</span>
                  <span className="muted">{net.VIFs} VIFs</span>
                  <span className="muted">{net.PIFs} PIFs</span>
                </div>
                <div style={{ marginTop: "0.5rem" }} onClick={(e) => e.stopPropagation()}>
                  <button className="btn-small btn-danger" onClick={() => destroyNet(net.ref)}>Destroy</button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Network Detail */}
      {selectedNet && (
        <>
          <button className="btn-back" onClick={() => setSelectedNet(null)} style={{ marginBottom: "1rem" }}>← Back to Networks</button>
          {detailLoading && <p className="muted">Loading...</p>}

          {netDetail && (
            <>
              <div className="card">
                <h3>{netDetail.name_label}</h3>
                <div className="detail-grid" style={{ marginTop: "0.5rem" }}>
                  <div><InfoRow label="Bridge" value={netDetail.bridge} /><InfoRow label="MTU" value={netDetail.MTU} /><InfoRow label="Locking Mode" value={netDetail.default_locking_mode || "unlocked"} /></div>
                  <div><InfoRow label="VIFs" value={String(netDetail.vifs?.length || 0)} /><InfoRow label="PIFs" value={String(netDetail.pifs?.length || 0)} /><InfoRow label="Tags" value={netDetail.tags?.join(", ") || "—"} /></div>
                </div>
              </div>

              {/* VIFs */}
              {netDetail.vifs && netDetail.vifs.length > 0 && (
                <div className="card" style={{ padding: 0, overflow: "auto" }}>
                  <h3 style={{ padding: "0.75rem 1rem", margin: 0 }}>Virtual Interfaces (VIFs)</h3>
                  <table className="data-table">
                    <thead><tr><th>Device</th><th>MAC</th><th>MTU</th><th>Attached</th><th>VM</th></tr></thead>
                    <tbody>
                      {netDetail.vifs.map((vif, i) => (
                        <tr key={i}><td><code>eth{vif.device}</code></td><td><code>{vif.MAC}</code></td><td>{vif.MTU}</td><td><span className={`badge ${vif.currently_attached ? "connected" : "disconnected"}`}>{vif.currently_attached ? "Yes" : "No"}</span></td><td className="muted"><code style={{fontSize:"0.7rem"}}>{vif.VM}</code></td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* PIFs */}
              {netDetail.pifs && netDetail.pifs.length > 0 && (
                <div className="card" style={{ padding: 0, overflow: "auto" }}>
                  <h3 style={{ padding: "0.75rem 1rem", margin: 0 }}>Physical Interfaces (PIFs)</h3>
                  <table className="data-table">
                    <thead><tr><th>Device</th><th>MAC</th><th>Host</th><th>IP</th><th>VLAN</th><th>Attached</th></tr></thead>
                    <tbody>
                      {netDetail.pifs.map((pif, i) => (
                        <tr key={i}>
                          <td><code>{pif.device}</code></td>
                          <td><code>{pif.MAC}</code></td>
                          <td>{pif.host_name || "—"}</td>
                          <td><code>{pif.IP || "—"}</code></td>
                          <td>{pif.VLAN && pif.VLAN !== "-1" ? pif.VLAN : "—"}</td>
                          <td><span className={`badge ${pif.currently_attached ? "connected" : "disconnected"}`}>{pif.currently_attached ? "Yes" : "No"}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}

function InfoRow({ label, value }) {
  return <div className="info-row"><span className="muted">{label}</span><span>{value}</span></div>;
}
