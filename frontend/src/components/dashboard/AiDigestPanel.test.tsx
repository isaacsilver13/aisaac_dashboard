import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AiDigestPanel } from "./AiDigestPanel";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.localStorage.clear();
});

const item = (id: number, priority: number) => ({
  id, title: `Item ${id}`, url: `https://example.com/${id}`, source: "Blog", published_at: "2026-10-02T12:00:00Z",
  category: "news", priority, summary: "s", why_it_matters: "",
});

function setup(body: unknown) {
  window.localStorage.setItem("aisaac.dashboardToken", "t");
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(body))));
  render(<MemoryRouter><AiDigestPanel /></MemoryRouter>);
}

describe("AiDigestPanel", () => {
  it("shows the three highest-priority items, each linking to its source", async () => {
    setup({ digest_date: "2026-10-03", items: [item(1, 2), item(2, 5), item(3, 4), item(4, 3)], pushed_at: "x" });
    const link = await screen.findByRole("link", { name: "Item 2" });
    expect(link.getAttribute("href")).toBe("https://example.com/2");
    expect(screen.getByRole("link", { name: "Item 3" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Item 4" })).toBeTruthy();
    expect(screen.queryByText("Item 1")).toBeNull();
    expect(screen.getByRole("link", { name: "Open the full digest" }).getAttribute("href")).toBe("/ai-digest");
  });

  it("renders nothing without a token or before a digest exists", async () => {
    render(<MemoryRouter><AiDigestPanel /></MemoryRouter>);
    expect(screen.queryByLabelText("AI digest")).toBeNull();
    cleanup();
    setup({ digest_date: null, items: [], pushed_at: null });
    await vi.waitFor(() => expect(vi.mocked(fetch)).toHaveBeenCalled());
    expect(screen.queryByLabelText("AI digest")).toBeNull();
  });
});
