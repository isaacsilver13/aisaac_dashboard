import type { ComponentType, SVGProps } from "react";
import { AppWindow, Book, Brain, Dashboard, Github, Settings, TaskList, Timer } from "iconoir-react";

export interface NavItem {
  to: string;
  label: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  /** Matches react-router's `end` prop — true only for the index route. */
  end?: boolean;
  /** Renders the monitored applications as a collapsible sub-list in the sidebar. */
  hasApps?: boolean;
}

export const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Overview", icon: Dashboard, end: true },
  { to: "/applications", label: "Applications", icon: AppWindow, hasApps: true },
  { to: "/github", label: "GitHub", icon: Github },
  { to: "/tasks", label: "Tasks", icon: TaskList },
  { to: "/news", label: "News", icon: Book },
  { to: "/automations", label: "Automations", icon: Timer },
  { to: "/knowledge", label: "Knowledge", icon: Brain },
  { to: "/settings", label: "Settings", icon: Settings },
];
