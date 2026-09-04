import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useApp } from "../store.jsx";
import { api, fmtNumber, scoreColor } from "../api.js";
import { Badge, Empty } from "../components/ui.jsx";

export default function Dashboard() {
  const { entities, currentId, selectEntity, refreshEntities, toast } = useApp();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [website, setWebsite] = useState("");
  const [busy, setBusy] = useState(false);

  async function create(e) {
    e.preventDefault();
    if (!name.trim()) return toast("Enter a site name first", "warn");
    setBusy(true);
    try {
      const ent = await api.createEntity(name.trim(), website.trim());
      setName("");
      setWebsite("");
      toast(`Site "${ent.name}" created`);
      selectEntity(ent.id);
      navigate(`/entities/${ent.id}/analytics`);
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setBusy(false);
    }
  }

  function open(id) {
    selectEntity(id);
    navigate(`/entities/${id}/analytics`);
  }

  return (
    <div>
      <div className="topbar" style={{ marginBottom: 4 }}>
        <div>
          <h1>Dashboard</h1>
          <div className="sub">Add a site, then track its visitors and profile.</div>
        </div>
      </div>

      <div className="grid grid-2" style={{ alignItems: "start" }}>
        <div className="card">
          <div className="card-title">Track a new site</div>
          <form onSubmit={create}>
            <div className="field">
              <label>Site / business name</label>
              <input type="text" value={name} onChange={(e) => setName(e.target.value)}
                placeholder="e.g. GuidingKey Cafe" autoFocus />
            </div>
            <div className="field">
              <label>Website URL (optional)</label>
              <input type="text" value={website} onChange={(e) => setWebsite(e.target.value)}
                placeholder="e.g. guidingkey.com" />
            </div>
            <div className="field">
              <button className="btn btn-primary" type="submit" disabled={busy || !name.trim()}>
                {busy ? "Creating…" : "Create site"}
              </button>
            </div>
          </form>
          <div className="card-title" style={{ marginTop: 22 }}>
            Embed beacon
          </div>
          <p className="muted" style={{ margin: "0 0 8px", fontSize: 12.5 }}>
            Add this snippet to the site you track. A tracking id is generated automatically.
          </p>
          <code className="step-tool" style={{ display: "block" }}>
            {"<script src=\"YOUR-HOST/tracker/tracker.js\" data-tid=\"THE-TRACKING-ID\"><\/script>"}
          </code>
        </div>

        <div className="card">
          <div className="card-title">Your sites</div>
          {entities.length === 0 ? (
            <Empty title="No sites yet" hint="🚀">
              Create your first site on the left to start collecting analytics.
            </Empty>
          ) : (
            <div style={{ display: "grid", gap: 10 }}>
              {entities.map((e) => (
                <div key={e.id} className="option" onClick={() => open(e.id)} style={{ cursor: "pointer" }}>
                  <div className="spread wrap">
                    <div className="opt-label">
                      <span className="radio" /> {e.name}
                    </div>
                    <div className="row">
                      {e.live_now > 0 && <Badge tone="green"><span className="live-dot" style={{ margin: 0 }} />{e.live_now} live</Badge>}
                      {e.last_score !== null && (
                        <Badge tone="green" >Score {e.last_score}</Badge>
                      )}
                      {!e.has_report && <Badge>No report</Badge>}
                    </div>
                  </div>
                  <div className="muted" style={{ marginTop: 8, display: "grid", gap: 2 }}>
                    <div>{e.website || "No website configured"}</div>
                    <div className="mono muted-2" style={{ fontSize: 11 }}>
                      tracking: {e.tracking_id} · {fmtNumber(e.total_visits)} visits
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
