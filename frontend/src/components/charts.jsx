import React, { useMemo } from "react";

const W = 860;
const H = 240;
const PAD = { l: 42, r: 14, t: 16, b: 26 };

export function TimeseriesChart({ data, height = 240 }) {
  const h = height;
  const { lines, max, xLabels } = useMemo(() => {
    if (!data || data.length === 0) return { lines: [], max: 1, xLabels: [] };
    const iw = W - PAD.l - PAD.r;
    const ih = h - PAD.t - PAD.b;
    const n = data.length;
    const maxVal = Math.max(1, ...data.map((d) => Math.max(d.views, d.visitors || 0)));
    const x = (i) => PAD.l + (n === 1 ? iw / 2 : (i / (n - 1)) * iw);
    const y = (v) => PAD.t + ih - (v / maxVal) * ih;
    const path = (key) =>
      data.map((d, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(d[key] || 0).toFixed(1)}`).join(" ");
    const area = (key) =>
      `${path(key)} L${x(n - 1).toFixed(1)},${(PAD.t + ih).toFixed(1)} L${x(0).toFixed(1)},${(PAD.t + ih).toFixed(1)} Z`;
    const labels = [];
    const step = Math.max(1, Math.floor(n / 7));
    for (let i = 0; i < n; i += step) labels.push({ i, label: data[i].date.slice(5) });
    if (!labels.length || labels[labels.length - 1].i !== n - 1)
      labels.push({ i: n - 1, label: data[n - 1].date.slice(5) });
    return {
      lines: [
        { key: "views", path: path("views"), area: area("views"), color: "#1ed760", name: "Views" },
        { key: "visitors", path: path("visitors"), area: area("visitors"), color: "#58a6ff", name: "Visitors" },
      ],
      max: maxVal,
      xLabels: labels,
    };
  }, [data, h]);

  const yTicks = useMemo(() => {
    const ticks = [];
    const n = 4;
    for (let i = 0; i <= n; i++) {
      const v = (max / n) * i;
      const ih = h - PAD.t - PAD.b;
      ticks.push({ v: Math.round(v), y: PAD.t + ih - (v / max) * ih });
    }
    return ticks;
  }, [max, h]);

  if (!data || data.length === 0)
    return <div className="swot-empty" style={{ padding: "40px 0", textAlign: "center" }}>No visits in this range.</div>;

  return (
    <svg viewBox={`0 0 ${W} ${h}`} style={{ width: "100%", height: "auto" }} role="img">
      {yTicks.map((t, i) => (
        <g key={i}>
          <line x1={PAD.l} x2={W - PAD.r} y1={t.y} y2={t.y} stroke="rgba(148,178,208,0.09)" />
          <text x={PAD.l - 8} y={t.y + 4} textAnchor="end" fontSize="10.5" fill="#5c6b7a">
            {t.v >= 1000 ? `${(t.v / 1000).toFixed(t.v >= 10000 ? 0 : 1)}k` : t.v}
          </text>
        </g>
      ))}
      <defs>
        <linearGradient id="g-views" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#1ed760" stopOpacity="0.35" />
          <stop offset="100%" stopColor="#1ed760" stopOpacity="0" />
        </linearGradient>
        <linearGradient id="g-visitors" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#58a6ff" stopOpacity="0.28" />
          <stop offset="100%" stopColor="#58a6ff" stopOpacity="0" />
        </linearGradient>
      </defs>
      {lines.map((ln) => (
        <path key={ln.key} d={ln.area} fill={ln.key === "views" ? "url(#g-views)" : "url(#g-visitors)"} />
      ))}
      {lines.map((ln) => (
        <path key={ln.key} d={ln.path} fill="none" stroke={ln.color} strokeWidth="2.2" strokeLinejoin="round" strokeLinecap="round" />
      ))}
      {xLabels.map(({ i, label }) => (
        <text key={i} x={PAD.l + (data.length === 1 ? (W - PAD.l - PAD.r) / 2 : (i / (data.length - 1)) * (W - PAD.l - PAD.r))}
          y={h - 7} textAnchor="middle" fontSize="10.5" fill="#5c6b7a">
          {label}
        </text>
      ))}
    </svg>
  );
}

export function HourlyChart({ hours, values, height = 200 }) {
  const max = Math.max(1, ...values);
  const barW = (W - PAD.l - PAD.r) / 24;
  return (
    <svg viewBox={`0 0 ${W} ${height}`} style={{ width: "100%", height: "auto" }} role="img">
      {[0, 0.5, 1].map((f) => (
        <line key={f} x1={PAD.l} x2={W - PAD.r} y1={PAD.t + (height - PAD.t - PAD.b) * f}
          y2={PAD.t + (height - PAD.t - PAD.b) * f} stroke="rgba(148,178,208,0.09)" />
      ))}
      {values.map((v, i) => {
        const bw = Math.min(barW * 0.62, 26);
        const x = PAD.l + i * barW + (barW - bw) / 2;
        const bh = (v / max) * (height - PAD.t - PAD.b);
        const y = PAD.t + (height - PAD.t - PAD.b) - bh;
        return (
          <g key={hours[i]}>
            <rect x={x} y={y} width={bw} height={Math.max(bh, v > 0 ? 2 : 0)} rx="3" fill={v > 0 ? "#1ed760" : "rgba(255,255,255,0.06)"}
              opacity={v > 0 ? 0.85 : 1} />
            {i % 4 === 0 && (
              <text x={PAD.l + i * barW + barW / 2} y={height - 7} textAnchor="middle" fontSize="10" fill="#5c6b7a">
                {hours[i]}
              </text>
            )}
          </g>
        );
      })}
      <text x={W - PAD.r} y={height - 7} textAnchor="end" fontSize="10" fill="#5c6b7a">24h</text>
    </svg>
  );
}
