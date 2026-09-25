import { NavLink } from "react-router-dom";
import { Activity } from "lucide-react";

import { StatusDot } from "../primitives/StatusDot";
import type { Tone } from "../primitives/tone";
import { NAV_ITEMS } from "./navItems";

interface SystemStatusSummary {
  label: string;
  tone: Tone;
}

interface SidebarProps {
  status: SystemStatusSummary;
  onNavigate?: () => void;
}

export function Sidebar({ status, onNavigate }: SidebarProps) {
  return (
    <aside className="app-sidebar" aria-label="Primary">
      <div className="app-sidebar-brand">
        <div className="brand-mark"><Activity size={18} strokeWidth={2.4} aria-hidden="true" /></div>
        <span>AISAAC</span>
      </div>
      <nav className="app-sidebar-nav">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            onClick={onNavigate}
            className={({ isActive }) => `app-sidebar-link${isActive ? " app-sidebar-link-active" : ""}`}
          >
            <item.icon size={17} strokeWidth={2.1} aria-hidden="true" />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="app-sidebar-status">
        <StatusDot tone={status.tone} label={status.label} />
        <span>{status.label}</span>
      </div>
    </aside>
  );
}
