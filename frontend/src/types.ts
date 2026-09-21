export type HealthState = "up" | "degraded" | "down" | "unavailable" | "stale";

export interface CheckResult {
  app_id: string;
  name: string;
  category: string;
  description: string;
  product_url: string | null;
  state: HealthState;
  checked_at: string;
  response_ms: number | null;
  http_status: number | null;
  readiness: HealthState | null;
  provider_state: string | null;
  freshness: string | null;
  page_state: HealthState | null;
  metrics_state: HealthState | null;
  metrics: Record<string, string | number | boolean>;
  detail: string | null;
  cached: boolean;
}

export interface DashboardResponse {
  profile: "local" | "production";
  refreshed_at: string;
  results: CheckResult[];
}

export interface Incident {
  id: number;
  app_id: string;
  failure_type: string;
  started_at: string;
  resolved_at: string | null;
  notes: string | null;
}

export type CiStatus = "success" | "failure" | "in_progress" | "unknown";

export interface PullRequestSummary {
  number: number;
  title: string;
  url: string;
  opened_at: string;
  stale: boolean;
}

export interface RepoActivity {
  repo_id: string;
  name: string;
  category: string;
  owner: string;
  repo: string;
  ci_status: CiStatus;
  open_issue_count: number | null;
  open_pr_count: number | null;
  open_pull_requests: PullRequestSummary[];
  commits_last_7d: number | null;
  last_commit_at: string | null;
  checked_at: string;
  cached: boolean;
  detail: string | null;
}

export interface AgentSummary {
  id: string;
  name: string;
  domain: string;
  description: string;
  scope: string[];
  last_run_at: string | null;
  last_run_note: string | null;
}

export interface CIEvent {
  id: number;
  app_id: string;
  repo: string;
  event_type: string;
  ci_status: CiStatus;
  details: string;
  received_at: string;
  notified: boolean;
}
