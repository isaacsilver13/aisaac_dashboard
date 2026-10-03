import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DeploymentsTab } from "./DeploymentsTab";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.localStorage.clear();
});

describe("DeploymentsTab", () => {
  it("asks for a token when none is stored", () => {
    render(<DeploymentsTab appId="a" />);
    expect(screen.getByText(/dashboard token/)).toBeTruthy();
  });

  it("lists releases sent with the token", async () => {
    window.localStorage.setItem("aisaac.dashboardToken", "t");
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({
      app_id: "a", fly_app: "a-fly",
      releases: [{ version: 7, status: "complete", description: "Release", reason: "", createdAt: "2026-10-03T00:00:00Z", imageRef: "r/a:deploy-1" }],
    })));
    vi.stubGlobal("fetch", fetchMock);
    render(<DeploymentsTab appId="a" />);
    expect(await screen.findByText("v7")).toBeTruthy();
    expect(screen.getByText("deploy-1")).toBeTruthy();
    expect((fetchMock.mock.calls[0] as unknown[])[1]).toMatchObject({ headers: { "X-Dashboard-Token": "t" } });
  });
});
