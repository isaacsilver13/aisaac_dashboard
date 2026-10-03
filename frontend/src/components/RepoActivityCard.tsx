import type { RepoActivity } from "../types";
import { CiStatusBadge } from "./CiStatusBadge";
import type { Column, TableFilter } from "./primitives/Table";

function formatLastCommit(value: string | null): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(new Date(value));
}

export const repoColumns: Column<RepoActivity>[] = [
  {
    key: "name",
    header: "Repo",
    sortValue: (r) => r.name,
    render: (r) => (
      <>
        <div className="repo-cell-name">{r.name}</div>
        <div className="repo-cell-path">{r.owner}/{r.repo}</div>
        {r.detail && <div className="repo-cell-detail">{r.detail}</div>}
      </>
    ),
  },
  { key: "category", header: "Category", sortValue: (r) => r.category, render: (r) => r.category },
  { key: "ci", header: "CI", sortValue: (r) => r.ci_status, render: (r) => <CiStatusBadge status={r.ci_status} /> },
  { key: "prs", header: "Open PRs", align: "right", sortValue: (r) => r.open_pr_count, render: (r) => r.open_pr_count ?? "—" },
  { key: "issues", header: "Open issues", align: "right", sortValue: (r) => r.open_issue_count, render: (r) => r.open_issue_count ?? "—" },
  { key: "commits", header: "Commits (7d)", align: "right", sortValue: (r) => r.commits_last_7d, render: (r) => r.commits_last_7d ?? "—" },
  { key: "last", header: "Last commit", sortValue: (r) => r.last_commit_at, render: (r) => formatLastCommit(r.last_commit_at) },
];

export const repoFilters: TableFilter<RepoActivity>[] = [
  { label: "Category", value: (r) => r.category },
  { label: "CI", value: (r) => r.ci_status },
];

export const repoSearchText = (r: RepoActivity) => `${r.name} ${r.owner}/${r.repo} ${r.category}`;
