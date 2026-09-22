import { CircleCheck, CircleDashed, CircleX, Loader } from "lucide-react";

import type { CiStatus } from "../types";

const config: Record<CiStatus, { label: string; className: string; Icon: typeof CircleCheck }> = {
  success: { label: "Passing", className: "status-up", Icon: CircleCheck },
  failure: { label: "Failing", className: "status-down", Icon: CircleX },
  in_progress: { label: "Running", className: "status-degraded", Icon: Loader },
  unknown: { label: "No CI runs", className: "status-unavailable", Icon: CircleDashed },
};

interface CiStatusBadgeProps {
  status: CiStatus;
}

export function CiStatusBadge({ status }: CiStatusBadgeProps) {
  const { label, className, Icon } = config[status];
  return (
    <span className={`status-badge status-badge-compact ${className}`}>
      <Icon size={14} strokeWidth={2.2} aria-hidden="true" />
      <span>{label}</span>
    </span>
  );
}
