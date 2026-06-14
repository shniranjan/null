/**
 * Null — Virtual Machines List Page
 *
 * Features:
 *  - Table with sortable columns: name, power state, vCPUs, RAM, host
 *  - Search box (filters by name)
 *  - Power state filter dropdown
 *  - Action buttons per VM: start, shutdown, reboot, console
 *  - Click row → VM detail page
 *  - Pool selector (if multiple pools)
 *  - Auto-refresh toggle
 */

import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";

const STATE_COLORS = {
  Running:    "green",
  Halted:     "muted",
  Paused:     "orange",
  Suspended:  "orange",
};

export default function VMsPage({ onNavigate, setPoolContext }) {
  const [pools, setPools] = useState([]);
  const [selectedPool, setSelectedPool] = useState(null);
  const [vms, setVms] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [powerFilter, setPowerFilter] = useState("");
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [actionBusy, setActionBusy] = useState({});

  // Load pools
  useEffect(() => {
    api.get("/pools").then(setPools).catch(() => {});
  }, []);

  // Auto-select first connected pool
  useEffect(() => {
    if (!selectedPool && pools.length > 0) {
      const connected = pools.find((p) => p.status === "connected");
      if (connected) {
        setSelectedPool(connected.id);
        setPoolContext?.(connected.id);
      }
    }
  }, [pools, selectedPool]);

  // Fetch VMs
  const fetchVMs = useCallback(async () => {
    if (!selectedPool) return;
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      if (powerFilter) params.set("power_state", powerFilter);
      if (search) params.set("search", search);
      params.set("include_templates", "false");

      const data = await api.get(`/pools/${selectedPool}/vms?${params}`);
      setVms(data.vms);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [selectedPool, powerFilter, search]);

  useEffect(() => { fetchVMs(); }, [fetchVMs]);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(fetchVMs, 5000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchVMs]);

  // VM action
  const doAction = async (vmRef, action, label) => {
    setActionBusy((prev) => ({ ...prev, [vmRef + action]: true }));
    try {
      await api.post(`/pools/${selectedPool}/vms/${encodeURIComponent(vmRef)}/${action}`);
      setTimeout(fetchVMs, 1500); // Wait for task to start, then refresh
    } catch (err) {
      alert(`${label} failed: ${err.message}`);
    } finally {
      setActionBusy((prev) => ({ ...prev, [vmRef + action]: false }));
    }
  };

  // Pool selector
  const poolOptions = pools.map((p) => (
    <option key={p.id} value={p.id}>
      {p.name} ({p.status})
    </option>
  ));

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h2>Virtual Machines</h2>
          <p className="page-desc">Manage virtual machines across your pools</p>
        </div>
        <div className="header-actions">
          <button className="btn-primary" onClick={() => onNavigate("vm-create")}>
            + New VM
          </button>
        </div>
      </div>

      {/* Toolbar */}
      <div className="toolbar">
        <div className="toolbar-left">
          <select
            value={selectedPool || ""}
            onChange={(e) => {
              const pid = Number(e.target.value);
              setSelectedPool(pid);
              setPoolContext?.(pid);
            }}
            className="field-select"
          >
            <option value="">Select pool...</option>
            {poolOptions}
          </select>

          <select
            value={powerFilter}
            onChange={(e) => setPowerFilter(e.target.value)}
            className="field-select"
          >
            <option value="">All states</option>
            <option value="Running">Running</option>
            <option value="Halted">Halted</option>
            <option value="Paused">Paused</option>
            <option value="Suspended">Suspended</option>
          </select>

          <input
            type="text"
            placeholder="Search VMs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="field-input"
          />
        </div>

        <div className="toolbar-right">
          <label className="field-checkbox">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            <span>Auto-refresh</span>
          </label>
          <button className="btn-secondary" onClick={fetchVMs} disabled={loading}>
            {loading ? "..." : "↻ Refresh"}
          </button>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button onClick={fetchVMs}>Retry</button>
        </div>
      )}

      {/* VM Table */}
      {!selectedPool && (
        <div className="card empty-state">
          <p>Select a pool above to view virtual machines.</p>
        </div>
      )}

      {selectedPool && !loading && vms.length === 0 && !error && (
        <div className="card empty-state">
          <p>No virtual machines found.</p>
          <p className="muted">Create your first VM to get started.</p>
        </div>
      )}

      {selectedPool && vms.length > 0 && (
        <div className="card" style={{ padding: 0, overflow: "auto" }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Power State</th>
                <th>vCPUs</th>
                <th>RAM (MB)</th>
                <th>OS</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {vms.map((vm) => (
                <tr
                  key={vm.ref}
                  onClick={() => onNavigate("vm-detail", vm.ref)}
                  style={{ cursor: "pointer" }}
                >
                  <td>
                    <div className="vm-name-cell">
                      <span className="state-icon" style={{ color: `var(--${STATE_COLORS[vm.power_state] || "muted"})` }}>
                        {vm.power_state === "Running" ? "●" : vm.power_state === "Paused" ? "⏸" : vm.power_state === "Suspended" ? "⏾" : "○"}
                      </span>
                      <strong>{vm.name_label}</strong>
                      {vm.name_description && (
                        <span className="muted vm-desc">{vm.name_description}</span>
                      )}
                    </div>
                  </td>
                  <td>
                    <span className={`badge ${vm.power_state.toLowerCase()}`}>
                      {vm.power_state}
                    </span>
                  </td>
                  <td>{vm.VCPUs_max}</td>
                  <td>{vm.memory_dynamic_max}</td>
                  <td className="muted">{vm.os_version || "—"}</td>
                  <td>
                    <div className="actions-cell" onClick={(e) => e.stopPropagation()}>
                      {vm.power_state === "Halted" && (
                        <button
                          className="btn-small"
                          onClick={() => doAction(vm.ref, "start", "Start")}
                          disabled={actionBusy[vm.ref + "start"]}
                          title="Start VM"
                        >
                          ▶
                        </button>
                      )}
                      {vm.power_state === "Running" && (
                        <>
                          <button
                            className="btn-small"
                            onClick={() => doAction(vm.ref, "shutdown", "Shutdown")}
                            disabled={actionBusy[vm.ref + "shutdown"]}
                            title="Clean shutdown"
                          >
                            ⏹
                          </button>
                          <button
                            className="btn-small"
                            onClick={() => doAction(vm.ref, "reboot", "Reboot")}
                            disabled={actionBusy[vm.ref + "reboot"]}
                            title="Reboot"
                          >
                            ↻
                          </button>
                          <button
                            className="btn-small"
                            onClick={() => doAction(vm.ref, "force-shutdown", "Force off")}
                            disabled={actionBusy[vm.ref + "force-shutdown"]}
                            title="Force power off"
                          >
                            ⏻
                          </button>
                        </>
                      )}
                      {vm.power_state === "Paused" && (
                        <button
                          className="btn-small"
                          onClick={() => doAction(vm.ref, "unpause", "Unpause")}
                          disabled={actionBusy[vm.ref + "unpause"]}
                          title="Resume"
                        >
                          ▶
                        </button>
                      )}
                      {vm.power_state === "Suspended" && (
                        <button
                          className="btn-small"
                          onClick={() => doAction(vm.ref, "resume", "Resume")}
                          disabled={actionBusy[vm.ref + "resume"]}
                          title="Resume"
                        >
                          ▶
                        </button>
                      )}
                      {vm.power_state === "Running" && (
                        <button
                          className="btn-small"
                          onClick={() => onNavigate("vm-console", vm.ref)}
                          title="Open console"
                        >
                          ▤
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {loading && (
        <div className="card">
          <p className="muted">Loading VMs...</p>
        </div>
      )}
    </div>
  );
}
