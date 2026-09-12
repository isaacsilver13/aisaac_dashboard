import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchDashboard } from "./api";

const response = {
  profile: "local",
  refreshed_at: "2026-09-09T12:00:00Z",
  results: [],
};

describe("fetchDashboard", () => {
  afterEach(() => vi.restoreAllMocks());

  it("requests the dashboard without allowing a target URL", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(response), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchDashboard()).resolves.toEqual(response);

    expect(fetchMock).toHaveBeenCalledWith("/api/v1/dashboard", {
      headers: { Accept: "application/json" },
    });
  });

  it("adds an explicit refresh query when requested", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(response), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchDashboard(true);

    expect(fetchMock).toHaveBeenCalledWith("/api/v1/dashboard?force_refresh=true", {
      headers: { Accept: "application/json" },
    });
  });

  it("turns a failed response into a user-safe error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("secret body", { status: 503 })));

    await expect(fetchDashboard()).rejects.toThrow("Dashboard request failed with HTTP 503.");
  });
});
