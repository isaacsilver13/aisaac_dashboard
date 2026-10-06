import { Refresh } from "iconoir-react";

import { fetchAnalytics, fetchIncidents } from "../api";
import { ErrorState } from "../components/primitives/ErrorState";
import { PageHeader } from "../components/primitives/PageHeader";
import { Table, type Column } from "../components/primitives/Table";
import { useAsyncData } from "../hooks/useAsyncData";

interface Task {
  key: string;
  kind: "Pull request" | "Incident";
  title: string;
  url: string | null;
  source: string;
  opened: string;
  stale: boolean;
}

const day = (iso: string) => new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(new Date(iso));

const columns: Column<Task>[] = [
  { key: "kind", header: "Kind", sortValue: (t) => t.kind, render: (t) => t.kind },
  {
    key: "title",
    header: "Item",
    sortValue: (t) => t.title,
    render: (t) => (t.url ? <a href={t.url} target="_blank" rel="noreferrer">{t.title}</a> : t.title),
  },
  { key: "source", header: "Source", sortValue: (t) => t.source, render: (t) => t.source },
  { key: "opened", header: "Opened", sortValue: (t) => t.opened, render: (t) => day(t.opened) },
  { key: "flag", header: "Flag", sortValue: (t) => (t.stale ? 1 : 0), render: (t) => (t.stale ? "stale" : "—") },
];

export default function Tasks() {
  const repos = useAsyncData(fetchAnalytics);
  const incidents = useAsyncData(() => fetchIncidents());

  const tasks: Task[] = [
    ...(repos.data ?? []).flatMap((r) =>
      r.open_pull_requests.map((pr): Task => ({
        key: `pr-${r.repo_id}-${pr.number}`, kind: "Pull request", title: pr.title, url: pr.url,
        source: r.name, opened: pr.opened_at, stale: pr.stale,
      })),
    ),
    ...(incidents.data ?? [])
      .filter((i) => i.resolved_at === null)
      .map((i): Task => ({
        key: `incident-${i.id}`, kind: "Incident", title: i.failure_type, url: null,
        source: i.app_id, opened: i.started_at, stale: false,
      })),
  ];
  const error = repos.error ?? incidents.error;
  const refreshing = repos.refreshing || incidents.refreshing;
  const reloadAll = () => void Promise.all([repos.reload(true), incidents.reload(true)]);

  return (
    <>
      <PageHeader
        title="Tasks"
        description={`${tasks.length} open item${tasks.length === 1 ? "" : "s"}: pull requests across tracked repos and unresolved incidents.`}
        actions={
          <button className="refresh-button" type="button" disabled={refreshing} onClick={reloadAll}>
            <Refresh width={16} height={16} aria-hidden="true" />
            <span>{refreshing ? "Checking" : "Refresh"}</span>
          </button>
        }
      />
      {error ? (
        <ErrorState message={error} onRetry={reloadAll} retrying={refreshing} />
      ) : repos.loading || incidents.loading ? null : (
        <Table
          columns={columns}
          rows={tasks}
          rowKey={(t) => t.key}
          searchText={(t) => `${t.title} ${t.source}`}
          filters={[{ label: "Kind", value: (t) => t.kind }, { label: "Source", value: (t) => t.source }]}
          emptyMessage="Nothing open."
        />
      )}
    </>
  );
}
