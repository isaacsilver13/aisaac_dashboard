import { describe, expect, it } from "vitest";

import type { DigestItem } from "../../types";
import { byPriority, failedSources, hostOf, safeHref, splitHeadline } from "./aiDigest";

const item = (id: number, priority: number, published_at: string | null): DigestItem => ({
  id, title: `T${id}`, url: `https://example.com/${id}`, source: "S", published_at,
  category: "news", priority, summary: "s", why_it_matters: "",
});

describe("ai digest helpers", () => {
  it("turns known [id] markers into citations and leaves unknown ones as text", () => {
    expect(splitHeadline("Lead [1], then [9] and [2].", new Set([1, 2]))).toEqual([
      { text: "Lead " },
      { id: 1 },
      { text: ", then [9] and " },
      { id: 2 },
      { text: "." },
    ]);
    expect(splitHeadline("No markers.", new Set([1]))).toEqual([{ text: "No markers." }]);
    expect(splitHeadline("", new Set([1]))).toEqual([]);
  });

  it("only allows http(s) links", () => {
    expect(safeHref("https://example.com/a")).toBe("https://example.com/a");
    expect(safeHref("http://example.com/a")).toBe("http://example.com/a");
    expect(safeHref("javascript:alert(1)")).toBeNull();
    expect(safeHref("data:text/html,x")).toBeNull();
  });

  it("shows the host without www", () => {
    expect(hostOf("https://www.example.com/a/b")).toBe("example.com");
    expect(hostOf("not a url")).toBe("");
  });

  it("orders by priority, then newest, without mutating the input", () => {
    const items = [item(1, 3, "2026-10-01T00:00:00Z"), item(2, 5, "2026-10-01T00:00:00Z"), item(3, 3, "2026-10-02T00:00:00Z"), item(4, 3, null)];
    expect(byPriority(items).map((i) => i.id)).toEqual([2, 3, 1, 4]);
    expect(items.map((i) => i.id)).toEqual([1, 2, 3, 4]);
  });

  it("lists only the sources that errored", () => {
    expect(failedSources({ A: { fetched: 2, error: null }, B: { fetched: 0, error: "HTTP 403" } })).toEqual([
      { name: "B", error: "HTTP 403" },
    ]);
    expect(failedSources(undefined)).toEqual([]);
  });
});
