import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DataTab } from "./DataTab";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const result = (metrics: Record<string, number>) => ({
  app_id: "a", state: "up", checked_at: "2026-10-03T00:00:00Z", freshness: "fresh", metrics_state: "up", provider_state: "ok", metrics,
});

describe("DataTab", () => {
  it("lists reported metrics", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ results: [result({ games: 3 })] }))));
    render(<DataTab appId="a" />);
    expect(await screen.findByText("games")).toBeTruthy();
    expect(screen.getByText("fresh")).toBeTruthy();
  });

  it("says so when no metrics are reported", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ results: [result({})] }))));
    render(<DataTab appId="a" />);
    expect(await screen.findByText("This app reports no metrics.")).toBeTruthy();
  });
});
