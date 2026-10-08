import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import Shoes from "./Shoes";

const watch = { id: 7, kind: "release", name: "AJ1 launch", keywords: "", size: null, condition: null, max_price: null, url: "https://example.com/launch" };
const listing = {
  id: 1, watch_id: 7, watch_name: "AJ1 launch", title: "AJ1 High", price: 120, prev_price: 140, condition: null,
  source: "ebay", url: "https://example.com/l", observed_at: "2026-10-07T12:00:00+00:00", changed_at: "2026-10-07T12:00:00+00:00", history: [],
};
const snapshot = (over = {}) => ({ watches: [watch], listings: [listing], configured: true, freshness_at: "2026-10-07T12:00:00+00:00", ...over });
const ownBody = { items: [], connections: [] };
const json = (body: unknown, url = "") => new Response(JSON.stringify(String(url).includes("/own") ? ownBody : body));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.localStorage.clear();
  window.sessionStorage.clear();
});

describe("Shoes", () => {
  it("asks for a token when none is stored", () => {
    render(<Shoes />);
    expect(screen.getByText(/dashboard token/)).toBeTruthy();
  });

  it("shows watches, price change and a notice when no provider is configured", async () => {
    window.localStorage.setItem("aisaac.dashboardToken", "t");
    vi.stubGlobal("fetch", vi.fn(async (u: string) => json(snapshot({ configured: false }), u)));
    render(<Shoes />);
    const link = (await screen.findByText("AJ1 launch")) as HTMLAnchorElement;
    expect(link.rel).toContain("noopener");
    expect(screen.getByText("$120.00 (was $140.00)")).toBeTruthy();
    expect(screen.getByText(/No listing provider/)).toBeTruthy();
  });

  it("shows the empty state for no watches", async () => {
    window.localStorage.setItem("aisaac.dashboardToken", "t");
    vi.stubGlobal("fetch", vi.fn(async (u: string) => json(snapshot({ watches: [], listings: [] }), u)));
    render(<Shoes />);
    expect(await screen.findByText("No watches yet.")).toBeTruthy();
  });

  it("disables writes without a write token and archives with one", async () => {
    window.localStorage.setItem("aisaac.dashboardToken", "t");
    const fetchMock = vi.fn(async (_url: string, init?: RequestInit) =>
      init?.method === "DELETE" ? new Response(null, { status: 204 }) : json(snapshot(), _url),
    );
    vi.stubGlobal("fetch", fetchMock);
    const { unmount } = render(<Shoes />);
    expect(((await screen.findByLabelText(/^Archive /)) as HTMLButtonElement).disabled).toBe(true);
    unmount();

    window.sessionStorage.setItem("aisaac.dashboardWriteToken", "w");
    render(<Shoes />);
    fireEvent.click(await screen.findByLabelText(/^Archive /));
    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([u, i]) => String(u).endsWith("/watches/7") && i?.method === "DELETE")).toBe(true),
    );
  });

  it("limits StockX watches to size 10 or 10.5", async () => {
    window.localStorage.setItem("aisaac.dashboardToken", "t");
    window.sessionStorage.setItem("aisaac.dashboardWriteToken", "w");
    const fetchMock = vi.fn(async (u: string, init?: RequestInit) =>
      init?.method === "POST" ? new Response(JSON.stringify({ id: 9 }), { status: 201 }) : json(snapshot(), u),
    );
    vi.stubGlobal("fetch", fetchMock);
    render(<Shoes />);
    fireEvent.change(await screen.findByLabelText("Type"), { target: { value: "stockx" } });
    const size = screen.getByLabelText("Size") as HTMLSelectElement;
    expect(Array.from(size.options).map((o) => o.value)).toEqual(["10", "10.5"]);
    fireEvent.change(size, { target: { value: "10.5" } });
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "AJ4" } });
    fireEvent.click(screen.getByText("Add watch"));
    await waitFor(() => {
      const post = fetchMock.mock.calls.find(([, i]) => i?.method === "POST");
      expect(JSON.parse(String(post?.[1]?.body))).toMatchObject({ kind: "stockx", size: "10.5" });
    });
  });

  it("shows an error state when the request fails", async () => {
    window.localStorage.setItem("aisaac.dashboardToken", "t");
    vi.stubGlobal("fetch", vi.fn(async () => new Response("", { status: 500 })));
    render(<Shoes />);
    expect(await screen.findByRole("alert")).toBeTruthy();
  });
});
