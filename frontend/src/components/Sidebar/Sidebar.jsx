/**
 * Null — Sidebar Navigation
 */

import { useAuth } from "../../context/AuthContext";

const NAV_ITEMS = [
  { id: "dashboard",  label: "Dashboard",   icon: "◉" },
  { id: "hosts",      label: "Hosts & Pool", icon: "☷" },
  { id: "vms",        label: "Virtual Machines", icon: "▣" },
  { id: "storage",    label: "Storage",      icon: "◈" },
  { id: "network",    label: "Networking",   icon: "⬡" },
  { id: "snapshots",  label: "Snapshots",    icon: "◴" },
  { id: "console",    label: "Console",      icon: "▤" },
  { id: "audit",      label: "Audit Log",    icon: "☰" },
  { id: "settings",   label: "Settings",     icon: "⚙" },
  { id: "help",       label: "Help & Docs",  icon: "?" },
];

export default function Sidebar({ activePage, onNavigate }) {
  const { user, logout } = useAuth();

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="brand-icon">∅</span>
        <span className="brand-text">Null</span>
        <span className="brand-version">v0.1</span>
      </div>

      <nav className="sidebar-nav">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            className={`nav-item ${activePage === item.id ? "active" : ""}`}
            onClick={() => onNavigate(item.id)}
            title={item.label}
          >
            <span className="nav-icon">{item.icon}</span>
            <span className="nav-label">{item.label}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-user">
          <span className="user-icon">●</span>
          <span className="user-name">{user?.username || "user"}</span>
        </div>
        <button className="btn-logout" onClick={logout} title="Sign out">
          ⏻
        </button>
      </div>
    </aside>
  );
}
