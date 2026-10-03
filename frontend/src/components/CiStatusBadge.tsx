import { CheckCircle, Circle, XmarkCircle, RefreshDouble } from "iconoir-react";

import type { CiStatus } from "../types";

const config: Record<CiStatus, { label: string; className: string; Icon: typeof CheckCircle }> = {
  success: { label: "Passing", className: "status-up", Icon: CheckCircle },
  failure: { label: "Failing", className: "status-down", Icon: XmarkCircle },
  in_progress: { label: "Running", className: "status-degraded", Icon: RefreshDouble },
  unknown: { label: "No CI runs", className: "status-unavailable", Icon: Circle },
};

interface CiStatusBadgeProps {
  status: CiStatus;
}

export function CiStatusBadge({ status }: CiStatusBadgeProps) {
  const { label, className, Icon } = config[status];
  return (
    <span className={`status-badge status-badge-compact ${className}`}>
      <Icon width={14} height={14} aria-hidden="true" />
      <span>{label}</span>
    </span>
  );
}
