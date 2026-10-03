import { WarningTriangle, ArrowUpRight, Refresh } from "iconoir-react";

import { fetchAnalytics } from "../api";
import { Card } from "../components/primitives/Card";
import { EmptyState } from "../components/primitives/EmptyState";
import { ErrorState } from "../components/primitives/ErrorState";
import { PageHeader } from "../components/primitives/PageHeader";
import { Skeleton } from "../components/primitives/Skeleton";
import { useAsyncData } from "../hooks/useAsyncData";

function formatOpenedAt(value: string): string {
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(new Date(value));
}

export default function Tasks() {
  const { data: activity, loading, refreshing, error, reload } = useAsyncData(fetchAnalytics);

  const reposWithOpenWork = (activity ?? []).filter((item) => item.open_pull_requests.length > 0);
  const openPrCount = reposWithOpenWork.reduce((total, item) => total + item.open_pull_requests.length, 0);

  return (
    <>
      <PageHeader
        title="Tasks"
        description={
          openPrCount > 0
            ? `${openPrCount} open pull request${openPrCount === 1 ? "" : "s"} across ${reposWithOpenWork.length} repo${reposWithOpenWork.length === 1 ? "" : "s"}.`
            : "The open backlog across your tracked repos."
        }
        actions={
          <button className="refresh-button" type="button" onClick={() => void reload(true)} disabled={refreshing}>
            <Refresh width={16} height={16} className={refreshing ? "spin" : ""} aria-hidden="true" />
            <span>{refreshing ? "Checking" : "Refresh"}</span>
          </button>
        }
      />

      {error ? (
        <ErrorState message={error} onRetry={() => void reload(true)} retrying={refreshing} />
      ) : loading ? (
        <div className="task-groups" aria-label="Loading tasks">
          {[1, 2].map((item) => <Skeleton height={140} key={item} />)}
        </div>
      ) : reposWithOpenWork.length > 0 ? (
        <div className="task-groups">
          {reposWithOpenWork.map((item) => (
            <Card className="task-group" key={item.repo_id}>
              <div className="tile-kicker">{item.name}</div>
              <ul className="task-list">
                {item.open_pull_requests.map((pr) => (
                  <li className="task-item" key={pr.number}>
                    {pr.stale && <WarningTriangle width={14} height={14} className="task-stale-icon" aria-hidden="true" />}
                    <a href={pr.url} target="_blank" rel="noreferrer">
                      {pr.title}
                    </a>
                    <span className="task-meta">
                      opened {formatOpenedAt(pr.opened_at)}
                      {pr.stale ? " · stale" : ""}
                    </span>
                    <ArrowUpRight width={14} height={14} aria-hidden="true" />
                  </li>
                ))}
              </ul>
            </Card>
          ))}
        </div>
      ) : (
        <EmptyState message="No open pull requests across any tracked repo." />
      )}
    </>
  );
}
