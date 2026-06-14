/**
 * Null — Audit Log Page
 *
 * Full audit log viewer with pagination, action type filter.
 */

import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";

const ACTIONS = ["", "vm.start", "vm.shutdown", "vm.reboot", "vm.destroy", "vm.migrate",
  "vm.clone", "vm.create", "pool.connect", "sr.create", "sr.destroy", "network.create"];

export default function AuditPage() {
  const [entries, setEntries] = useState([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [limit] = useState(50);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(false);

  const fetchLog = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.get(`/audit?limit=${limit}&offset=${offset}`);
      setEntries(data.entries);
      setTotal(data.total);
    } catch (err) { /* ignore */ }
    finally { setLoading(false); }
  }, [offset]);

  useEffect(() => { fetchLog(); }, [fetchLog]);

  const filtered = filter ? entries.filter((e) => e.action === filter) : entries;
  const totalPages = Math.ceil(total / limit);
  const page = Math.floor(offset / limit) + 1;

  return (
    <div className="page">
      <div className="page-header">
        <h2>Audit Log</h2>
        <p className="page-desc">Record of all management actions ({total} entries)</p>
      </div>

      <div className="toolbar">
        <select value={filter} onChange={(e) => setFilter(e.target.value)} className="field-select">
          <option value="">All actions</option>
          {ACTIONS.filter(Boolean).map((a) => <option key={a} value={a}>{a}</option>)}
        </select>
        <div className="toolbar-right">
          <span className="muted">Page {page} of {totalPages || 1}</span>
          <button className="btn-small" onClick={() => setOffset(Math.max(0, offset - limit))} disabled={offset === 0}>← Prev</button>
          <button className="btn-small" onClick={() => setOffset(offset + limit)} disabled={offset + limit >= total}>Next →</button>
          <button className="btn-secondary" onClick={fetchLog} disabled={loading}>↻</button>
        </div>
      </div>

      <div className="card" style={{ padding: 0, overflow: "auto" }}>
        <table className="data-table">
          <thead><tr><th>Time</th><th>User</th><th>Action</th><th>Target</th><th>Pool</th><th>Details</th></tr></thead>
          <tbody>
            {filtered.map((e) => (
              <tr key={e.id}>
                <td className="muted" style={{ fontSize: "0.75rem", whiteSpace: "nowrap" }}>{e.timestamp?.slice(0, 19) || "—"}</td>
                <td>{e.username}</td>
                <td><span className="badge muted" style={{fontSize:"0.65rem"}}>{e.action}</span></td>
                <td>{e.target_type} {e.target_name && `"${e.target_name}"`}</td>
                <td className="muted">{e.pool_name || "—"}</td>
                <td className="muted" style={{ maxWidth: "250px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{e.details || "—"}</td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr><td colSpan="6" className="muted" style={{ textAlign: "center", padding: "2rem" }}>No audit entries found.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
