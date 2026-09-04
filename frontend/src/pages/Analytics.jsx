import React, { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { api, fmtDuration, fmtTime } from "../api.js";
import { BarList, Loading, StatCard } from "../components/ui.jsx";
import { HourlyChart, TimeseriesChart } from "../components/charts.jsx";

const RANGES = [7, 14, 30, 90];

export default function Analytics() {
  const { id } = useParams();
  const entityId = Number(id);
  const [days, setDays] = useState(30);
  const [data, setData] = useState(null);
  const [live, setLive] = useState({ live_now: 0, views_today: 0, live: [] });
  const [error, setError] = useState("");
  const timer = useRef(null);

  const load = useCallback(async () => {
    try {
      setData(await api.analytics(entityId, days));
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }, [entityId, days]);

  const loadLive = useCallback(async () => {
    try {
      setLive(await api.analyticsLive(entityId));
    } catch {
      /* silent */
    }
  }, [entityId]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    loadLive();
    timer.current = setInterval(loadLive, 15000);
    return () => clearInterval(timer.current);
  }, [loadLive]);

  if (error) return <div className="card muted">Failed to load analytics: {error}</div>;
  if (!data) return <Loading text="Loading analytics…" />;

  const t = data.totals || {};
  const hourlyLabels = (data.hourly || {}).hour || [];

  return (
    <div>
      <div className="topbar">
        <div>
          <h1>Analytics <span className="muted" style={{ fontWeight: 600, fontSize: 16 }}>· {data.entity?.name}</span></h1>
          <div className="sub">Last {days} days · Google-Search-Console style</div>
        </div>
        <div className="topbar-actions">
          <div className="seg">
            {RANGES.map((r) => (
              <button key={r} className={days === r ? "active" : ""} onClick={() => setDays(r)}>{r}d</button>
            ))}
          </div>
          <button className="btn btn-ghost btn-sm" onClick={load}>↻ Refresh</button>
        </div>
      </div>

      <div className="grid grid-4">
        <StatCard label="Views" value={fmtNum(t.views)} hint="in selected range" accent="#1ed760" />
        <StatCard label="Visitors" value={fmtNum(t.visitors)} hint="unique visitor ids" accent="#58a6ff" />
        <StatCard label="Avg. time" value={fmtDuration(t.avg_time_s)} hint="per visit" />
        <StatCard label="Bounce rate" value={t.bounce_rate != null ? `${t.bounce_rate}%` : "—"} hint="visits under 5s" accent={t.bounce_rate > 60 ? "#ff5c5c" : undefined} />
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <div className="card-title">
          <span>Visits over time</span>
          <span className="badge green"><span className="live-dot" style={{ margin: 0 }} />{live.live_now} live · {fmtNum(live.views_today)} today</span>
        </div>
        <TimeseriesChart data={data.timeseries} />
        <div className="row muted-2" style={{ fontSize: 12, gap: 18, marginTop: 8 }}>
          <span><span style={{ color: "#1ed760" }}>●</span> Views</span>
          <span><span style={{ color: "#58a6ff" }}>●</span> Visitors</span>
        </div>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <div className="card-title">Traffic by hour (today)</div>
          <HourlyChart hours={hourlyLabels} values={data.hourly?.views || []} />
        </div>
        <div className="card">
          <div className="card-title">Top pages</div>
          {data.top_pages.length === 0 ? (
            <div className="swot-empty">No page views yet.</div>
          ) : (
            <table className="table">
              <thead><tr><th>Page</th><th style={{ textAlign: "right" }}>Views</th><th style={{ textAlign: "right" }}>Avg time</th></tr></thead>
              <tbody>
                {data.top_pages.map((p) => (
                  <tr key={p.path}>
                    <td className="mono" style={{ maxWidth: 300, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{p.path}</td>
                    <td style={{ textAlign: "right" }} className="strong">{fmtNum(p.views)}</td>
                    <td style={{ textAlign: "right" }} className="muted">{fmtDuration(p.avg_time_s)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <div className="card-title">Referrers</div>
          <BarList items={data.referrers.map(([label, value]) => ({ label, value }))} color="#58a6ff" />
        </div>
        <div className="card">
          <div className="card-title">Devices</div>
          <BarList items={data.devices.map(([label, value]) => ({ label, value }))} color="#1ed760" />
        </div>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <div className="card-title">Browsers</div>
          <BarList items={data.browsers.map(([label, value]) => ({ label, value }))} color="#9be15d" />
        </div>
        <div className="card">
          <div className="card-title">Live visitors <span className="live-dot" /></div>
          {live.live.length === 0 ? (
            <div className="swot-empty">Nobody here right now. Embed the tracker and open your site!</div>
          ) : (
            <div style={{ display: "grid", gap: 8 }}>
              {live.live.map((v, i) => (
                <div key={i} className="row spread">
                  <div className="mono" style={{ maxWidth: 240, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{v.path}</div>
                  <div className="row" style={{ gap: 6 }}>
                    <span className="badge">{v.device}</span>
                    <span className="muted-2" style={{ fontSize: 12 }}>{fmtTime(v.ts)}</span>
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

function fmtNum(n) {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + "M";
  if (n >= 1000) return (n / 1000).toFixed(1) + "k";
  return n ?? 0;
}
