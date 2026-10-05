import { useMemo } from "react";
import { Link } from "react-router-dom";

import type { VaultGraph } from "../../types";
import { noteHref } from "../dashboard/secondBrain";
import { layout } from "./graphLayout";

const SIZE = { w: 800, h: 480 };

/** Labels are drawn only in neighbourhood mode (`current` set); the full vault relies on hover titles. */
export function Graph({ graph, current }: { graph: VaultGraph; current?: string }) {
  const pos = useMemo(() => layout(graph.nodes, graph.edges, SIZE), [graph]);
  return (
    <svg className="kb-graph" viewBox={`0 0 ${SIZE.w} ${SIZE.h}`} role="img" aria-label="Note graph">
      {graph.edges.map(
        ([s, d]) =>
          pos[s] &&
          pos[d] && <line key={`${s}>${d}`} x1={pos[s].x} y1={pos[s].y} x2={pos[d].x} y2={pos[d].y} />,
      )}
      {graph.nodes.map((n) => (
        <Link key={n.path} to={noteHref(n.path)}>
          <circle
            cx={pos[n.path].x}
            cy={pos[n.path].y}
            r={n.path === current ? 7 : 5}
            className={`node-${n.folder}${n.path === current ? " node-current" : ""}`}
          >
            <title>{n.title}</title>
          </circle>
          {current && (
            <text x={pos[n.path].x + 8} y={pos[n.path].y + 3}>
              {n.title}
            </text>
          )}
        </Link>
      ))}
    </svg>
  );
}
