import { Card } from "../primitives/Card";
import { Stat } from "../primitives/Stat";
import { StatusDot } from "../primitives/StatusDot";
import type { CheckResult } from "../../types";

interface SystemOverviewProps {
  results: CheckResult[];
  loading: boolean;
  lastChecked?: string;
}

export function SystemOverview({ results, loading, lastChecked }: SystemOverviewProps) {
  const total = results.length;
  const down = results.filter((result) => result.state === "down").length;
  const degraded = results.filter((result) => result.state === "degraded").length;
  const unavailable = results.filter((result) => result.state === "unavailable").length;
  const operational = total - down - degraded - unavailable;

  return (
    <Card>
      <div className="ui-stat-label" style={{ marginBottom: 12 }}>System status</div>
      <Stat
        label="Operational"
        value={loading ? "--" : `${operational}/${total}`}
      />
      <div style={{ display: "flex", gap: 16, marginTop: 16, flexWrap: "wrap" }}>
        <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
          <StatusDot tone="success" label="Operational" /> {operational} operational
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
          <StatusDot tone="warning" label="Degraded" /> {degraded} degraded
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
          <StatusDot tone="error" label="Down" /> {down} down
        </span>
      </div>
      {lastChecked && (
        <div className="ui-stat-label" style={{ marginTop: 16 }}>Last checked {lastChecked}</div>
      )}
    </Card>
  );
}
