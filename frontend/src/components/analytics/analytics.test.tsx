import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { RepoActivity } from "../../types";
import { CommitActivityChart } from "./CommitActivityChart";

function makeActivity(overrides: Partial<RepoActivity>): RepoActivity {
  return {
    repo_id: "repo",
    name: "Repo",
    category: "app",
    owner: "isaacsilver13",
    repo: "repo",
    ci_status: "success",
    open_issue_count: 0,
    open_pr_count: 0,
    open_pull_requests: [],
    commits_last_7d: 0,
    last_commit_at: null,
    checked_at: "2026-09-25T12:00:00Z",
    cached: false,
    detail: null,
    ...overrides,
  };
}

describe("CommitActivityChart", () => {
  it("shows an empty state when no repo has commit data", () => {
    render(<CommitActivityChart activity={[makeActivity({ commits_last_7d: null })]} />);
    expect(screen.getByText("No commit data reported for any tracked repo.")).toBeInTheDocument();
  });

  it("renders a chart when commit data is present", () => {
    const { container } = render(<CommitActivityChart activity={[makeActivity({ name: "Vinyl", commits_last_7d: 5 })]} />);
    expect(container.querySelector(".recharts-responsive-container")).toBeInTheDocument();
  });
});
