import type { NoteRef, VaultGraph } from "../../types";

type Pos = { x: number; y: number };

export function neighborhood(g: VaultGraph, path: string): VaultGraph {
  const keep = new Set([path]);
  for (const [s, d] of g.edges) {
    if (s === path) keep.add(d);
    if (d === path) keep.add(s);
  }
  return {
    nodes: g.nodes.filter((n) => keep.has(n.path)),
    edges: g.edges.filter(([s, d]) => keep.has(s) && keep.has(d)),
  };
}

// ponytail: O(n^2 * iterations) force layout; fine for a few hundred notes, switch to d3-force beyond ~1000.
/** Deterministic force layout: circle start, pairwise repulsion, edge springs, centring. */
export function layout(
  nodes: NoteRef[],
  edges: [string, string][],
  { w, h }: { w: number; h: number },
  iterations = 200,
): Record<string, Pos> {
  const pos: Record<string, Pos> = {};
  nodes.forEach((n, i) => {
    const a = (2 * Math.PI * i) / nodes.length;
    pos[n.path] = { x: w / 2 + (w / 3) * Math.cos(a), y: h / 2 + (h / 3) * Math.sin(a) };
  });
  const k = Math.sqrt((w * h) / Math.max(nodes.length, 1));
  for (let it = 0; it < iterations; it++) {
    const cool = 1 - it / iterations;
    const move: Record<string, Pos> = Object.fromEntries(nodes.map((n) => [n.path, { x: 0, y: 0 }]));
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = pos[nodes[i].path];
        const b = pos[nodes[j].path];
        const dx = a.x - b.x || 0.01;
        const dy = a.y - b.y || 0.01;
        const d = Math.hypot(dx, dy);
        const f = (k * k) / d / d;
        move[nodes[i].path].x += dx * f;
        move[nodes[i].path].y += dy * f;
        move[nodes[j].path].x -= dx * f;
        move[nodes[j].path].y -= dy * f;
      }
    }
    for (const [s, d] of edges) {
      const a = pos[s];
      const b = pos[d];
      if (!a || !b) continue;
      const dx = a.x - b.x;
      const dy = a.y - b.y;
      const f = Math.hypot(dx, dy) / k;
      move[s].x -= dx * f;
      move[s].y -= dy * f;
      move[d].x += dx * f;
      move[d].y += dy * f;
    }
    for (const n of nodes) {
      const p = pos[n.path];
      const m = move[n.path];
      const len = Math.hypot(m.x, m.y) || 1;
      const step = Math.min(len, 20 * cool + 1) / len;
      p.x = Math.min(w, Math.max(0, p.x + m.x * step + (w / 2 - p.x) * 0.01));
      p.y = Math.min(h, Math.max(0, p.y + m.y * step + (h / 2 - p.y) * 0.01));
    }
  }
  return pos;
}
