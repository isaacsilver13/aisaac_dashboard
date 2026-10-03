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

  it("shows a history chart for each numeric metric series", async () => {
    vi.stubGlobal("fetch", vi.fn(async (url: string) => new Response(JSON.stringify(
      url.includes("metrics-history")
        ? { series: { games: [{ t: "2026-10-03T00:00:00Z", value: 3 }, { t: "2026-10-03T01:00:00Z", value: 5 }] } }
        : { results: [result({ games: 3 })] },
    ))));
    render(<DataTab appId="a" />);
    expect((await screen.findAllByText("games")).length).toBeGreaterThan(1); // table row + chart title
  });

  it("says so when no metrics are reported", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ results: [result({})] }))));
    render(<DataTab appId="a" />);
    expect(await screen.findByText("This app reports no metrics.")).toBeTruthy();
  });
});
