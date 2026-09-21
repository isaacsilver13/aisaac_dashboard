import { Activity } from "lucide-react";
import { Route, Routes } from "react-router-dom";

import { TabNav } from "./components/TabNav";
import Agents from "./pages/Agents";
import Analytics from "./pages/Analytics";
import CommandCenter from "./pages/CommandCenter";
import Tasks from "./pages/Tasks";

const TABS = [
  { to: "/", label: "Command Center" },
  { to: "/agents", label: "Agents" },
  { to: "/analytics", label: "Analytics" },
  { to: "/tasks", label: "Tasks" },
];

export default function App() {
  return (
    <main className="shell">
      <div className="ambient-grid" aria-hidden="true" />
      <header className="masthead">
        <div className="brand-lockup">
          <div className="brand-mark"><Activity size={20} strokeWidth={2.4} /></div>
          <div>
            <p className="eyebrow">Personal systems</p>
            <h1>AIsaac Dashboard</h1>
          </div>
        </div>
      </header>

      <TabNav tabs={TABS} />

      <Routes>
        <Route path="/" element={<CommandCenter />} />
        <Route path="/agents" element={<Agents />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/tasks" element={<Tasks />} />
      </Routes>

      <footer className="footer-note">
        <span>Server-side checks / no private data</span>
        <span>AIsaac Dashboard v0.1</span>
      </footer>
    </main>
  );
}
