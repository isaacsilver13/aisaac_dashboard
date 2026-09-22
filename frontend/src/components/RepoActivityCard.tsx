import { GitCommitHorizontal, GitPullRequest } from "lucide-react";

import type { RepoActivity } from "../types";
import { CiStatusBadge } from "./CiStatusBadge";
import { GlassCard } from "./GlassCard";

interface RepoActivityCardProps {
  activity: RepoActivity;
  index: number;
}

export function RepoActivityCard({ activity, index }: RepoActivityCardProps) {
  return (
    <GlassCard className="app-card" style={{ "--card-index": index } as React.CSSProperties}>
      <div className="card-topline">
        <span className="card-category">{activity.category}</span>
        <CiStatusBadge status={activity.ci_status} />
      </div>
      <div className="card-heading">
        <div>
          <h2>{activity.name}</h2>
          <p>
            {activity.owner}/{activity.repo}
          </p>
        </div>
      </div>
      <div className="card-rule" />
      <div className="card-facts">
        <div className="fact">
          <GitPullRequest size={15} aria-hidden="true" />
          <span>
            {activity.open_pr_count === null ? "PRs unknown" : `${activity.open_pr_count} open PR(s)`}
          </span>
        </div>
        <div className="fact">
          <GitCommitHorizontal size={15} aria-hidden="true" />
          <span>
            {activity.commits_last_7d === null
              ? "Commits unknown"
              : `${activity.commits_last_7d} commit(s) this week`}
          </span>
        </div>
        <div className="fact">
          <span>
            {activity.open_issue_count === null ? "Issues unknown" : `${activity.open_issue_count} open issue(s)`}
          </span>
        </div>
      </div>
      {activity.detail && <p className="card-detail">{activity.detail}</p>}
    </GlassCard>
  );
}
