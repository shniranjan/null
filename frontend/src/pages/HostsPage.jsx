/**
 * Null — Hosts & Pool Page
 *
 * Lists hosts in the pool with metrics, enable/disable, and pool config.
 */

import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";

export default function HostsPage() {
  const [pools, setPools] = useState([]);
  const [selectedPool, setSelectedPool] = useState(null);
  const [hosts, setHosts] = useState([]);
  const [poolInfo, setPoolInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/pools").then((data) => {
      setPools(data);
      const c = data.find((p) => p.status === "connected");
      if (c) setSelectedPool(c.id);
    }).catch(() => {});
  }, []);

  const fetchHosts = useCallback(async () => {
    if (!selectedPool) return;
    setLoading(true);
    setError("");
    try {
      const [hostData, metricData] = await Promise.all([
        api.get(`/pools/${selectedPool}/hosts`),
        api.get(`/pools/${selectedPool}/metrics/hosts`),
      ]);
      setHosts(hostData.hosts);
      setPoolInfo(hostData);
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }, [selectedPool]);

  useEffect(() => { fetchHosts(); }, [fetchHosts]);

  const usagePercent = (used, total) => total > 0 ? Math.round((used / total) * 100) : 0;

  return (
    <div className="page">
      <div className="page-header">
        <h2>Hosts & Pool</h2>
        <p className="page-desc">Manage XCP-ng hosts and pool configuration</p>
      </div>

      <div className="toolbar">
        <select value={selectedPool || ""} onChange={(e) => setSelectedPool(Number(e.target.value))} className="field-select">
          <option value="">Select pool...</option>
          {pools.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <button className="btn-secondary" onClick={fetchHosts} disabled={loading}>↻ Refresh</button>
      </div>

      {error && <div className="error-banner"><span>{error}</span></div>}

      {loading && <p className="muted">Loading hosts...</p>}

      {hosts.map((host, i) => {
        const total = host.metrics?.memory_total || 0;
        const free = host.metrics?.memory_free || 0;
        const used = total - free;
        const pct = usagePercent(used, total);
        const isMaster = host.is_master;

        return (
          <div key={i} className="card" style={{ marginBottom: "1rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <h3 style={{ border: "none", padding: 0, margin: 0 }}>
                  {isMaster && <span title="Pool Master" style={{ color: "var(--accent)", marginRight: "0.4rem" }}>★</span>}
                  {host.name_label}
                </h3>
                <p className="muted">{host.address}</p>
              </div>
              <div style={{ display: "flex", gap: "0.4rem" }}>
                {isMaster && <span className="badge admin">Master</span>}
                <span className={`badge ${host.enabled ? "connected" : "disconnected"}`}>
                  {host.enabled ? "Enabled" : "Disabled"}
                </span>
                <span className={`badge ${host.metrics?.live ? "running" : "halted"}`}>
                  {host.metrics?.live ? "Live" : "Offline"}
                </span>
              </div>
            </div>

            <div className="detail-grid" style={{ marginTop: "1rem" }}>
              <div>
                <InfoRow label="CPU Count" value={host.cpu_info || "—"} />
                <InfoRow label="Product Version" value={host.software_version?.product_version || "—"} />
                <InfoRow label="Build" value={host.software_version?.build_number || "—"} />
              </div>
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", marginBottom: "0.25rem" }}>
                  <span className="muted">Memory</span>
                  <span className="muted">{used} / {total} MB ({pct}%)</span>
                </div>
                <div className="usage-bar">
                  <div className="usage-fill" style={{ width: `${pct}%`, background: pct > 80 ? "var(--orange)" : pct > 90 ? "var(--red)" : "var(--green)" }} />
                </div>
              </div>
            </div>
          </div>
        );
      })}

      {!loading && hosts.length === 0 && !error && (
        <div className="card empty-state"><p>No hosts found in this pool.</p></div>
      )}
    </div>
  );
}

function InfoRow({ label, value }) {
  return <div className="info-row"><span className="muted">{label}</span><span>{value}</span></div>;
}
