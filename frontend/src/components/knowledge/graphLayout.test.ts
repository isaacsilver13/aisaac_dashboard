import { describe, expect, it } from "vitest";

import { neighborhood, neighbors, searchMatches } from "./graphLayout";

const n = (path: string, title = path, folder = "wikis") => ({ path, title, folder });
const graph = {
  nodes: ["a", "b", "c", "d"].map((p) => n(p)),
  edges: [
    ["a", "b"],
    ["c", "a"],
    ["c", "d"],
  ] as [string, string][],
};

describe("graph helpers", () => {
  it("keeps the note, its direct neighbours and the edges between them", () => {
    const g = neighborhood(graph, "a");
    expect(g.nodes.map((x) => x.path).sort()).toEqual(["a", "b", "c"]);
    expect(g.edges).toEqual([
      ["a", "b"],
      ["c", "a"],
    ]);
  });

  it("lists a node and its direct neighbours, in either edge direction", () => {
    expect([...neighbors(graph.edges, "a")].sort()).toEqual(["a", "b", "c"]);
    expect([...neighbors(graph.edges, "zzz")]).toEqual(["zzz"]);
  });

  it("matches notes by case-insensitive title substring; blank query matches nothing", () => {
    const nodes = [n("x", "Fly Scale-to-Zero"), n("y", "Gym Tracker")];
    expect([...searchMatches(nodes, "scale")]).toEqual(["x"]);
    expect([...searchMatches(nodes, "  ")]).toEqual([]);
  });
});
