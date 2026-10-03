import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LogsTab } from "./LogsTab";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.localStorage.clear();
});

describe("LogsTab", () => {
  it("asks for a token when none is stored", () => {
    render(<LogsTab appId="a" />);
    expect(screen.getByText(/dashboard token/)).toBeTruthy();
  });

  it("shows newest lines first", async () => {
    window.localStorage.setItem("aisaac.dashboardToken", "t");
    const line = (message: string, timestamp: string) => ({ timestamp, level: "info", message, instance: "i", region: "ewr" });
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
      app_id: "a", fly_app: "a-fly", lines: [line("old", "2026-10-03T00:00:00Z"), line("new", "2026-10-03T00:01:00Z")],
    }))));
    render(<LogsTab appId="a" />);
    await screen.findByText("new");
    const cells = screen.getAllByRole("row").slice(1).map((r) => r.textContent ?? "");
    expect(cells[0]).toContain("new");
    expect(cells[1]).toContain("old");
  });
});
