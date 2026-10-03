import { Refresh } from "iconoir-react";

import { fetchAnalytics } from "../api";
import { CommitActivityChart } from "../components/analytics/CommitActivityChart";
import { Card } from "../components/primitives/Card";
import { EmptyState } from "../components/primitives/EmptyState";
import { ErrorState } from "../components/primitives/ErrorState";
import { PageHeader } from "../components/primitives/PageHeader";
import { Skeleton } from "../components/primitives/Skeleton";
import { Stat } from "../components/primitives/Stat";
import { Table } from "../components/primitives/Table";
import { repoColumns, repoFilters, repoSearchText } from "../components/RepoActivityCard";
import { useAsyncData } from "../hooks/useAsyncData";
import type { RepoActivity } from "../types";

function sumField(repos: RepoActivity[], select: (repo: RepoActivity) => number | null): number {
  return repos.reduce((total, repo) => total + (select(repo) ?? 0), 0);
}

export default function Analytics() {
  const { data: activity, loading, refreshing, error, reload } = useAsyncData(fetchAnalytics);
  const repos = activity ?? [];

  const openPrCount = sumField(repos, (repo) => repo.open_pr_count);
  const openIssueCount = sumField(repos, (repo) => repo.open_issue_count);
  const commitCount = sumField(repos, (repo) => repo.commits_last_7d);

  return (
    <>
      <PageHeader
        title="Analytics"
        description="Build and deploy health across tracked repos."
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
        <div className="analytics-top-row" aria-label="Loading analytics">
          <Skeleton height={100} />
          <Skeleton height={100} />
          <Skeleton height={100} />
        </div>
      ) : (
        <>
          <div className="analytics-top-row">
            <Card><Stat label="Open pull requests" value={openPrCount} /></Card>
            <Card><Stat label="Open issues" value={openIssueCount} /></Card>
            <Card><Stat label="Commits, last 7 days" value={commitCount} /></Card>
          </div>

          <div className="activity-feed-section">
            <CommitActivityChart activity={repos} />
          </div>
        </>
      )}

      {!loading && !error && (
        <div className="activity-feed-section">
          {repos.length > 0 ? (
            <Table columns={repoColumns} rows={repos} rowKey={(r) => r.repo_id} searchText={repoSearchText} filters={repoFilters} />
          ) : (
            <EmptyState message="No repositories are configured for this profile." />
          )}
        </div>
      )}
    </>
  );
}
