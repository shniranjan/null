/**
 * Null — VM Create Wizard
 *
 * Step 1: Select pool
 * Step 2: Select template
 * Step 3: Configure (name, vCPUs, RAM, disk, network)
 * Step 4: Review and create
 */

import { useState, useEffect } from "react";
import { api } from "../api/client";

export default function VMCreate({ onNavigate }) {
  const [step, setStep] = useState(1);
  const [pools, setPools] = useState([]);
  const [selectedPool, setSelectedPool] = useState(null);
  const [templates, setTemplates] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({
    name_label: "",
    name_description: "",
    vcpus: 2,
    memory_mb: 2048,
  });

  // Load pools
  useEffect(() => {
    api.get("/pools").then((data) => {
      setPools(data);
      const connected = data.find((p) => p.status === "connected");
      if (connected) setSelectedPool(connected.id);
    }).catch(() => {});
  }, []);

  // Load templates when pool selected
  useEffect(() => {
    if (!selectedPool) return;
    setLoading(true);
    api.get(`/pools/${selectedPool}/templates`)
      .then(setTemplates)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [selectedPool]);

  const handleCreate = async () => {
    setCreating(true);
    try {
      await api.post(`/pools/${selectedPool}/vms`, {
        name_label: form.name_label,
        name_description: form.name_description,
        template_ref: selectedTemplate,
        vcpus: form.vcpus,
        memory_mb: form.memory_mb,
      });
      onNavigate("vms");
    } catch (err) {
      alert(`Creation failed: ${err.message}`);
    } finally {
      setCreating(false);
    }
  };

  const nextStep = () => setStep((s) => Math.min(s + 1, 4));
  const prevStep = () => setStep((s) => Math.max(s - 1, 1));

  return (
    <div className="page">
      <div className="page-header">
        <button className="btn-back" onClick={() => onNavigate("vms")}>← Back to VMs</button>
        <h2 style={{ marginTop: "0.5rem" }}>Create Virtual Machine</h2>
        <p className="page-desc">Step-by-step VM creation wizard</p>
      </div>

      {/* Progress bar */}
      <div className="wizard-progress">
        {["Pool", "Template", "Configure", "Review"].map((label, i) => (
          <div key={label} className={`wizard-step ${step > i + 1 ? "done" : ""} ${step === i + 1 ? "active" : ""}`}>
            <div className="wizard-dot">{step > i + 1 ? "✓" : i + 1}</div>
            <span>{label}</span>
          </div>
        ))}
      </div>

      {/* Step 1: Pool */}
      {step === 1 && (
        <div className="card">
          <h3>Select Pool</h3>
          <p className="muted" style={{ marginBottom: "1rem" }}>Choose which XCP-ng pool to create the VM in.</p>
          {pools.length === 0 ? (
            <p className="muted">No pools configured. Go to Settings to add one.</p>
          ) : (
            <div className="template-grid">
              {pools.map((p) => (
                <button
                  key={p.id}
                  className={`template-card ${selectedPool === p.id ? "selected" : ""}`}
                  onClick={() => setSelectedPool(p.id)}
                >
                  <span className="template-icon">⬡</span>
                  <strong>{p.name}</strong>
                  <span className="muted">{p.host}:{p.port}</span>
                  {p.status !== "connected" && (
                    <span className="badge disconnected">Not connected</span>
                  )}
                </button>
              ))}
            </div>
          )}
          <div style={{ marginTop: "1rem" }}>
            <button className="btn-primary" onClick={nextStep} disabled={!selectedPool}>Next →</button>
          </div>
        </div>
      )}

      {/* Step 2: Template */}
      {step === 2 && (
        <div className="card">
          <h3>Select Template</h3>
          <p className="muted" style={{ marginBottom: "1rem" }}>
            Templates define the OS type, default resources, and boot configuration.
          </p>
          {loading && <p className="muted">Loading templates...</p>}
          {!loading && templates.length === 0 && (
            <p className="muted">No templates found in this pool.</p>
          )}
          <div className="template-grid">
            {templates.map((t) => (
              <button
                key={t.ref}
                className={`template-card ${selectedTemplate === t.ref ? "selected" : ""}`}
                onClick={() => {
                  setSelectedTemplate(t.ref);
                  setForm({
                    ...form,
                    vcpus: parseInt(t.VCPUs_max) || 2,
                    memory_mb: t.memory_static_max || 2048,
                  });
                }}
              >
                <span className="template-icon">
                  {t.name_label?.toLowerCase().includes("windows") ? "⊞" :
                   t.name_label?.toLowerCase().includes("ubuntu") ? "⧂" :
                   t.name_label?.toLowerCase().includes("debian") ? "⟐" :
                   t.name_label?.toLowerCase().includes("centos") ? "◎" : "▣"}
                </span>
                <strong>{t.name_label}</strong>
                <span className="muted">{t.name_description || t.os_version?.name || ""}</span>
                <span className="template-specs">
                  {t.VCPUs_max} vCPU · {t.memory_static_max} MB
                </span>
              </button>
            ))}
          </div>
          <div style={{ marginTop: "1rem", display: "flex", gap: "0.5rem" }}>
            <button className="btn-secondary" onClick={prevStep}>← Back</button>
            <button className="btn-primary" onClick={nextStep} disabled={!selectedTemplate}>Next →</button>
          </div>
        </div>
      )}

      {/* Step 3: Configure */}
      {step === 3 && (
        <div className="card">
          <h3>Configure VM</h3>
          <div className="pool-form" style={{ marginTop: "1rem" }}>
            <label className="field">
              <span>VM Name *</span>
              <input
                type="text"
                value={form.name_label}
                onChange={(e) => setForm({ ...form, name_label: e.target.value })}
                placeholder="e.g., web-server-01"
                required
              />
            </label>
            <label className="field">
              <span>Description</span>
              <input
                type="text"
                value={form.name_description}
                onChange={(e) => setForm({ ...form, name_description: e.target.value })}
                placeholder="Optional description"
              />
            </label>
            <div className="form-row">
              <label className="field">
                <span>vCPUs</span>
                <input
                  type="number"
                  value={form.vcpus}
                  onChange={(e) => setForm({ ...form, vcpus: parseInt(e.target.value) || 1 })}
                  min={1}
                  max={64}
                />
              </label>
              <label className="field">
                <span>Memory (MB)</span>
                <input
                  type="number"
                  value={form.memory_mb}
                  onChange={(e) => setForm({ ...form, memory_mb: parseInt(e.target.value) || 512 })}
                  min={512}
                  step={512}
                />
              </label>
            </div>
          </div>
          <div style={{ marginTop: "1rem", display: "flex", gap: "0.5rem" }}>
            <button className="btn-secondary" onClick={prevStep}>← Back</button>
            <button className="btn-primary" onClick={nextStep} disabled={!form.name_label}>Next →</button>
          </div>
        </div>
      )}

      {/* Step 4: Review */}
      {step === 4 && (
        <div className="card">
          <h3>Review & Create</h3>
          <div style={{ marginTop: "1rem" }}>
            <InfoRow label="Pool" value={pools.find((p) => p.id === selectedPool)?.name || "—"} />
            <InfoRow label="Template" value={templates.find((t) => t.ref === selectedTemplate)?.name_label || "—"} />
            <InfoRow label="Name" value={form.name_label} />
            <InfoRow label="Description" value={form.name_description || "—"} />
            <InfoRow label="vCPUs" value={String(form.vcpus)} />
            <InfoRow label="Memory" value={`${form.memory_mb} MB`} />
          </div>
          <div style={{ marginTop: "1.5rem", display: "flex", gap: "0.5rem" }}>
            <button className="btn-secondary" onClick={prevStep}>← Back</button>
            <button className="btn-primary" onClick={handleCreate} disabled={creating}>
              {creating ? "Creating..." : "✓ Create VM"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function InfoRow({ label, value }) {
  return (
    <div className="info-row">
      <span className="muted">{label}</span>
      <span>{value}</span>
    </div>
  );
}
