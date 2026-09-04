import React from "react";
import { fmtNumber, scoreColor } from "../api.js";

export function ScoreRing({ score, size = 158, label = "Digital Score" }) {
  const stroke = 10;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const val = score ?? 0;
  const pct = Math.max(0, Math.min(100, val));
  const color = scoreColor(val);
  return (
    <div className="ring-wrap" style={{ width: size, height: size }}>
      <svg width={size} height={size}>
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth={stroke}
        />
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke={color} strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${(pct / 100) * c} ${c}`}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ transition: "stroke-dasharray 0.8s cubic-bezier(0.2,0.8,0.2,1)" }}
        />
      </svg>
      <div className="ring-center">
        <div className="num" style={{ color }}>{fmtNumber(val)}</div>
        <div className="lbl">{label}</div>
      </div>
    </div>
  );
}

export function StatCard({ label, value, hint, accent }) {
  return (
    <div className="stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value" style={accent ? { color: accent } : undefined}>
        {value}
      </div>
      {hint ? <div className="stat-hint">{hint}</div> : null}
    </div>
  );
}

export function BarList({ items, color = "#1ed760", valueFmt }) {
  const max = Math.max(1, ...items.map((i) => (typeof i === "number" ? i : i.value)));
  const fmt = valueFmt || fmtNumber;
  return (
    <div>
      {items.map((it, idx) => {
        const label = typeof it === "number" ? idx : it.label;
        const value = typeof it === "number" ? it : it.value;
        const pct = (value / max) * 100;
        return (
          <div className="bar-row" key={label}>
            <div className="bar-label" title={label}>{label}</div>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${pct}%`, background: color }} />
            </div>
            <div className="bar-value">{fmt(value)}</div>
          </div>
        );
      })}
      {items.length === 0 && <div className="swot-empty">No data yet.</div>}
    </div>
  );
}

export function CategoryBars({ categories, scores }) {
  return (
    <div>
      {categories.map((c) => {
        const s = scores?.[c.key] ?? 0;
        return (
          <div className="bar-row" key={c.key}>
            <div className="bar-label" title={c.label}>{c.label}</div>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${s}%`, background: scoreColor(s) }} />
            </div>
            <div className="bar-value">{Math.round(s)}</div>
          </div>
        );
      })}
    </div>
  );
}

export function SwotBox({ title, icon, tone, items }) {
  return (
    <div className={`swot-box swot-${tone}`}>
      <div className="swot-title">
        <span>{icon}</span> {title}
      </div>
      {items && items.length > 0 ? (
        <ul>
          {items.map((it, i) => (
            <li key={i}>{it}</li>
          ))}
        </ul>
      ) : (
        <div className="swot-empty">Nothing flagged — keep it up.</div>
      )}
    </div>
  );
}

export function Badge({ children, tone }) {
  return <span className={`badge ${tone || ""}`}>{children}</span>;
}

export function Loading({ text = "Loading…" }) {
  return (
    <div className="loading">
      <span className="spinner" /> {text}
    </div>
  );
}

export function Empty({ title, hint, children }) {
  return (
    <div className="empty-state">
      <div className="big">{hint || "📊"}</div>
      <div className="strong">{title}</div>
      {children && <div className="muted" style={{ marginTop: 6 }}>{children}</div>}
    </div>
  );
}
