import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import AiDigest from "./AiDigest";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.localStorage.clear();
});

const digest = {
  digest_date: "2026-10-03",
  generated_at: "2026-10-03T11:00:00Z",
  model: "anthropic/claude-sonnet-5-5",
  headline: "Agent design leads [1], with a tooling note [2] and a stray [9].",
  items: [
    { id: 2, title: "A tooling tip", url: "https://tips.example/tip", source: "Tips", published_at: null, category: "technique", priority: 3, summary: "Pin your prompts.", why_it_matters: "" },
    { id: 1, title: "Building effective agents", url: "https://www.example.com/agents", source: "Example Blog", published_at: "2026-10-02T12:00:00Z", category: "systems", priority: 5, summary: "Simple patterns beat frameworks.", why_it_matters: "Applies to this very pipeline." },
  ],
  source_stats: {
    "Example Blog": { fetched: 3, recent: 1, error: null },
    "Broken Feed": { fetched: 0, recent: 0, error: "OSError: HTTP Error 403" },
  },
  pushed_at: "2026-10-03T11:05:00Z",
};

function serve(body: unknown, dates: string[] = ["2026-10-03"]) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) =>
    new Response(JSON.stringify(String(input).endsWith("/dates") ? dates : body)),
  );
  vi.stubGlobal("fetch", fetchMock);
  window.localStorage.setItem("aisaac.dashboardToken", "t");
  return fetchMock;
}

describe("AiDigest", () => {
  it("asks for a token when none is stored", () => {
    render(<AiDigest />);
    expect(screen.getByText(/dashboard token/)).toBeTruthy();
  });

  it("links every item and every headline citation to the item's own source", async () => {
    serve(digest);
    render(<AiDigest />);

    const title = await screen.findByRole("link", { name: /Building effective agents/ });
    expect(title.getAttribute("href")).toBe("https://www.example.com/agents");
    expect(title.getAttribute("target")).toBe("_blank");
    expect(title.getAttribute("rel")).toContain("noopener");

    expect(screen.getByRole("link", { name: "[1]" }).getAttribute("href")).toBe("https://www.example.com/agents");
    expect(screen.getByRole("link", { name: "[2]" }).getAttribute("href")).toBe("https://tips.example/tip");
    // A marker for an item that is not in the digest is text, not a link.
    expect(screen.queryByRole("link", { name: "[9]" })).toBeNull();
    expect(screen.getByText(/stray \[9\]/)).toBeTruthy();
  });

  it("shows summaries, priority and the host each link goes to", async () => {
    serve(digest);
    render(<AiDigest />);
    expect(await screen.findByText("Simple patterns beat frameworks.")).toBeTruthy();
    expect(screen.getByText("Applies to this very pipeline.")).toBeTruthy();
    expect(screen.getByText("P5")).toBeTruthy();
    expect(screen.getByText("example.com")).toBeTruthy();
  });

  it("surfaces sources that failed so a broken feed is noticed", async () => {
    serve(digest);
    render(<AiDigest />);
    expect(await screen.findByText("1 source failed")).toBeTruthy();
    expect(screen.getByText(/Broken Feed: OSError: HTTP Error 403/)).toBeTruthy();
  });

  it("never turns a non-http url into a link", async () => {
    serve({ ...digest, headline: "", items: [{ ...digest.items[0], url: "javascript:alert(1)", title: "Sneaky" }] });
    render(<AiDigest />);
    expect(await screen.findByText("Sneaky")).toBeTruthy();
    expect(screen.queryByRole("link", { name: /Sneaky/ })).toBeNull();
  });

  it("explains how to get the first digest when none exists", async () => {
    serve({ digest_date: null, items: [], pushed_at: null }, []);
    render(<AiDigest />);
    expect(await screen.findByText(/No digest yet/)).toBeTruthy();
  });

  it("loads an older digest when its date is picked", async () => {
    const fetchMock = serve(digest, ["2026-10-03", "2026-10-02"]);
    render(<AiDigest />);
    await screen.findByText("Simple patterns beat frameworks.");
    await userEvent.selectOptions(screen.getByLabelText("Digest date"), "2026-10-02");
    await vi.waitFor(() =>
      expect(fetchMock.mock.calls.some(([url]) => String(url) === "/api/v1/ai-digest/2026-10-02")).toBe(true),
    );
  });
});
