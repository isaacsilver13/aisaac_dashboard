import { Activity, Menu } from "lucide-react";

import { StatusDot } from "../primitives/StatusDot";
import type { Tone } from "../primitives/tone";
import { ThemeToggle } from "./ThemeToggle";

interface SystemStatusSummary {
  label: string;
  tone: Tone;
}

interface MobileTopBarProps {
  status: SystemStatusSummary;
  onOpenMenu: () => void;
}

export function MobileTopBar({ status, onOpenMenu }: MobileTopBarProps) {
  return (
    <header className="app-topbar">
      <div className="app-sidebar-brand">
        <div className="brand-mark"><Activity size={16} strokeWidth={2.4} aria-hidden="true" /></div>
        <span>AISAAC</span>
      </div>
      <div className="app-topbar-right">
        <StatusDot tone={status.tone} label={status.label} />
        <ThemeToggle />
        <button type="button" className="app-topbar-menu-button" onClick={onOpenMenu} aria-label="Open navigation menu">
          <Menu size={20} aria-hidden="true" />
        </button>
      </div>
    </header>
  );
}
