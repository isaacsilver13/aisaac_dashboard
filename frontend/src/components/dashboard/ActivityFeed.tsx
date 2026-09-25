import { Card } from "../primitives/Card";
import { EmptyState } from "../primitives/EmptyState";
import type { CheckResult } from "../../types";

interface ActivityFeedProps {
  results: CheckResult[];
  limit?: number;
}

function formatCheckedTime(value: string): string {
  return new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(new Date(value));
}

export function ActivityFeed({ results, limit = 6 }: ActivityFeedProps) {
  const recent = results.slice(0, limit);

  return (
    <Card>
      <div className="ui-stat-label" style={{ marginBottom: 12 }}>Recent activity</div>
      {recent.length === 0 ? (
        <EmptyState message="No recent activity." />
      ) : (
        <div className="activity-list">
          {recent.map((result) => (
            <div className="activity-item" key={result.app_id}>
              <span className={`activity-dot activity-${result.state}`} />
              <div>
                <strong>{result.name}</strong>
                <span>{result.detail ?? `${result.state} check completed`}</span>
              </div>
              <time>{formatCheckedTime(result.checked_at)}</time>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
