import { Activity, Menu } from "iconoir-react";

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
        <div className="brand-mark"><Activity width={16} height={16} aria-hidden="true" /></div>
        <span>AISAAC</span>
      </div>
      <div className="app-topbar-right">
        <StatusDot tone={status.tone} label={status.label} />
        <ThemeToggle />
        <button type="button" className="app-topbar-menu-button" onClick={onOpenMenu} aria-label="Open navigation menu">
          <Menu width={20} height={20} aria-hidden="true" />
        </button>
      </div>
    </header>
  );
}
