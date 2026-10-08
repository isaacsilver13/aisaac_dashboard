import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import Sports from "./Sports";

const event = (over = {}) => ({
  id: "1", league: "NCAAF", home: "Ohio State", away: "Iowa", home_score: null, away_score: null,
  status: "scheduled", start_at: "2026-10-07T20:00:00+00:00", home_conference: "Big Ten",
  away_conference: "Big Ten", home_rank: 3, away_rank: null, poll_date: "2026-10-05",
  url: "https://example.com/g", ...over,
});
const links = { NFL: "https://nfl.test", NBA: "https://nba.test", MLB: "https://mlb.test", NCAAF: "https://f.test", NCAAB: "https://b.test" };
const snapshot = (over = {}) => ({
  events: [event(), event({ id: "2", home: "Tulane", away: "Rice", home_rank: null, home_conference: "AAC" })],
  priority: [], priority_teams: {}, official_links: links,
  rankings: { poll_date: "2026-10-05", current: true }, configured: true,
  freshness_at: "2026-10-07T12:00:00+00:00", last_error: null, ...over,
});
const json = (body: unknown) => new Response(JSON.stringify(body));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.localStorage.clear();
});

describe("Sports", () => {
  it("asks for a token when none is stored", () => {
    render(<Sports />);
    expect(screen.getByText(/dashboard token/)).toBeTruthy();
  });

  it("filters to AP Top 25 games when the poll is current", async () => {
    window.localStorage.setItem("aisaac.dashboardToken", "t");
    vi.stubGlobal("fetch", vi.fn(async () => json(snapshot())));
    render(<Sports />);
    expect(await screen.findByText("Rice at Tulane")).toBeTruthy();
    fireEvent.click(screen.getByLabelText(/AP Top 25 only/));
    expect(screen.queryByText("Rice at Tulane")).toBeNull();
    expect(screen.getByText("Iowa at #3 Ohio State")).toBeTruthy();
  });

  it("disables Top 25 and says rankings are unavailable when the poll is stale", async () => {
    window.localStorage.setItem("aisaac.dashboardToken", "t");
    const stale = snapshot({ rankings: { poll_date: "2026-09-01", current: false } });
    vi.stubGlobal("fetch", vi.fn(async () => json(stale)));
    render(<Sports />);
    expect(await screen.findByText(/Rankings unavailable/)).toBeTruthy();
    expect((screen.getByLabelText(/AP Top 25 only/) as HTMLInputElement).disabled).toBe(true);
  });

  it("links to official scoreboards when no provider is configured", async () => {
    window.localStorage.setItem("aisaac.dashboardToken", "t");
    const none = snapshot({ events: [], configured: false, freshness_at: null });
    vi.stubGlobal("fetch", vi.fn(async () => json(none)));
    render(<Sports />);
    const link = (await screen.findByText("NFL")) as HTMLAnchorElement;
    expect(link.href).toBe("https://nfl.test/");
    expect(screen.getByText("No games match.")).toBeTruthy();
  });

  it("flags a failed refresh while keeping saved games", async () => {
    window.localStorage.setItem("aisaac.dashboardToken", "t");
    vi.stubGlobal("fetch", vi.fn(async () => json(snapshot({ last_error: "fetch_failed" }))));
    render(<Sports />);
    expect(await screen.findByText(/latest refresh failed/)).toBeTruthy();
    expect(screen.getByText("Rice at Tulane")).toBeTruthy();
  });

  it("shows an error state when the request fails", async () => {
    window.localStorage.setItem("aisaac.dashboardToken", "t");
    vi.stubGlobal("fetch", vi.fn(async () => new Response("", { status: 500 })));
    render(<Sports />);
    expect(await screen.findByRole("alert")).toBeTruthy();
  });
});
