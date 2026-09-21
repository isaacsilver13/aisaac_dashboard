import type { AgentSummary, DashboardResponse, Incident, RepoActivity } from "./types";

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

export async function fetchIncidents(): Promise<Incident[]> {
  const response = await fetch("/api/v1/incidents", { headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new Error(`Incidents request failed with HTTP ${response.status}.`);
  }
  return (await response.json()) as Incident[];
}

export async function resolveIncident(incidentId: number, notes?: string): Promise<void> {
  const response = await fetch(`/api/v1/incidents/${incidentId}/resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ notes: notes ?? null }),
  });
  if (!response.ok) {
    throw new Error(`Resolve incident failed with HTTP ${response.status}.`);
  }
}

export async function fetchAgents(): Promise<AgentSummary[]> {
  const response = await fetch("/api/v1/agents", { headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new Error(`Agents request failed with HTTP ${response.status}.`);
  }
  return (await response.json()) as AgentSummary[];
}

export async function fetchAnalytics(forceRefresh = false): Promise<RepoActivity[]> {
  const query = forceRefresh ? "?force_refresh=true" : "";
  const response = await fetch(`/api/v1/analytics${query}`, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Analytics request failed with HTTP ${response.status}.`);
  }
  return (await response.json()) as RepoActivity[];
}

export async function fetchRunbook(appId: string): Promise<string | null> {
  const response = await fetch(`/api/v1/runbooks/${appId}`);
  if (response.status === 404) return null;
  if (!response.ok) {
    throw new Error(`Runbook request failed with HTTP ${response.status}.`);
  }
  return response.text();
}
