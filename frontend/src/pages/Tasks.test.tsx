import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import Tasks from "./Tasks";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("Tasks", () => {
  it("merges open PRs and unresolved incidents, skipping resolved ones", async () => {
    const repo = { repo_id: "a", name: "A", open_pull_requests: [{ number: 1, title: "Fix it", url: "https://x", opened_at: "2026-10-01T00:00:00Z", stale: true }] };
    const open = { id: 1, app_id: "a", failure_type: "down", started_at: "2026-10-02T00:00:00Z", resolved_at: null, notes: null };
    vi.stubGlobal("fetch", vi.fn(async (url: string) =>
      new Response(JSON.stringify(url.includes("analytics") ? [repo] : [open, { ...open, id: 2, failure_type: "old", resolved_at: "2026-10-02T01:00:00Z" }])),
    ));
    render(<Tasks />);
    expect(await screen.findByText("Fix it")).toBeTruthy();
    expect(screen.getByText("down")).toBeTruthy();
    expect(screen.queryByText("old")).toBeNull();
    expect(screen.getByText("stale")).toBeTruthy();
  });
});
