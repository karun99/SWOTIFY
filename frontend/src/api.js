// Swotify API client — thin wrapper around the FastAPI backend.

const BASE = ""; // same origin (dev: vite proxy / prod: served by FastAPI)

async function request(method, path, body) {
  const opts = { method, headers: {} };
  if (body instanceof FormData) {
    opts.body = body;
  } else if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(`${BASE}${path}`, opts);
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      if (typeof data === "string") detail = data;
      else if (data && data.detail) detail = data.detail;
    } catch {
      /* non-json error body */
    }
    throw new Error(detail);
  }
  const ct = res.headers.get("content-type") || "";
  if (res.status === 204) return null;
  return ct.includes("application/json") ? res.json() : res.text();
}

export const api = {
  health: () => request("GET", "/api/health"),

  // Entities
  createEntity: (name, website) =>
    request("POST", "/api/entities", { name, website }),
  listEntities: () => request("GET", "/api/entities"),
  getEntity: (id) => request("GET", `/api/entities/${id}`),

  // Analytics
  analytics: (id, days = 30) =>
    request("GET", `/api/entities/${id}/analytics?days=${days}`),
  analyticsLive: (id) => request("GET", `/api/entities/${id}/analytics/live`),

  // Assessment
  questions: () => request("GET", "/api/questions"),
  submitAssessment: (id, responses) =>
    request("POST", `/api/entities/${id}/assessments`, { responses }),
  report: (id) => request("GET", `/api/entities/${id}/report`),

  // AI agent
  reachStatus: (id) => request("GET", `/api/entities/${id}/agent/reach`),
  runAudit: (id) => request("POST", `/api/entities/${id}/agent/audit`),

  // Documents
  uploadDocument: (id, file) => {
    const fd = new FormData();
    fd.append("file", file);
    return request("POST", `/api/entities/${id}/documents`, fd);
  },
  listDocuments: (id) => request("GET", `/api/entities/${id}/documents`),
  deleteDocument: (id, docId) =>
    request("DELETE", `/api/entities/${id}/documents/${docId}`),
};

export function fmtNumber(n) {
  if (n === null || n === undefined) return "0";
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1).replace(/\.0$/, "") + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1).replace(/\.0$/, "") + "k";
  return String(n);
}

export function fmtDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function fmtTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

export function fmtDuration(s) {
  if (!s || s <= 0) return "0s";
  if (s < 60) return `${Math.round(s)}s`;
  const m = Math.floor(s / 60);
  const sec = Math.round(s % 60);
  return `${m}m ${sec}s`;
}

export function tierColor(tier) {
  switch (tier) {
    case "maintain": return "#1ed760";
    case "optimise": return "#9be15d";
    case "priority": return "#ffb020";
    case "critical": return "#ff5c5c";
    default: return "#8b98a5";
  }
}

export function scoreColor(score) {
  if (score === null || score === undefined) return "#8b98a5";
  if (score >= 85) return "#1ed760";
  if (score >= 65) return "#9be15d";
  if (score >= 45) return "#ffb020";
  return "#ff5c5c";
}
