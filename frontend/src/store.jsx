import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "./api.js";

const AppCtx = createContext(null);

const ENTITY_KEY = "swotify_entity";

export function AppProvider({ children }) {
  const [entities, setEntities] = useState([]);
  const [currentId, setCurrentId] = useState(() => {
    try {
      return Number(localStorage.getItem(ENTITY_KEY)) || null;
    } catch {
      return null;
    }
  });
  const [toasts, setToasts] = useState([]);

  const toast = useCallback((msg, type = "success") => {
    const id = Math.random().toString(36).slice(2);
    setToasts((t) => [...t, { id, msg, type }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4200);
  }, []);

  const refreshEntities = useCallback(async () => {
    try {
      const list = await api.listEntities();
      setEntities(list);
      return list;
    } catch (err) {
      toast(err.message, "error");
      return [];
    }
  }, []);

  useEffect(() => {
    refreshEntities();
  }, [refreshEntities]);

  const currentEntity = entities.find((e) => e.id === currentId) || null;

  const selectEntity = useCallback((id) => {
    setCurrentId(id);
    try {
      if (id) localStorage.setItem(ENTITY_KEY, String(id));
      else localStorage.removeItem(ENTITY_KEY);
    } catch {
      /* ignore */
    }
  }, []);

  return (
    <AppCtx.Provider
      value={{ entities, currentEntity, currentId, selectEntity, refreshEntities, toast }}
    >
      {children}
      <div className="toast-wrap">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.type === "error" ? "error" : t.type === "warn" ? "warn" : ""}`}>
            {t.msg}
          </div>
        ))}
      </div>
    </AppCtx.Provider>
  );
}

export function useApp() {
  return useContext(AppCtx);
}
