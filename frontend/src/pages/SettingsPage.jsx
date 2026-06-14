/**
 * Null — Settings Page
 *
 * Pool management: add, edit, delete, test connection.
 * User management: list, create, delete users.
 */

import { useState, useEffect } from "react";
import { api } from "../api/client";

export default function SettingsPage() {
  return (
    <div className="page">
      <div className="page-header">
        <h2>Settings</h2>
        <p className="page-desc">Configure pools, users, and application preferences</p>
      </div>

      <PoolManager />
      <UserManager />
    </div>
  );
}

// ── Pool Manager ──────────────────────────────────────────────────

function PoolManager() {
  const [pools, setPools] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [connecting, setConnecting] = useState(null);
  const [form, setForm] = useState({
    name: "", host: "", port: 443, username: "root", password: "", verify_ssl: false,
  });

  const loadPools = () => api.get("/pools").then(setPools).catch(() => {});

  useEffect(() => { loadPools(); }, []);

  const handleAdd = async (e) => {
    e.preventDefault();
    await api.post("/pools", form);
    setShowForm(false);
    setForm({ name: "", host: "", port: 443, username: "root", password: "", verify_ssl: false });
    loadPools();
  };

  const handleDelete = async (id) => {
    if (!confirm("Remove this pool?")) return;
    await api.delete(`/pools/${id}`);
    loadPools();
  };

  const handleConnect = async (id) => {
    setConnecting(id);
    try {
      const result = await api.post(`/pools/${id}/connect`);
      alert(`Connected! ${result.host_count} host(s) found.`);
    } catch (err) {
      alert(`Connection failed: ${err.message}`);
    } finally {
      setConnecting(null);
      loadPools();
    }
  };

  return (
    <section className="card settings-section">
      <div className="section-header">
        <h3>XCP-ng Pools</h3>
        <button className="btn-secondary" onClick={() => setShowForm(!showForm)}>
          {showForm ? "Cancel" : "+ Add Pool"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleAdd} className="pool-form">
          <div className="form-row">
            <label className="field">
              <span>Pool Name</span>
              <input type="text" value={form.name} onChange={(e) => setForm({...form, name: e.target.value})} placeholder="Production" required />
            </label>
            <label className="field">
              <span>Host</span>
              <input type="text" value={form.host} onChange={(e) => setForm({...form, host: e.target.value})} placeholder="192.168.1.100" required />
            </label>
          </div>
          <div className="form-row">
            <label className="field">
              <span>Port</span>
              <input type="number" value={form.port} onChange={(e) => setForm({...form, port: parseInt(e.target.value)})} />
            </label>
            <label className="field">
              <span>Username</span>
              <input type="text" value={form.username} onChange={(e) => setForm({...form, username: e.target.value})} />
            </label>
          </div>
          <label className="field">
            <span>Password</span>
            <input type="password" value={form.password} onChange={(e) => setForm({...form, password: e.target.value})} placeholder="XCP-ng root password" />
          </label>
          <label className="field-checkbox">
            <input type="checkbox" checked={form.verify_ssl} onChange={(e) => setForm({...form, verify_ssl: e.target.checked})} />
            <span>Verify SSL certificate</span>
          </label>
          <button type="submit" className="btn-primary">Save Pool</button>
        </form>
      )}

      {pools.length === 0 ? (
        <p className="muted">No pools configured. Add one to get started.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Host</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {pools.map((p) => (
              <tr key={p.id}>
                <td><strong>{p.name}</strong></td>
                <td className="muted">{p.host}:{p.port}</td>
                <td><span className={`badge ${p.status}`}>{p.status}</span></td>
                <td className="actions-cell">
                  <button className="btn-small" onClick={() => handleConnect(p.id)} disabled={connecting === p.id}>
                    {connecting === p.id ? "..." : "Test"}
                  </button>
                  <button className="btn-small btn-danger" onClick={() => handleDelete(p.id)}>✕</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

// ── User Manager ──────────────────────────────────────────────────

function UserManager() {
  const [users, setUsers] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ username: "", password: "", role: "admin" });

  const loadUsers = () => api.get("/users").then(setUsers).catch(() => {});

  useEffect(() => { loadUsers(); }, []);

  const handleAdd = async (e) => {
    e.preventDefault();
    await api.post("/users", form);
    setShowForm(false);
    setForm({ username: "", password: "", role: "admin" });
    loadUsers();
  };

  const handleDelete = async (id) => {
    if (!confirm("Delete this user?")) return;
    try {
      await api.delete(`/users/${id}`);
      loadUsers();
    } catch (err) {
      alert(err.message);
    }
  };

  return (
    <section className="card settings-section">
      <div className="section-header">
        <h3>Users</h3>
        <button className="btn-secondary" onClick={() => setShowForm(!showForm)}>
          {showForm ? "Cancel" : "+ Add User"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleAdd} className="pool-form">
          <div className="form-row">
            <label className="field">
              <span>Username</span>
              <input type="text" value={form.username} onChange={(e) => setForm({...form, username: e.target.value})} required />
            </label>
            <label className="field">
              <span>Password</span>
              <input type="password" value={form.password} onChange={(e) => setForm({...form, password: e.target.value})} required />
            </label>
          </div>
          <button type="submit" className="btn-primary">Create User</button>
        </form>
      )}

      <table className="data-table">
        <thead>
          <tr><th>Username</th><th>Role</th><th>Created</th><th>Actions</th></tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id}>
              <td><strong>{u.username}</strong></td>
              <td><span className="badge">{u.role}</span></td>
              <td className="muted">{u.created_at?.slice(0, 10)}</td>
              <td className="actions-cell">
                <button className="btn-small btn-danger" onClick={() => handleDelete(u.id)}>✕</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
