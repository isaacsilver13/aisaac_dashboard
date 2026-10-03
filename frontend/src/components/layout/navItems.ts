import type { ComponentType, SVGProps } from "react";
import { Activity, Spark, TaskList, Antenna, StatsReport, Book } from "iconoir-react";

export interface NavItem {
  to: string;
  label: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  /** Matches react-router's `end` prop — true only for the index route. */
  end?: boolean;
}

export const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Command Center", icon: Activity, end: true },
  { to: "/agents", label: "Agents", icon: Spark },
  { to: "/analytics", label: "Analytics", icon: StatsReport },
  { to: "/tasks", label: "Tasks", icon: TaskList },
  { to: "/coms", label: "Coms", icon: Antenna },
  { to: "/second-brain", label: "Second Brain", icon: Book },
];
