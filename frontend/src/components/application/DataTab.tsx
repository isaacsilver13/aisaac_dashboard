import { fetchDashboard } from "../../api";
import { useAsyncData } from "../../hooks/useAsyncData";
import { Card } from "../primitives/Card";
import { EmptyState } from "../primitives/EmptyState";
import { ErrorState } from "../primitives/ErrorState";
import { Stat } from "../primitives/Stat";
import { Table, type Column } from "../primitives/Table";

type Metric = { key: string; value: string };

const columns: Column<Metric>[] = [
  { key: "key", header: "Metric", sortValue: (m) => m.key, render: (m) => m.key },
  { key: "value", header: "Value", align: "right", sortValue: (m) => m.value, render: (m) => m.value },
];

/** Data the app itself reports (allowlisted per app in the registry). Snapshot only; no history yet. */
export function DataTab({ appId }: { appId: string }) {
  const { data, loading, error, reload } = useAsyncData(fetchDashboard);

  if (error) return <ErrorState message={error} onRetry={() => void reload()} />;
  const result = data?.results.find((r) => r.app_id === appId);
  if (!loading && !result) return <EmptyState message="This application is not registered." />;
  if (!result) return null;

  const rows: Metric[] = Object.entries(result.metrics).map(([key, value]) => ({ key, value: String(value) }));

  return (
    <>
      <Card>
        <div style={{ display: "grid", gap: 16, gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))" }}>
          <Stat label="Freshness" value={result.freshness ?? "—"} />
          <Stat label="Metrics" value={result.metrics_state ?? "—"} />
          <Stat label="Provider" value={result.provider_state ?? "—"} />
          <Stat label="Reported" value={new Date(result.checked_at).toLocaleString([], { dateStyle: "short", timeStyle: "short" })} />
        </div>
      </Card>
      <div className="ui-stat-label" style={{ margin: "16px 0 8px" }}>Reported metrics</div>
      <Table columns={columns} rows={rows} rowKey={(m) => m.key} searchText={(m) => m.key} emptyMessage="This app reports no metrics." />
    </>
  );
}
