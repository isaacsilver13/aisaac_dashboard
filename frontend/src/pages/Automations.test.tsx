import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import Automations from "./Automations";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.localStorage.clear();
});

describe("Automations", () => {
  it("asks for a token when none is stored", () => {
    render(<Automations />);
    expect(screen.getByText(/dashboard token/)).toBeTruthy();
  });

  it("lists automations with their status", async () => {
    window.localStorage.setItem("aisaac.dashboardToken", "t");
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify([
      { id: "x", name: "Neon usage push", kind: "push", detail: "scripts/", last_run_at: null, expected_hours: 26, status: "never" },
    ]))));
    render(<Automations />);
    expect(await screen.findByText("Neon usage push")).toBeTruthy();
    expect(screen.getAllByText("never").length).toBeGreaterThan(0);
  });
});
