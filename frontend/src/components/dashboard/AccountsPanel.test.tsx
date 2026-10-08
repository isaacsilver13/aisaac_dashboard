import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AccountsPanel } from "./AccountsPanel";

const own = (over = {}) => ({
  items: [
    { id: 1, provider: "stockx", kind: "bid", external_id: "b1", title: "Dunk Low", price: 90, url: "https://example.com/d", occurred_at: null },
  ],
  connections: [
    { provider: "ebay", available: false, connected: false },
    { provider: "stockx", available: true, connected: true },
  ],
  ...over,
});
const json = (body: unknown) => new Response(JSON.stringify(body));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.localStorage.clear();
  window.sessionStorage.clear();
});

describe("AccountsPanel", () => {
  it("renders nothing without a token", () => {
    const { container } = render(<AccountsPanel />);
    expect(container.textContent).toBe("");
  });

  it("shows connection states and own items without exposing tokens", async () => {
    window.localStorage.setItem("aisaac.dashboardToken", "t");
    vi.stubGlobal("fetch", vi.fn(async () => json(own())));
    render(<AccountsPanel />);
    expect(await screen.findByText(/eBay · not set up/)).toBeTruthy();
    expect(screen.getByText(/StockX · connected/)).toBeTruthy();
    expect(((await screen.findByLabelText("Connect eBay")) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByText("Dunk Low") as HTMLAnchorElement).rel).toContain("noopener");
  });

  it("disconnects with a write token", async () => {
    window.localStorage.setItem("aisaac.dashboardToken", "t");
    window.sessionStorage.setItem("aisaac.dashboardWriteToken", "w");
    const fetchMock = vi.fn(async (_url: string, init?: RequestInit) =>
      init?.method === "DELETE" ? new Response(null, { status: 204 }) : json(own()),
    );
    vi.stubGlobal("fetch", fetchMock);
    render(<AccountsPanel />);
    fireEvent.click(await screen.findByLabelText("Disconnect StockX"));
    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([u, i]) => String(u).endsWith("/connections/stockx") && i?.method === "DELETE")).toBe(true),
    );
  });

  it("shows an error when the request fails", async () => {
    window.localStorage.setItem("aisaac.dashboardToken", "t");
    vi.stubGlobal("fetch", vi.fn(async () => new Response("", { status: 500 })));
    render(<AccountsPanel />);
    expect(await screen.findByRole("alert")).toBeTruthy();
  });
});
