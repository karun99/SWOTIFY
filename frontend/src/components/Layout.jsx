import React, { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useApp } from "../store.jsx";
import { api, fmtNumber } from "../api.js";

const NAV = [
  { to: "/", label: "Dashboard", icon: "▦" },
  { to: "analytics", label: "Analytics", icon: "📈" },
  { to: "assessment", label: "Assessment", icon: "📝" },
  { to: "report", label: "Report", icon: "🧭" },
  { to: "agent", label: "AI Audit", icon: "🤖" },
];

const ICO_SIZE = 17;

export default function Layout() {
  const { entities, currentEntity, currentId, selectEntity } = useApp();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    function onDoc(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const base = currentId ? `/entities/${currentId}` : "";

  function pick(e) {
    selectEntity(e.id);
    setOpen(false);
    navigate(`/entities/${e.id}/analytics`);
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-logo">S</div>
          <div>
            <div className="brand-name">Swotify</div>
            <div className="brand-sub">by GuidingKey</div>
          </div>
        </div>

        <div className="nav-label">Workspace</div>
        <NavLink to="/" end className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
          <span className="ico" style={{ fontSize: ICO_SIZE }}>▦</span> Dashboard
        </NavLink>

        {currentId && (
          <>
            <div className="nav-label">Entity</div>
            {NAV.slice(1).map((n) => (
              <NavLink
                key={n.label}
                to={`${base}${n.to === "analytics" ? "/analytics" : `/${n.to}`}`}
                className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
              >
                <span className="ico" style={{ fontSize: ICO_SIZE }}>{n.icon}</span> {n.label}
              </NavLink>
            ))}
          </>
        )}
      </aside>

      <main className="main">
        <div className="topbar">
          <div className="entity-switch" ref={menuRef}>
            <button className="trigger" onClick={() => setOpen((o) => !o)}>
              <span>{currentEntity ? currentEntity.name : "Select a site"}</span>
              <span className="muted">▾</span>
            </button>
            {open && (
              <div className="menu">
                <div className="menu-head">Sites tracked</div>
                {entities.length === 0 && (
                  <div className="menu-item muted" onClick={() => { setOpen(false); navigate("/"); }}>
                    No sites yet — create one
                  </div>
                )}
                {entities.map((e) => (
                  <div className="menu-item" key={e.id} onClick={() => pick(e)}>
                    <div className="row">
                      <div className="nm">{e.name}</div>
                      <div className="badge">{fmtNumber(e.total_visits || 0)} visits</div>
                    </div>
                    <div className="ws">{e.website || "no website"}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
          <div className="grow" />
          <button className="btn btn-ghost btn-sm" onClick={() => navigate("/")}>+ New site</button>
        </div>
        <Outlet />
      </main>
    </div>
  );
}
