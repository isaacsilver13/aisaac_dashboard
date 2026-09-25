import type { RepoActivity } from "../types";
import { CiStatusBadge } from "./CiStatusBadge";

interface RepoActivityRowProps {
  activity: RepoActivity;
}

function formatLastCommit(value: string | null): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(new Date(value));
}

export function RepoActivityRow({ activity }: RepoActivityRowProps) {
  return (
    <tr>
      <td>
        <div className="repo-cell-name">{activity.name}</div>
        <div className="repo-cell-path">{activity.owner}/{activity.repo}</div>
        {activity.detail && <div className="repo-cell-detail">{activity.detail}</div>}
      </td>
      <td>{activity.category}</td>
      <td><CiStatusBadge status={activity.ci_status} /></td>
      <td>{activity.open_pr_count ?? "—"}</td>
      <td>{activity.open_issue_count ?? "—"}</td>
      <td>{activity.commits_last_7d ?? "—"}</td>
      <td>{formatLastCommit(activity.last_commit_at)}</td>
    </tr>
  );
}
