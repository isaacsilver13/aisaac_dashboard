import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { RepoActivity } from "../../types";
import { Card } from "../primitives/Card";
import { EmptyState } from "../primitives/EmptyState";

interface CommitActivityChartProps {
  activity: RepoActivity[];
}

interface ChartDatum {
  name: string;
  commits: number;
}

export function CommitActivityChart({ activity }: CommitActivityChartProps) {
  const data: ChartDatum[] = activity
    .filter((item): item is RepoActivity & { commits_last_7d: number } => item.commits_last_7d !== null)
    .map((item) => ({ name: item.name, commits: item.commits_last_7d }));

  return (
    <Card>
      <div className="ui-stat-label" style={{ marginBottom: 12 }}>Commits, last 7 days</div>
      {data.length === 0 ? (
        <EmptyState message="No commit data reported for any tracked repo." />
      ) : (
        <div style={{ height: 220 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" vertical={false} />
              <XAxis
                dataKey="name"
                tick={{ fill: "var(--muted)", fontSize: 11 }}
                tickLine={false}
                axisLine={{ stroke: "var(--line)" }}
              />
              <YAxis
                allowDecimals={false}
                tick={{ fill: "var(--muted)", fontSize: 11 }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                cursor={{ fill: "rgba(255, 255, 255, 0.06)" }}
                contentStyle={{
                  background: "#111827",
                  border: "1px solid var(--line)",
                  borderRadius: 8,
                  fontSize: 12,
                }}
                labelStyle={{ color: "var(--ink)" }}
              />
              <Bar dataKey="commits" fill="#667eea" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </Card>
  );
}
