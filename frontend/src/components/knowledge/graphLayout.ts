import type { NoteRef, VaultGraph } from "../../types";

export function neighborhood(g: VaultGraph, path: string): VaultGraph {
  const keep = neighbors(g.edges, path);
  return {
    nodes: g.nodes.filter((n) => keep.has(n.path)),
    edges: g.edges.filter(([s, d]) => keep.has(s) && keep.has(d)),
  };
}

/** The node itself plus every node directly linked to it, in either direction. */
export function neighbors(edges: [string, string][], path: string): Set<string> {
  const out = new Set([path]);
  for (const [s, d] of edges) {
    if (s === path) out.add(d);
    if (d === path) out.add(s);
  }
  return out;
}

/** Paths whose title contains the query (case-insensitive); a blank query matches nothing. */
export function searchMatches(nodes: NoteRef[], query: string): Set<string> {
  const q = query.trim().toLowerCase();
  return new Set(q ? nodes.filter((n) => n.title.toLowerCase().includes(q)).map((n) => n.path) : []);
}
