import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { OverviewTab } from "./OverviewTab";

const result = {
  app_id: "a", name: "A", category: "Cat", description: "Does things", product_url: "https://a.example",
  state: "up", checked_at: "2026-10-03T00:00:00Z", response_ms: 120, http_status: 200, readiness: "up",
  provider_state: null, freshness: null, page_state: null, metrics_state: null, metrics: { games: 3 }, detail: null, cached: false,
};
const repo = { repo_id: "a", ci_status: "success", open_pr_count: 2, open_issue_count: 0, commits_last_7d: 5, last_commit_at: null };

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("OverviewTab", () => {
  it("renders the app's signals, repo and metrics from the shared endpoints", async () => {
    vi.stubGlobal("fetch", vi.fn(async (url: string) =>
      new Response(JSON.stringify(
        url.includes("dashboard") ? { results: [result] } : url.includes("analytics") ? [repo] : [],
      )),
    ));
    render(<OverviewTab appId="a" />);
    expect(await screen.findByText("Does things")).toBeTruthy();
    expect(screen.getByText("120 ms")).toBeTruthy();
    expect(await screen.findByText("Passing")).toBeTruthy();
    expect(screen.getByText("games")).toBeTruthy();
    expect(screen.getByText("3")).toBeTruthy();
  });

  it("says so when the app reports no metrics", async () => {
    vi.stubGlobal("fetch", vi.fn(async (url: string) =>
      new Response(JSON.stringify(url.includes("dashboard") ? { results: [{ ...result, metrics: {} }] } : [])),
    ));
    render(<OverviewTab appId="a" />);
    expect(await screen.findByText("This app reports no metrics.")).toBeTruthy();
  });

  it("shows an empty state for an unregistered app", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ results: [] }))));
    render(<OverviewTab appId="zzz" />);
    expect(await screen.findByText("This application is not registered.")).toBeTruthy();
  });
});
