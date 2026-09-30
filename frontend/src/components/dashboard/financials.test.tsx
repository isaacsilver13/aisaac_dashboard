import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { fetchFinancials } from "../../api";
import type { FinancialSnapshot } from "../../types";
import { FinancialsPanel } from "./FinancialsPanel";
import { formatTimeUntil, isStale, usageTone } from "./financials";

const NOW = new Date("2026-09-30T12:00:00Z").getTime();

function makeSnapshot(overrides: Partial<FinancialSnapshot> = {}): FinancialSnapshot {
  const reported = new Date().toISOString();
  return {
    claude: {
      session: { used_pct: 42, resets_at: "2026-10-01T00:00:00Z" },
      weekly: { used_pct: 80, resets_at: "2026-10-03T00:00:00Z" },
      reported_at: reported,
    },
    neon: { period: "2026-09", total_compute_hours: 12.5, by_app: { vinyl: 10, "gym-tracker": 2.5 }, reported_at: reported },
    fly: {
      period: "2026-09",
      total_usd: 10.3,
      by_app: { "vinyl-api": 0.15, "(unattributed)": 10.15 },
      estimated: true,
      reported_at: reported,
    },
    detail: null,
    ...overrides,
  };
}

describe("financials helpers", () => {
  it("picks tone at the 75 and 90 thresholds", () => {
    expect(usageTone(74.9)).toBe("success");
    expect(usageTone(75)).toBe("warning");
    expect(usageTone(90)).toBe("error");
  });

  it("formats time until reset", () => {
    expect(formatTimeUntil("2026-09-30T14:14:00Z", NOW)).toBe("2h 14m");
    expect(formatTimeUntil("2026-10-03T16:00:00Z", NOW)).toBe("3d 4h");
    expect(formatTimeUntil("2026-09-30T11:00:00Z", NOW)).toBe("now");
  });

  it("detects stale reports", () => {
    expect(isStale("2026-09-30T11:00:00Z", 30 * 60 * 1000, NOW)).toBe(true);
    expect(isStale("2026-09-30T11:45:00Z", 30 * 60 * 1000, NOW)).toBe(false);
  });
});

describe("fetchFinancials", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("sends the token header", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(makeSnapshot()), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await fetchFinancials("abc");
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/command-center/financials", {
      headers: { Accept: "application/json", "X-Dashboard-Token": "abc" },
    });
  });

  it("throws an auth error on 401", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("", { status: 401 })));
    await expect(fetchFinancials("bad")).rejects.toThrow("Invalid dashboard token.");
  });
});

describe("FinancialsPanel", () => {
  beforeEach(() => window.localStorage.clear());
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("prompts for a token when none is stored", () => {
    render(<FinancialsPanel />);
    expect(screen.getByLabelText(/access token/i)).toBeInTheDocument();
  });

  it("renders usage, costs and not-reporting state after unlocking", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(makeSnapshot()), { status: 200 })));
    render(<FinancialsPanel />);
    await userEvent.type(screen.getByLabelText(/access token/i), "secret");
    await userEvent.click(screen.getByRole("button", { name: /unlock/i }));

    expect(await screen.findByText("42%")).toBeInTheDocument();
    expect(screen.getByText("80%")).toBeInTheDocument();
    expect(screen.getByText("12.5 h")).toBeInTheDocument();
    expect(screen.getByText("2.50 h")).toBeInTheDocument();
    expect(screen.getByText("vinyl")).toBeInTheDocument();
    expect(screen.getByText("$10.30")).toBeInTheDocument();
    expect(screen.getByText("(unattributed)")).toBeInTheDocument();
    expect(screen.getByText("Estimate")).toBeInTheDocument();
    expect(window.localStorage.getItem("aisaac.dashboardToken")).toBe("secret");
  });

  it("shows not-reporting for a source that has never pushed", async () => {
    window.localStorage.setItem("aisaac.dashboardToken", "secret");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify(makeSnapshot({ fly: null })), { status: 200 })),
    );
    render(<FinancialsPanel />);
    expect(await screen.findByText("Not reporting")).toBeInTheDocument();
  });

  it("clears a rejected token and re-prompts", async () => {
    window.localStorage.setItem("aisaac.dashboardToken", "old");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("", { status: 401 })));
    render(<FinancialsPanel />);
    await waitFor(() => expect(screen.getByLabelText(/access token/i)).toBeInTheDocument());
    expect(screen.getByRole("alert")).toHaveTextContent("not accepted");
    expect(window.localStorage.getItem("aisaac.dashboardToken")).toBeNull();
  });
});
