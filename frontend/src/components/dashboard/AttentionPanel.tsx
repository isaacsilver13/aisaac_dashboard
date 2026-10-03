import { CheckCircle, WarningTriangle } from "iconoir-react";

import { Card } from "../primitives/Card";
import type { CheckResult, Incident } from "../../types";

interface AttentionPanelProps {
  openIncidents: Incident[];
  results: CheckResult[];
}

function formatSince(value: string): string {
  return new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(new Date(value));
}

export function AttentionPanel({ openIncidents, results }: AttentionPanelProps) {
  if (openIncidents.length === 0) {
    return (
      <Card>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <CheckCircle width={18} height={18} style={{ color: "var(--success)" }} aria-hidden="true" />
          <strong style={{ fontSize: 14 }}>All systems nominal</strong>
        </div>
        <p className="ui-stat-label" style={{ marginTop: 10, textTransform: "none", letterSpacing: 0 }}>
          No active incidents.
        </p>
      </Card>
    );
  }

  return (
    <Card>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
        <WarningTriangle width={18} height={18} style={{ color: "var(--warning)" }} aria-hidden="true" />
        <strong style={{ fontSize: 14 }}>Attention required</strong>
      </div>
      <ul style={{ display: "flex", flexDirection: "column", gap: 10, listStyle: "none", margin: 0, padding: 0 }}>
        {openIncidents.map((incident) => {
          const app = results.find((result) => result.app_id === incident.app_id);
          return (
            <li key={incident.id}>
              <a href={`#app-${incident.app_id}`} style={{ color: "inherit", textDecoration: "none" }}>
                <strong style={{ fontSize: 13 }}>{app?.name ?? incident.app_id}</strong>
              </a>
              <div className="ui-stat-label" style={{ textTransform: "none", letterSpacing: 0, marginTop: 2 }}>
                {incident.failure_type} · since {formatSince(incident.started_at)}
              </div>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}
