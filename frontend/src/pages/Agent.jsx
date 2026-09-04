import React, { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api.js";
import { Badge, Loading } from "../components/ui.jsx";
import { useApp } from "../store.jsx";

export default function Agent() {
  const { id } = useParams();
  const entityId = Number(id);
  const { toast } = useApp();
  const [entity, setEntity] = useState(null);
  const [reach, setReach] = useState(null);
  const [docs, setDocs] = useState([]);
  const [audit, setAudit] = useState(null);
  const [running, setRunning] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef(null);

  const loadAll = useCallback(async () => {
    try {
      const [r, d] = await Promise.all([api.reachStatus(entityId), api.listDocuments(entityId)]);
      setEntity(r.entity);
      setReach(r.reach);
      setDocs(d);
    } catch (err) {
      toast(err.message, "error");
    }
  }, [entityId, toast]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  useEffect(() => {
    if (entity?.id) {
      api.report(entityId).then((rep) => {
        const last = rep.agent?.audits?.[rep.agent.audits.length - 1];
        if (last) setAudit(last);
      }).catch(() => {});
    }
  }, [entity, entityId]);

  async function runAudit() {
    setRunning(true);
    setAudit(null);
    try {
      const res = await api.runAudit(entityId);
      setAudit(res);
      toast("Audit complete — findings merged into report");
      loadAll();
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setRunning(false);
    }
  }

  async function onUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const doc = await api.uploadDocument(entityId, file);
      toast(`"${doc.filename}" uploaded`);
      loadAll();
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function removeDoc(docId, filename) {
    try {
      await api.deleteDocument(entityId, docId);
      toast(`Deleted "${filename}"`);
      loadAll();
    } catch (err) {
      toast(err.message, "error");
    }
  }

  if (!entity) return <Loading text="Loading agent…" />;

  return (
    <div>
      <div className="topbar">
        <div>
          <h1>AI Reach Agent <span className="muted" style={{ fontWeight: 600, fontSize: 16 }}>· {entity.name}</span></h1>
          <div className="sub">Live web audit: fetches your site, searches your brand, parses documents.</div>
        </div>
        <button className="btn btn-primary" onClick={runAudit} disabled={running}>
          {running ? "Auditing…" : "Run audit"}
        </button>
      </div>

      {running && (
        <div className="card">
          <div className="loading" style={{ padding: 20 }}>
            <span className="spinner" /> Auditing {entity.name} across the web — this can take ~30s…
          </div>
        </div>
      )}

      {!running && audit && (
        <div className="card">
          <div className="card-title">
            <span>Audit log</span>
            <span className="badge green">completed in {(audit.total_duration_ms / 1000).toFixed(1)}s</span>
          </div>
          {audit.summary && <p className="muted" style={{ marginTop: 0 }}>{audit.summary}</p>}
          {audit.steps.map((s) => (
            <div className="step" key={s.step}>
              <div className="step-head">
                <span className="step-num">{s.step}</span>
                {s.title}
              </div>
              <div className="step-thought">{s.thought}</div>
              {s.tool_calls.map((tc, i) => (
                <div className="step-tool" key={i}>
                  <span className="badge" style={{ marginBottom: 6 }}>
                    {tc.tool}{tc.success ? "" : " · failed"}
                  </span>{" "}
                  {tc.success ? "" : <span className="badge red">error</span>}
                  <div style={{ marginTop: 6 }}>
                    {tc.result || tc.error || "—"}
                  </div>
                </div>
              ))}
              {s.output && <div className="step-output">→ {s.output}</div>}
            </div>
          ))}
        </div>
      )}

      {!running && audit && audit.findings.length > 0 && (
        <div className="card">
          <div className="card-title">Findings</div>
          <div style={{ display: "grid", gap: 8 }}>
            {audit.findings.map((f, i) => (
              <div className={`finding ${f.type || "neutral"}`} key={i}>
                <span className="dot" />
                <div>
                  <div className="strong">{f.title}</div>
                  <div className="muted" style={{ fontSize: 12.5 }}>{f.detail}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-2">
        <div className="card">
          <div className="card-title">Reach channels</div>
          {reach ? (
            <div style={{ display: "grid", gap: 8 }}>
              {Object.entries(reach).map(([k, v]) => (
                <div key={k} className="row spread">
                  <div className="strong" style={{ textTransform: "capitalize" }}>{k.replace("_", " ")}</div>
                  <Badge tone={String(v).startsWith("ok") ? "green" : String(v).startsWith("http") ? "amber" : "red"}>{v}</Badge>
                </div>
              ))}
            </div>
          ) : (
            <div className="swot-empty">Checking channels…</div>
          )}
        </div>

        <div className="card">
          <div className="card-title">
            <span>Documents</span>
            <button className="btn btn-ghost btn-sm" onClick={() => fileRef.current?.click()} disabled={uploading}>
              {uploading ? "Uploading…" : "+ Upload"}
            </button>
            <input ref={fileRef} type="file" hidden accept=".pdf,.docx,.pptx,.jpg,.jpeg,.png,.txt,.md" onChange={onUpload} />
          </div>
          <div className="card-title" style={{ marginTop: 0, marginBottom: 8, fontSize: 11 }}>
            PDF · DOCX · PPTX · images · TXT — parsed by OCR (or client-side)
          </div>
          {docs.length === 0 ? (
            <div className="swot-empty">No documents uploaded. Add brochures, plans or reports to enrich the audit.</div>
          ) : (
            <div style={{ display: "grid", gap: 8 }}>
              {docs.map((d) => (
                <div key={d.id} className="row spread" style={{ background: "var(--bg-2)", border: "1px solid var(--border)", borderRadius: 9, padding: "10px 12px" }}>
                  <div style={{ minWidth: 0 }}>
                    <div className="strong" style={{ fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{d.filename}</div>
                    <div className="muted-2" style={{ fontSize: 11.5 }}>
                      {d.source} · {(d.size / 1024).toFixed(0)} KB · {d.text_len} chars
                    </div>
                  </div>
                  <button className="icon-btn danger btn-sm" title="Delete" onClick={() => removeDoc(d.id, d.filename)}>✕</button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
