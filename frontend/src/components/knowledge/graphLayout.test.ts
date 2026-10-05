import { describe, expect, it } from "vitest";

import { layout, neighborhood } from "./graphLayout";

const n = (path: string) => ({ path, title: path, folder: "wikis" });
const graph = {
  nodes: ["a", "b", "c", "d"].map(n),
  edges: [
    ["a", "b"],
    ["c", "a"],
    ["c", "d"],
  ] as [string, string][],
};

describe("graph layout", () => {
  it("keeps the note, its direct neighbours and the edges between them", () => {
    const g = neighborhood(graph, "a");
    expect(g.nodes.map((x) => x.path).sort()).toEqual(["a", "b", "c"]);
    expect(g.edges).toEqual([
      ["a", "b"],
      ["c", "a"],
    ]);
  });

  it("places every node at finite, distinct coordinates inside the box", () => {
    const pos = layout(graph.nodes, graph.edges, { w: 400, h: 300 });
    const pts = Object.values(pos);
    expect(pts).toHaveLength(4);
    for (const p of pts) {
      expect(Number.isFinite(p.x) && Number.isFinite(p.y)).toBe(true);
      expect(p.x).toBeGreaterThanOrEqual(0);
      expect(p.x).toBeLessThanOrEqual(400);
      expect(p.y).toBeGreaterThanOrEqual(0);
      expect(p.y).toBeLessThanOrEqual(300);
    }
    expect(new Set(pts.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`)).size).toBe(4);
  });

  it("handles an empty and a single-node graph", () => {
    expect(layout([], [], { w: 10, h: 10 })).toEqual({});
    expect(Object.keys(layout([n("a")], [], { w: 10, h: 10 }))).toEqual(["a"]);
  });
});
