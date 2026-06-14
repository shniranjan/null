/**
 * Null — Root Application Component
 *
 * Layout: Sidebar + main content area.
 * Navigation uses { page, poolId?, vmRef? } state.
 */

import { useState, useEffect } from "react";
import { AuthProvider, useAuth } from "./context/AuthContext";

import LoginPage from "./pages/LoginPage";
import Sidebar from "./components/Sidebar/Sidebar";
import Dashboard from "./pages/Dashboard";
import SettingsPage from "./pages/SettingsPage";
import VMsPage from "./pages/VMsPage";
import VMDetail from "./pages/VMDetail";
import VMCreate from "./pages/VMCreate";
import ConsolePage from "./pages/ConsolePage";
import StoragePage from "./pages/StoragePage";
import NetworkPage from "./pages/NetworkPage";
import SnapshotsPage from "./pages/SnapshotsPage";
import AuditPage from "./pages/AuditPage";
import HostsPage from "./pages/HostsPage";
import HelpPage from "./pages/HelpPage";

function AuthenticatedApp() {
  const [nav, setNav] = useState({ page: "dashboard" });

  // Navigation helper: call with (page, vmRef?) or for vms page: ("vms")
  const navigate = (page, vmRef) => {
    setNav((prev) => {
      const next = { page };
      // Carry forward poolId if navigating sub-pages within same context
      if (vmRef) next.vmRef = vmRef;
      if (prev.poolId && ["vm-detail", "vm-console", "vm-create", "vm-clone"].includes(page)) {
        next.poolId = prev.poolId;
      }
      return next;
    });
  };

  // When VMsPage is rendered, it needs to set poolId
  const setPoolContext = (poolId) => {
    setNav((prev) => ({ ...prev, poolId }));
  };

  const renderPage = () => {
    switch (nav.page) {
      case "dashboard":
        return <Dashboard onNavigate={navigate} />;
      case "hosts":
        return <HostsPage />;
      case "vms":
        return <VMsPage onNavigate={navigate} setPoolContext={setPoolContext} />;
      case "vm-detail":
        return <VMDetail poolId={nav.poolId} vmRef={nav.vmRef} onNavigate={navigate} />;
      case "vm-create":
        return <VMCreate onNavigate={navigate} />;
      case "vm-console":
        return <ConsolePage poolId={nav.poolId} vmRef={nav.vmRef} onNavigate={navigate} />;
      case "storage":
        return <StoragePage />;
      case "network":
        return <NetworkPage />;
      case "snapshots":
        return <SnapshotsPage />;
      case "console":
        return <ConsolePage onNavigate={navigate} />;
      case "audit":
        return <AuditPage />;
      case "settings":
        return <SettingsPage />;
      case "help":
        return <HelpPage />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <div className="app-layout">
      <Sidebar activePage={nav.page} onNavigate={(page) => setNav({ page })} />
      <main className="main-content">
        {renderPage()}
      </main>
    </div>
  );
}

function AppContent() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner" />
        <p>Loading...</p>
      </div>
    );
  }

  if (!user) {
    return <LoginPage />;
  }

  return <AuthenticatedApp />;
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
