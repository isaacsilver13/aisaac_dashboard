import { CircleCheck, CircleDashed, CircleX, TriangleAlert } from "lucide-react";

import type { HealthState } from "../types";

const statusConfig: Record<HealthState, { label: string; className: string; Icon: typeof CircleCheck }> = {
  up: { label: "Operational", className: "status-up", Icon: CircleCheck },
  degraded: { label: "Degraded", className: "status-degraded", Icon: TriangleAlert },
  down: { label: "Down", className: "status-down", Icon: CircleX },
  unavailable: { label: "Not configured", className: "status-unavailable", Icon: CircleDashed },
};

interface StatusBadgeProps {
  state: HealthState;
  compact?: boolean;
}

export function StatusBadge({ state, compact = false }: StatusBadgeProps) {
  const config = statusConfig[state];
  return (
    <span className={`status-badge ${config.className}${compact ? " status-badge-compact" : ""}`}>
      <config.Icon size={compact ? 14 : 16} strokeWidth={2.2} aria-hidden="true" />
      <span>{config.label}</span>
    </span>
  );
}
