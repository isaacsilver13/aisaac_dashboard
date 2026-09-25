import { Route, Routes } from "react-router-dom";

import { AppShell } from "./components/layout/AppShell";
import Agents from "./pages/Agents";
import Analytics from "./pages/Analytics";
import CommandCenter from "./pages/CommandCenter";
import Coms from "./pages/Coms";
import Tasks from "./pages/Tasks";

export default function App() {
  return (
    <AppShell>
      <div className="ambient-grid" aria-hidden="true" />
      <Routes>
        <Route path="/" element={<CommandCenter />} />
        <Route path="/agents" element={<Agents />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/tasks" element={<Tasks />} />
        <Route path="/coms" element={<Coms />} />
      </Routes>
      <footer className="footer-note">
        <span>Server-side checks / no private data</span>
        <span>AIsaac Dashboard v0.1</span>
      </footer>
    </AppShell>
  );
}
