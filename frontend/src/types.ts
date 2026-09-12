export type HealthState = "up" | "degraded" | "down" | "unavailable";

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
