import type { CIEvent } from "../../types";
import { CiStatusBadge } from "../CiStatusBadge";

interface ComEventRowProps {
  event: CIEvent;
}

function formatReceivedAt(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

export function ComEventRow({ event }: ComEventRowProps) {
  return (
    <li className="task-item">
      <CiStatusBadge status={event.ci_status} />
      <span>
        {event.repo} · {event.event_type}
      </span>
      {event.details && <span className="card-detail">{event.details}</span>}
      <span className="task-meta">
        {formatReceivedAt(event.received_at)}
        {!event.notified ? " · debounced" : ""}
      </span>
    </li>
  );
}
