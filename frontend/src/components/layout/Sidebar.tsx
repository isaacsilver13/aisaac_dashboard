import { NavLink } from "react-router-dom";
import { Activity } from "iconoir-react";

import { StatusDot } from "../primitives/StatusDot";
import type { Tone } from "../primitives/tone";
import { NAV_ITEMS } from "./navItems";
import { ThemeToggle } from "./ThemeToggle";

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
        <div className="brand-mark"><Activity width={18} height={18} aria-hidden="true" /></div>
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
            <item.icon width={17} height={17} aria-hidden="true" />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="app-sidebar-status">
        <StatusDot tone={status.tone} label={status.label} />
        <span>{status.label}</span>
        <ThemeToggle />
      </div>
    </aside>
  );
}
