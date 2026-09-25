import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { CheckResult, Incident } from "../../types";
import { ActivityFeed } from "./ActivityFeed";
import { AttentionPanel } from "./AttentionPanel";
import { SystemOverview } from "./SystemOverview";

function makeResult(overrides: Partial<CheckResult>): CheckResult {
  return {
    app_id: "svc",
    name: "Service",
    category: "app",
    description: "",
    product_url: null,
    state: "up",
    checked_at: "2026-09-25T12:00:00Z",
    response_ms: 100,
    http_status: 200,
    readiness: null,
    provider_state: null,
    freshness: null,
    page_state: null,
    metrics_state: null,
    metrics: {},
    detail: null,
    cached: false,
    ...overrides,
  };
}

describe("SystemOverview", () => {
  it("shows the operational ratio and per-state counts", () => {
    const results = [
      makeResult({ app_id: "a", state: "up" }),
      makeResult({ app_id: "b", state: "down" }),
    ];
    render(<SystemOverview results={results} loading={false} />);
    expect(screen.getByText("1/2")).toBeInTheDocument();
    expect(screen.getByText(/1 down/)).toBeInTheDocument();
  });

  it("shows a placeholder while loading", () => {
    render(<SystemOverview results={[]} loading />);
    expect(screen.getByText("--")).toBeInTheDocument();
  });
});

describe("AttentionPanel", () => {
  it("shows an all-nominal message when there are no open incidents", () => {
    render(<AttentionPanel openIncidents={[]} results={[]} />);
    expect(screen.getByText("All systems nominal")).toBeInTheDocument();
  });

  it("lists open incidents by the app's display name", () => {
    const incident: Incident = {
      id: 1,
      app_id: "svc",
      failure_type: "http_error",
      started_at: "2026-09-25T12:00:00Z",
      resolved_at: null,
      notes: null,
    };
    render(<AttentionPanel openIncidents={[incident]} results={[makeResult({ app_id: "svc", name: "Vinyl" })]} />);
    expect(screen.getByText("Vinyl")).toBeInTheDocument();
    expect(screen.getByText(/http_error/)).toBeInTheDocument();
  });
});

describe("ActivityFeed", () => {
  it("renders an empty state when there is no activity", () => {
    render(<ActivityFeed results={[]} />);
    expect(screen.getByText("No recent activity.")).toBeInTheDocument();
  });

  it("lists recent checks up to the limit", () => {
    const results = [makeResult({ app_id: "a", name: "A" }), makeResult({ app_id: "b", name: "B" })];
    render(<ActivityFeed results={results} limit={1} />);
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.queryByText("B")).not.toBeInTheDocument();
  });
});
