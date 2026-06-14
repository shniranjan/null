/**
 * Null — Storage Page
 *
 * SR list → click → SR detail with VDIs → attach disk to VM
 */

import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";

export default function StoragePage({ onNavigate }) {
  const [pools, setPools] = useState([]);
  const [selectedPool, setSelectedPool] = useState(null);
  const [srs, setSrs] = useState([]);
  const [selectedSR, setSelectedSR] = useState(null);
  const [srDetail, setSrDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");

  // Load pools
  useEffect(() => {
    api.get("/pools").then((data) => {
      setPools(data);
      const c = data.find((p) => p.status === "connected");
      if (c) setSelectedPool(c.id);
    }).catch(() => {});
  }, []);

  // Load SRs
  const fetchSRs = useCallback(async () => {
    if (!selectedPool) return;
    setLoading(true);
    setError("");
    try {
      const data = await api.get(`/pools/${selectedPool}/storage/srs`);
      setSrs(data.srs);
    } catch (err) {
      setError(err.message);
    } finally { setLoading(false); }
  }, [selectedPool]);

  useEffect(() => { fetchSRs(); setSelectedSR(null); setSrDetail(null); }, [fetchSRs]);

  // Load SR detail
  const viewSR = async (srRef) => {
    setSelectedSR(srRef);
    setDetailLoading(true);
    try {
      const data = await api.get(`/pools/${selectedPool}/storage/srs/${encodeURIComponent(srRef)}`);
      setSrDetail(data);
    } catch (err) {
      setError(err.message);
    } finally { setDetailLoading(false); }
  };

  const srAction = async (srRef, action, label) => {
    if (!confirm(`${label} SR? This cannot be undone.`)) return;
    try {
      await api.post(`/pools/${selectedPool}/storage/srs/${encodeURIComponent(srRef)}/${action}`);
      fetchSRs();
    } catch (err) { alert(`${label} failed: ${err.message}`); }
  };

  const usagePercent = (used, total) => total > 0 ? Math.round((used / total) * 100) : 0;

  return (
    <div className="page">
      <div className="page-header">
        <h2>Storage</h2>
        <p className="page-desc">Storage Repositories, virtual disks, and attachments</p>
      </div>

      {/* Pool selector */}
      <div className="toolbar">
        <select value={selectedPool || ""} onChange={(e) => setSelectedPool(Number(e.target.value))} className="field-select">
          <option value="">Select pool...</option>
          {pools.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <button className="btn-secondary" onClick={fetchSRs} disabled={loading}>↻ Refresh</button>
      </div>

      {error && <div className="error-banner"><span>{error}</span><button onClick={fetchSRs}>Retry</button></div>}

      {!selectedSR && (
        <>
          {/* SR List */}
          {loading && <p className="muted">Loading SRs...</p>}
          {!loading && srs.length === 0 && (
            <div className="card empty-state"><p>No storage repositories found.</p></div>
          )}

          <div className="detail-grid">
            {srs.map((sr) => (
              <div key={sr.ref} className="card sr-card" onClick={() => viewSR(sr.ref)} style={{ cursor: "pointer" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <h3 style={{ border: "none", padding: 0, margin: 0 }}>{sr.name_label}</h3>
                    <span className="badge muted" style={{ fontSize: "0.7rem" }}>{sr.type}</span>
                  </div>
                  <span className="muted">{sr.VDIs} VDIs</span>
                </div>

                {/* Usage bar */}
                <div style={{ marginTop: "0.75rem" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.78rem" }}>
                    <span className="muted">{sr.physical_utilisation} MB used</span>
                    <span className="muted">{sr.physical_size} MB total</span>
                  </div>
                  <div className="usage-bar">
                    <div
                      className="usage-fill"
                      style={{ width: `${usagePercent(sr.physical_utilisation, sr.physical_size)}%` }}
                    />
                  </div>
                </div>

                <div style={{ display: "flex", gap: "0.3rem", marginTop: "0.75rem" }} onClick={(e) => e.stopPropagation()}>
                  <button className="btn-small btn-danger" onClick={() => srAction(sr.ref, "forget", "Forget")}>Forget</button>
                  <button className="btn-small btn-danger" onClick={() => srAction(sr.ref, "destroy", "Destroy")}>Destroy</button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* SR Detail */}
      {selectedSR && (
        <>
          <button className="btn-back" onClick={() => setSelectedSR(null)} style={{ marginBottom: "1rem" }}>
            ← Back to Storage
          </button>

          {detailLoading && <p className="muted">Loading SR detail...</p>}

          {srDetail && (
            <>
              <div className="card">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <h3>{srDetail.name_label}</h3>
                    <p className="muted">{srDetail.name_description}</p>
                  </div>
                  <span className="badge muted">{srDetail.type}</span>
                </div>
                <div className="detail-grid" style={{ marginTop: "1rem" }}>
                  <div><InfoRow label="Type" value={srDetail.type} /><InfoRow label="Content Type" value={srDetail.content_type} /><InfoRow label="Shared" value={srDetail.shared ? "Yes" : "No"} /></div>
                  <div><InfoRow label="Physical Size" value={`${srDetail.physical_size_mb} MB`} /><InfoRow label="Used" value={`${srDetail.physical_utilisation_mb} MB`} /><InfoRow label="Virtual Allocation" value={`${srDetail.virtual_allocation_mb} MB`} /></div>
                </div>
              </div>

              {/* PBDs (host attachments) */}
              {srDetail.pbds && srDetail.pbds.length > 0 && (
                <div className="card" style={{ padding: 0, overflow: "auto" }}>
                  <h3 style={{ padding: "0.75rem 1rem", margin: 0 }}>Host Attachments</h3>
                  <table className="data-table">
                    <thead><tr><th>Host</th><th>Attached</th><th>Device Config</th></tr></thead>
                    <tbody>
                      {srDetail.pbds.map((pbd, i) => (
                        <tr key={i}><td>{pbd.host_name || "—"}</td><td><span className={`badge ${pbd.currently_attached ? "connected" : "disconnected"}`}>{pbd.currently_attached ? "Yes" : "No"}</span></td><td className="muted"><code style={{fontSize:"0.7rem"}}>{JSON.stringify(pbd.device_config)}</code></td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* VDIs */}
              <div className="card" style={{ padding: 0, overflow: "auto" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.75rem 1rem" }}>
                  <h3 style={{ margin: 0 }}>Virtual Disks ({srDetail.vdi_count})</h3>
                </div>
                <table className="data-table">
                  <thead><tr><th>Name</th><th>Size (MB)</th><th>Physical (MB)</th><th>Type</th><th>Snapshot</th></tr></thead>
                  <tbody>
                    {srDetail.vdis.map((v) => (
                      <tr key={v.ref}>
                        <td><strong>{v.name_label}</strong>{!v.managed && <span className="badge disconnected" style={{marginLeft:"0.5rem"}}>unmanaged</span>}</td>
                        <td>{v.virtual_size_mb}</td>
                        <td>{v.physical_utilisation_mb}</td>
                        <td><span className="badge muted">{v.type}</span></td>
                        <td>{v.is_a_snapshot ? "✓" : "—"}</td>
                      </tr>
                    ))}
                    {srDetail.vdis.length === 0 && <tr><td colSpan="5" className="muted" style={{textAlign:"center",padding:"2rem"}}>No VDIs in this SR.</td></tr>}
                  </tbody>
                </table>
              </div>
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
