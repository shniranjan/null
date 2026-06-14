/**
 * Null — Dashboard
 *
 * Live overview with pool status, host metrics, VM summary, and quick actions.
 * Auto-refreshes every 15 seconds.
 */

import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";

export default function Dashboard({ onNavigate }) {
  const [pools, setPools] = useState([]);
  const [selectedPool, setSelectedPool] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/pools").then((data) => {
      setPools(data);
      const c = data.find((p) => p.status === "connected");
      if (c) setSelectedPool(c.id);
    }).catch(() => {});
  }, []);

  const fetchMetrics = useCallback(async () => {
    if (!selectedPool) return;
    setLoading(true);
    setError("");
    try {
      const data = await api.get(`/pools/${selectedPool}/metrics/dashboard`);
      setMetrics(data);
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }, [selectedPool]);

  useEffect(() => { fetchMetrics(); }, [fetchMetrics]);

  // Auto-refresh every 15s
  useEffect(() => {
    if (!selectedPool) return;
    const interval = setInterval(fetchMetrics, 15000);
    return () => clearInterval(interval);
  }, [fetchMetrics]);

  const usagePercent = (used, total) => total > 0 ? Math.round((used / total) * 100) : 0;

  return (
    <div className="page dashboard-page">
      <div className="page-header">
        <div>
          <h2>Dashboard</h2>
          <p className="page-desc">Overview of your XCP-ng infrastructure</p>
        </div>
        <div className="header-actions">
          <select value={selectedPool || ""} onChange={(e) => setSelectedPool(Number(e.target.value))} className="field-select">
            <option value="">Select pool...</option>
            {pools.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <button className="btn-secondary" onClick={fetchMetrics} disabled={loading}>↻</button>
        </div>
      </div>

      {error && <div className="error-banner"><span>{error}</span></div>}

      {metrics && (
        <>
          {/* VM Summary Cards */}
          <div className="dashboard-grid">
            <div className="card stat-card">
              <span className="stat-value">{metrics.vm_summary?.total || 0}</span>
              <span className="stat-label">Total VMs</span>
            </div>
            <div className="card stat-card">
              <span className="stat-value green">{metrics.vm_summary?.Running || 0}</span>
              <span className="stat-label">Running</span>
            </div>
            <div className="card stat-card">
              <span className="stat-value muted">{metrics.vm_summary?.Halted || 0}</span>
              <span className="stat-label">Halted</span>
            </div>
            <div className="card stat-card">
              <span className="stat-value orange">{metrics.vm_summary?.Paused || 0}</span>
              <span className="stat-label">Paused</span>
            </div>
          </div>

          {/* Host Metrics */}
          <div className="detail-grid" style={{ marginTop: "1rem" }}>
            {metrics.hosts?.map((h, i) => {
              const used = h.memory_total_mb - h.memory_free_mb;
              const pct = usagePercent(used, h.memory_total_mb);
              return (
                <div key={i} className="card">
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <h3 style={{ border: "none", padding: 0, margin: 0 }}>{h.host_name}</h3>
                    <span className={`badge ${h.live ? "connected" : "error"}`}>{h.live ? "Live" : "Down"}</span>
                  </div>
                  <div style={{ marginTop: "0.75rem" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.78rem", marginBottom: "0.25rem" }}>
                      <span className="muted">Memory: {used} / {h.memory_total_mb} MB</span>
                      <span className="muted">{pct}%</span>
                    </div>
                    <div className="usage-bar">
                      <div className="usage-fill" style={{ width: `${pct}%`, background: pct > 80 ? "var(--orange)" : pct > 90 ? "var(--red)" : "var(--green)" }} />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Running VMs Summary */}
          {metrics.vm_metrics?.filter(v => v.power_state === "Running").length > 0 && (
            <div className="card" style={{ marginTop: "1rem", padding: 0, overflow: "auto" }}>
              <h3 style={{ padding: "0.75rem 1rem", margin: 0 }}>Running VMs</h3>
              <table className="data-table">
                <thead><tr><th>VM</th><th>State</th><th>vCPUs</th><th>RAM (MB)</th><th>CPU Usage</th></tr></thead>
                <tbody>
                  {metrics.vm_metrics?.filter(v => v.power_state === "Running").map((v, i) => (
                    <tr key={i} onClick={() => onNavigate?.("vms")} style={{ cursor: "pointer" }}>
                      <td><strong>{v.vm_name}</strong></td>
                      <td><span className="badge running">{v.power_state}</span></td>
                      <td>{v.vcpus_number}</td>
                      <td>{v.memory_actual_mb}</td>
                      <td>
                        {v.vcpus_utilisation && typeof v.vcpus_utilisation === "object" ? (
                          Object.values(v.vcpus_utilisation).map((val, j) => (
                            <span key={j} style={{ marginRight: "0.5rem", fontSize: "0.75rem" }}>
                              CPU{j}: {Math.round(Number(val) * 100)}%
                            </span>
                          ))
                        ) : (
                          <span className="muted">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Quick Actions */}
          <div className="card" style={{ marginTop: "1rem" }}>
            <h3>Quick Actions</h3>
            <div className="quick-actions">
              <button className="btn-primary" onClick={() => onNavigate?.("vm-create")}>+ New VM</button>
              <button className="btn-secondary" onClick={() => onNavigate?.("vms")}>▣ View VMs</button>
              <button className="btn-secondary" onClick={() => onNavigate?.("storage")}>◈ Storage</button>
              <button className="btn-secondary" onClick={() => onNavigate?.("network")}>⬡ Networking</button>
              <button className="btn-secondary" onClick={() => onNavigate?.("snapshots")}>◐ Snapshots</button>
            </div>
          </div>
        </>
      )}

      {!selectedPool && !loading && (
        <div className="card empty-state">
          <p>Select a pool above to view the dashboard.</p>
          <p className="muted">Go to Settings to add your first XCP-ng pool.</p>
        </div>
      )}

      {loading && !metrics && <p className="muted">Loading dashboard...</p>}
    </div>
  );
}
