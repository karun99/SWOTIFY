import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, tierColor } from "../api.js";
import { Badge, CategoryBars, Loading, ScoreRing, SwotBox } from "../components/ui.jsx";

export default function Report() {
  const { id } = useParams();
  const navigate = useNavigate();
  const entityId = Number(id);
  const [rep, setRep] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.report(entityId).then(setRep).catch((e) => setError(e.message));
  }, [entityId]);

  if (error) return <div className="card muted">{error}</div>;
  if (!rep) return <Loading text="Loading report…" />;

  if (!rep.has_report) {
    return (
      <div className="card">
        <div className="empty-state">
          <div className="big">📝</div>
          <div className="strong">No report yet for {rep.entity?.name}</div>
          <div className="muted" style={{ marginTop: 6 }}>Run the digital profile assessment to generate your SWOT report.</div>
          <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={() => navigate(`/entities/${entityId}/assessment`)}>
            Start assessment
          </button>
        </div>
      </div>
    );
  }

  const agent = rep.agent;
  const auditFindings = agent?.audits?.[agent.audits.length - 1]?.findings || [];

  return (
    <div>
      <div className="topbar">
        <div>
          <h1>Profile Report <span className="muted" style={{ fontWeight: 600, fontSize: 16 }}>· {rep.entity?.name}</span></h1>
          <div className="sub">{rep.verdict?.label} · updated {rep.created_at}</div>
        </div>
        <button className="btn btn-primary" onClick={() => navigate(`/entities/${entityId}/assessment`)}>
          Re-assess
        </button>
      </div>

      <div className="grid grid-3">
        <div className="card" style={{ display: "flex", justifyContent: "center" }}>
          <ScoreRing score={rep.score} />
        </div>
        <div className="card" style={{ gridColumn: "span 2" }}>
          <div className="card-title">Category scores</div>
          <CategoryBars categories={rep.categories} scores={rep.category_scores} />
        </div>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <div className="card-title">Impact — where to focus</div>
          {(rep.impact || []).length === 0 ? (
            <div className="swot-empty">Strong across the board — consolidate and scale.</div>
          ) : (
            (rep.impact || []).map((im, i) => (
              <div className="impact-item" key={i}>
                <div className="impact-tier" style={{ background: `${tierColor(im.tier)}1f`, color: tierColor(im.tier) }}>
                  {Math.round(im.current)}
                </div>
                <div className="impact-body">
                  <div className="row" style={{ gap: 8 }}>
                    <div className="impact-title">{im.category_label}</div>
                    <Badge tone={im.tier === "critical" ? "red" : im.tier === "priority" ? "amber" : im.tier === "optimise" ? "blue" : "green"}>
                      {im.tier}
                    </Badge>
                  </div>
                  <div className="impact-lift">{im.lift}</div>
                </div>
              </div>
            ))
          )}
        </div>

        <div className="card">
          <div className="card-title">Verdict</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <div className="strong" style={{ fontSize: 20 }}>{rep.verdict?.label}</div>
            <p className="muted" style={{ margin: 0 }}>{rep.verdict?.description}</p>
            <div className="kv" style={{ marginTop: 12 }}>
              <div><span className="k">Profile score</span><div className="strong">{rep.score}/100</div></div>
              <div><span className="k">Assessment id</span><div className="mono">{rep.assessment_id}</div></div>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-title">SWOT analysis</div>
        <div className="swot-grid">
          <SwotBox title="Strengths" icon="💪" tone="strength" items={rep.swot?.strengths} />
          <SwotBox title="Weaknesses" icon="⚠️" tone="weakness" items={rep.swot?.weaknesses} />
          <SwotBox title="Opportunities" icon="🚀" tone="opportunity" items={rep.swot?.opportunities} />
          <SwotBox title="Threats" icon="🔥" tone="threat" items={rep.swot?.threats} />
        </div>
      </div>

      {auditFindings.length > 0 && (
        <div className="card">
          <div className="card-title">
            <span>AI agent findings <span className="badge blue">merged into SWOT</span></span>
          </div>
          <div style={{ display: "grid", gap: 8 }}>
            {auditFindings.map((f, i) => (
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

      {rep.detail?.length > 0 && (
        <div className="card">
          <div className="card-title">Answer detail</div>
          <table className="table">
            <thead><tr><th>Question</th><th>Answer</th><th style={{ textAlign: "right" }}>Points</th></tr></thead>
            <tbody>
              {rep.detail.map((d) => (
                <tr key={d.id}>
                  <td style={{ maxWidth: 360 }}>{d.question}</td>
                  <td className="muted">{d.answer}</td>
                  <td style={{ textAlign: "right" }} className="strong">{d.points}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
