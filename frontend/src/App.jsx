import React from "react";
import { Routes, Route } from "react-router-dom";
import { AppProvider } from "./store.jsx";
import Layout from "./components/Layout.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Analytics from "./pages/Analytics.jsx";
import Assessment from "./pages/Assessment.jsx";
import Report from "./pages/Report.jsx";
import Agent from "./pages/Agent.jsx";

export default function App() {
  return (
    <AppProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="entities/:id/analytics" element={<Analytics />} />
          <Route path="entities/:id/assessment" element={<Assessment />} />
          <Route path="entities/:id/report" element={<Report />} />
          <Route path="entities/:id/agent" element={<Agent />} />
          <Route path="*" element={<Dashboard />} />
        </Route>
      </Routes>
    </AppProvider>
  );
}
