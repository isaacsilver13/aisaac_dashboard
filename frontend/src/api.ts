import type { DashboardResponse } from "./types";

export async function fetchDashboard(forceRefresh = false): Promise<DashboardResponse> {
  const query = forceRefresh ? "?force_refresh=true" : "";
  const response = await fetch(`/api/v1/dashboard${query}`, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Dashboard request failed with HTTP ${response.status}.`);
  }
  return (await response.json()) as DashboardResponse;
}
