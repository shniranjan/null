/**
 * Null — Help & Documentation Page
 *
 * Built-in documentation browser. Fetches markdown docs from the backend
 * and renders them with basic formatting.
 */

import { useState, useEffect } from "react";
import { api } from "../api/client";

export default function HelpPage() {
  const [docs, setDocs] = useState([]);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.get("/docs").then((d) => setDocs(d.docs)).catch(() => {});
  }, []);

  const loadDoc = async (docId) => {
    setSelectedDoc(docId);
    setLoading(true);
    try {
      const data = await api.get(`/docs/${docId}`);
      setContent(data.content);
    } catch (err) {
      setContent(`Error loading document: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Simple markdown-to-HTML rendering
  const renderMarkdown = (md) => {
    if (!md) return "";
    return md
      .replace(/^### (.+)$/gm, "<h4>$1</h4>")
      .replace(/^## (.+)$/gm, "<h3>$1</h3>")
      .replace(/^# (.+)$/gm, "<h2>$1</h2>")
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.+?)\*/g, "<em>$1</em>")
      .replace(/`{3}(\w*)\n([\s\S]*?)`{3}/g, "<pre><code>$2</code></pre>")
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/^---$/gm, "<hr>")
      .replace(/^- (.+)$/gm, "<li>$1</li>")
      .replace(/(<li>.*<\/li>\n?)+/g, "<ul>$&</ul>")
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
      .replace(/\n\n/g, "</p><p>")
      .replace(/^(?!<[hupdltc])/gm, "<p>")
      .replace(/(?<![>\n])$/gm, "</p>");
  };

  return (
    <div className="page">
      <div className="page-header">
        <h2>Help & Documentation</h2>
        <p className="page-desc">Guides, reference, and tutorials — built into the application</p>
      </div>

      <div style={{ display: "flex", gap: "1rem" }}>
        {/* Sidebar nav */}
        <div style={{ width: "220px", flexShrink: 0 }}>
          <div className="card" style={{ position: "sticky", top: "1rem" }}>
            <h3>Topics</h3>
            {docs.map((d) => (
              <button
                key={d.id}
                className={`nav-item ${selectedDoc === d.id ? "active" : ""}`}
                onClick={() => loadDoc(d.id)}
                style={{ width: "100%", textAlign: "left", padding: "0.5rem", marginBottom: "2px" }}
              >
                {d.title}
              </button>
            ))}
            <hr style={{ borderColor: "var(--border)", margin: "0.75rem 0" }} />
            <h3 style={{ fontSize: "0.85rem" }}>About</h3>
            <p className="muted" style={{ fontSize: "0.78rem", lineHeight: 1.6 }}>
              Null v0.1.0<br />
              Docker-based remote management GUI for XCP-ng virtualization hosts.
            </p>
            <p className="muted" style={{ fontSize: "0.78rem", marginTop: "0.5rem" }}>
              <strong>Tech Stack:</strong> FastAPI + React + SQLite + Docker
            </p>
          </div>
        </div>

        {/* Content area */}
        <div className="card" style={{ flex: 1, minHeight: "400px" }}>
          {!selectedDoc && !loading && (
            <div className="empty-state">
              <span style={{ fontSize: "3rem" }}>?</span>
              <h3>Documentation</h3>
              <p className="muted">
                Select a topic from the sidebar to view documentation.
              </p>
              <p className="muted" style={{ marginTop: "0.5rem" }}>
                All guides are also available in the <code>docs/</code> directory of the project repository.
              </p>
            </div>
          )}

          {loading && <p className="muted">Loading...</p>}

          {content && !loading && (
            <div
              className="doc-content"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
            />
          )}
        </div>
      </div>
    </div>
  );
}
