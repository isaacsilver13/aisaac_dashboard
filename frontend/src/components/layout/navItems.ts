import { Activity, Bot, ListChecks, Radio, BarChart3, type LucideIcon } from "lucide-react";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  /** Matches react-router's `end` prop — true only for the index route. */
  end?: boolean;
}

export const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Command Center", icon: Activity, end: true },
  { to: "/agents", label: "Agents", icon: Bot },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/tasks", label: "Tasks", icon: ListChecks },
  { to: "/coms", label: "Coms", icon: Radio },
];
