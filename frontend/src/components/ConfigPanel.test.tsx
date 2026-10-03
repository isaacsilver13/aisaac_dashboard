import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ConfigPanel } from "./ConfigPanel";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("ConfigPanel", () => {
  it("shows which settings are set, sending the token", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ items: [
      { key: "fly_api_token", label: "Fly API token", used_for: "Deployments", configured: true },
      { key: "github_token", label: "GitHub token", used_for: "Repo data", configured: false },
    ] })));
    vi.stubGlobal("fetch", fetchMock);
    render(<ConfigPanel token="t" />);
    expect(await screen.findByText("Fly API token")).toBeTruthy();
    expect(screen.getByText("Set")).toBeTruthy();
    expect(screen.getByText("Not set")).toBeTruthy();
    expect((fetchMock.mock.calls[0] as unknown[])[1]).toMatchObject({ headers: { "X-Dashboard-Token": "t" } });
  });
});
