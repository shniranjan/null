/**
 * Null — VM Console Page
 *
 * Fetches VNC console info from XAPI and provides browser-based access.
 *
 * Architecture:
 *   1. Backend queries XAPI for console location (host:port)
 *   2. Backend starts a websockify proxy (WebSocket ↔ VNC TCP)
 *   3. Frontend uses noVNC to render the console in-browser
 *
 * For now (Phase 2), we show console info and a direct-connect option.
 * Full noVNC integration with websockify proxy coming in Phase 4.
 */

import { useState, useEffect } from "react";
import { api } from "../api/client";

export default function ConsolePage({ poolId, vmRef, onNavigate }) {
  const [consoles, setConsoles] = useState([]);
  const [vm, setVm] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeConsole, setActiveConsole] = useState(null);

  useEffect(() => {
    if (!poolId || !vmRef) return;
    setLoading(true);
    setError("");

    Promise.all([
      api.get(`/pools/${poolId}/vms/${encodeURIComponent(vmRef)}/console`),
      api.get(`/pools/${poolId}/vms/${encodeURIComponent(vmRef)}`),
    ])
      .then(([consoleData, vmData]) => {
        setConsoles(consoleData.consoles || []);
        setVm(vmData);
        if (consoleData.consoles && consoleData.consoles.length > 0) {
          setActiveConsole(0);
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [poolId, vmRef]);

  if (loading) return <div className="page"><p className="muted">Loading console...</p></div>;
  if (error) return <div className="page"><div className="error-banner">{error}</div></div>;

  const con = consoles[activeConsole];

  return (
    <div className="page console-page">
      <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <button className="btn-back" onClick={() => onNavigate("vm-detail", vmRef)}>
            ← Back to VM
          </button>
          <h2 style={{ marginTop: "0.5rem" }}>
            ▤ Console: {vm?.name_label || vmRef}
          </h2>
          <p className="page-desc">
            {vm?.power_state === "Running"
              ? "VM is running — console should be available."
              : `VM is ${vm?.power_state?.toLowerCase()}. Start the VM to access the console.`}
          </p>
        </div>
      </div>

      {consoles.length === 0 && (
        <div className="card">
          <p className="muted">No console available for this VM.</p>
          <p>Make sure the VM is running and has a VNC console configured.</p>
          {vm?.power_state !== "Running" && (
            <button
              className="btn-primary"
              style={{ marginTop: "1rem" }}
              onClick={async () => {
                await api.post(`/pools/${poolId}/vms/${encodeURIComponent(vmRef)}/start`);
                setTimeout(() => window.location.reload(), 3000);
              }}
            >
              ▶ Start VM
            </button>
          )}
        </div>
      )}

      {consoles.length > 0 && (
        <>
          {/* Console selector tabs */}
          {consoles.length > 1 && (
            <div className="tabs">
              {consoles.map((c, i) => (
                <button
                  key={i}
                  className={`tab-item ${activeConsole === i ? "active" : ""}`}
                  onClick={() => setActiveConsole(i)}
                >
                  Console {i + 1} ({c.protocol})
                </button>
              ))}
            </div>
          )}

          {/* Console info */}
          <div className="card" style={{ marginBottom: "1rem" }}>
            <div className="info-row">
              <span className="muted">Protocol</span>
              <span><code>{con.protocol.toUpperCase()}</code></span>
            </div>
            <div className="info-row">
              <span className="muted">Location</span>
              <span><code>{con.location}</code></span>
            </div>
            <div className="info-row">
              <span className="muted">UUID</span>
              <span><code style={{ fontSize: "0.7rem" }}>{con.uuid}</code></span>
            </div>
          </div>

          {/* Console viewer area */}
          <div className="card console-viewer">
            <div className="console-placeholder">
              <span style={{ fontSize: "3rem" }}>▤</span>
              <h3>VNC Console</h3>
              <p className="muted" style={{ maxWidth: "500px", textAlign: "center" }}>
                Full in-browser console with noVNC coming in Phase 4.
                <br />
                For now, connect directly using any VNC client:
              </p>
              <code className="console-address">
                {con.location}
              </code>
              <div style={{ marginTop: "1rem", display: "flex", gap: "0.5rem", flexWrap: "wrap", justifyContent: "center" }}>
                <a
                  href={`vnc://${con.location}`}
                  className="btn-primary"
                  style={{ textDecoration: "none" }}
                >
                  Open in VNC Client
                </a>
                <button
                  className="btn-secondary"
                  onClick={() => {
                    navigator.clipboard.writeText(con.location);
                  }}
                >
                  Copy Address
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
