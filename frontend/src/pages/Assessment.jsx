import React, { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api.js";
import { Loading } from "../components/ui.jsx";
import { useApp } from "../store.jsx";

export default function Assessment() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useApp();
  const entityId = Number(id);
  const [cats, setCats] = useState([]);
  const [questions, setQuestions] = useState([]);
  const [responses, setResponses] = useState({});
  const [idx, setIdx] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.questions().then((d) => {
      setCats(d.categories || []);
      setQuestions(d.questions || []);
    }).catch((e) => setError(e.message));
  }, []);

  const flat = questions;
  const q = flat[idx];

  const answeredCount = useMemo(
    () => flat.filter((x) => responses[x.id] !== undefined).length,
    [flat, responses]
  );

  function answer(label) {
    setResponses((r) => ({ ...r, [q.id]: label }));
    if (idx < flat.length - 1) setIdx(idx + 1);
  }

  function back() {
    if (idx > 0) setIdx(idx - 1);
  }

  async function submit() {
    if (answeredCount < flat.length) return;
    setSubmitting(true);
    try {
      await api.submitAssessment(entityId, responses);
      toast("Report generated");
      navigate(`/entities/${entityId}/report`);
    } catch (err) {
      toast(err.message, "error");
      setSubmitting(false);
    }
  }

  if (error) return <div className="card muted">{error}</div>;
  if (!q) return <Loading text="Loading questionnaire…" />;

  const catLabel = cats.find((c) => c.key === q.category)?.label || q.category;

  return (
    <div style={{ maxWidth: 720, margin: "0 auto" }}>
      <div className="topbar">
        <div>
          <h1>Digital Profile Assessment</h1>
          <div className="sub">Answer honestly — the report adapts to your answers.</div>
        </div>
        <div className="badge">{answeredCount}/{flat.length} answered</div>
      </div>

      <div className="bar-track" style={{ height: 8, marginBottom: 22 }}>
        <div className="bar-fill" style={{ width: `${(answeredCount / flat.length) * 100}%` }} />
      </div>

      <div className="card">
        <div className="spread wrap" style={{ marginBottom: 6 }}>
          <span className="badge blue">{catLabel}</span>
          <span className="muted-2" style={{ fontSize: 12 }}>Question {idx + 1} of {flat.length}</span>
        </div>
        <h2 style={{ fontSize: 19, margin: "8px 0 18px", lineHeight: 1.35 }}>{q.text}</h2>

        <div>
          {q.options.map((o) => (
            <label
              key={o.label}
              className={`option ${responses[q.id] === o.label ? "selected" : ""}`}
              onClick={() => answer(o.label)}
            >
              <div className="opt-label">
                <span className="radio" /> {o.label}
              </div>
              <div className="opt-note">{o.note}</div>
            </label>
          ))}
        </div>
      </div>

      <div className="spread" style={{ marginTop: 16 }}>
        <button className="btn btn-ghost" onClick={back} disabled={idx === 0}>← Back</button>
        {idx === flat.length - 1 && (
          <button className="btn btn-primary" onClick={submit} disabled={submitting || answeredCount < flat.length}>
            {submitting ? "Generating report…" : "Generate report"}
          </button>
        )}
      </div>
    </div>
  );
}
