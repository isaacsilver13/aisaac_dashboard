import { useState, type ReactNode } from "react";

import { fetchDashboard } from "../../api";
import { useAsyncData } from "../../hooks/useAsyncData";
import type { Tone } from "../primitives/tone";
import { MobileDrawer } from "./MobileDrawer";
import { MobileTopBar } from "./MobileTopBar";
import { Sidebar } from "./Sidebar";

interface AppShellProps {
  children: ReactNode;
}

function summarizeSystemStatus(
  loading: boolean,
  error: string | null,
  results: { state: string }[] | undefined,
): { label: string; tone: Tone } {
  if (error) return { label: "Unable to reach services", tone: "error" };
  if (loading || !results) return { label: "Checking systems…", tone: "neutral" };

  const total = results.length;
  const down = results.filter((result) => result.state === "down").length;
  const degraded = results.filter((result) => result.state === "degraded").length;
  const operational = total - down - degraded;

  if (down > 0) return { label: `${operational}/${total} operational`, tone: "error" };
  if (degraded > 0) return { label: `${operational}/${total} operational`, tone: "warning" };
  return { label: total > 0 ? `${operational}/${total} operational` : "No systems configured", tone: "success" };
}

export function AppShell({ children }: AppShellProps) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { data, loading, error } = useAsyncData(fetchDashboard);
  const status = summarizeSystemStatus(loading, error, data?.results);

  return (
    <div className="app-shell">
      <Sidebar status={status} />
      <MobileTopBar status={status} onOpenMenu={() => setDrawerOpen(true)} />
      <MobileDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />
      <main className="app-main">{children}</main>
    </div>
  );
}
