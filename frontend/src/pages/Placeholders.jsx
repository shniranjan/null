/**
 * Null — Placeholder pages for yet-to-be-built modules.
 */

export function HostsPage() {
  return (
    <div className="page">
      <div className="page-header">
        <h2>Hosts & Pool</h2>
        <p className="page-desc">Manage XCP-ng hosts and pool configuration</p>
      </div>
      <div className="card">
        <p className="muted">Host management coming in Phase 2.</p>
        <p>Features planned: host list, add/remove, enable/disable, HA config, patching.</p>
      </div>
    </div>
  );
}

export function VMsPage() {
  return (
    <div className="page">
      <div className="page-header">
        <h2>Virtual Machines</h2>
        <p className="page-desc">Create, manage, and monitor virtual machines</p>
      </div>
      <div className="card">
        <p className="muted">VM management coming in Phase 2.</p>
        <p>Features planned: VM list with filters, create wizard, console, migrate, snapshot.</p>
      </div>
    </div>
  );
}

export function StoragePage() {
  return (
    <div className="page">
      <div className="page-header">
        <h2>Storage</h2>
        <p className="page-desc">Storage repositories, virtual disks, and attachments</p>
      </div>
      <div className="card">
        <p className="muted">Storage management coming in Phase 3.</p>
      </div>
    </div>
  );
}

export function NetworkPage() {
  return (
    <div className="page">
      <div className="page-header">
        <h2>Networking</h2>
        <p className="page-desc">Networks, VLANs, bonds, and virtual interfaces</p>
      </div>
      <div className="card">
        <p className="muted">Network management coming in Phase 3.</p>
      </div>
    </div>
  );
}

export function SnapshotsPage() {
  return (
    <div className="page">
      <div className="page-header">
        <h2>Snapshots</h2>
        <p className="page-desc">VM snapshots, schedules, and protection policies</p>
      </div>
      <div className="card">
        <p className="muted">Snapshot management coming in Phase 4.</p>
      </div>
    </div>
  );
}

export function ConsolePage() {
  return (
    <div className="page">
      <div className="page-header">
        <h2>Console</h2>
        <p className="page-desc">In-browser VNC console access</p>
      </div>
      <div className="card">
        <p className="muted">VNC console coming in Phase 2.</p>
      </div>
    </div>
  );
}

export function AuditPage() {
  return (
    <div className="page">
      <div className="page-header">
        <h2>Audit Log</h2>
        <p className="page-desc">Record of all management actions</p>
      </div>
      <div className="card">
        <p className="muted">Audit log viewer coming in Phase 4.</p>
      </div>
    </div>
  );
}

export function HelpPage() {
  return (
    <div className="page">
      <div className="page-header">
        <h2>Help & Documentation</h2>
        <p className="page-desc">Guides, tutorials, and reference</p>
      </div>
      <div className="card">
        <p>See the <code>docs/</code> directory in the project repository for full documentation.</p>
        <ul style={{ marginTop: "1rem", paddingLeft: "1.5rem" }}>
          <li><strong>Quick Start</strong> — Getting your first pool connected</li>
          <li><strong>VM Management</strong> — Creating and managing VMs</li>
          <li><strong>Storage Guide</strong> — SR types, VDI operations</li>
          <li><strong>Networking</strong> — VLANs, bonds, and virtual networks</li>
          <li><strong>Troubleshooting</strong> — Common issues and solutions</li>
        </ul>
      </div>
    </div>
  );
}
