import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, ArrowUpRight, WifiOff } from "lucide-react";

import { fetchAnalytics } from "../api";
import { GlassCard } from "../components/GlassCard";
import type { RepoActivity } from "../types";

function formatOpenedAt(value: string): string {
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(new Date(value));
}

export default function Tasks() {
  const [activity, setActivity] = useState<RepoActivity[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setError(null);
    try {
      setActivity(await fetchAnalytics());
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to reach the dashboard service.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  const reposWithOpenWork = activity.filter((item) => item.open_pull_requests.length > 0);

  return (
    <section className="apps-section" aria-labelledby="tasks-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Open backlog</p>
          <h2 id="tasks-heading">Tasks</h2>
        </div>
      </div>
      {error && (
        <div className="error-banner" role="alert">
          <WifiOff size={18} aria-hidden="true" />
          <span>{error}</span>
          <button type="button" onClick={() => void load()}>Try again</button>
        </div>
      )}
      {loading ? (
        <div className="bento-grid loading-grid" aria-label="Loading tasks">
          {[1, 2].map((item) => <div className="skeleton-card" key={item} />)}
        </div>
      ) : reposWithOpenWork.length > 0 ? (
        <div className="task-groups">
          {reposWithOpenWork.map((item) => (
            <GlassCard className="task-group" key={item.repo_id}>
              <div className="tile-kicker">{item.name}</div>
              <ul className="task-list">
                {item.open_pull_requests.map((pr) => (
                  <li className="task-item" key={pr.number}>
                    {pr.stale && <AlertTriangle size={14} className="task-stale-icon" aria-hidden="true" />}
                    <a href={pr.url} target="_blank" rel="noreferrer">
                      {pr.title}
                    </a>
                    <span className="task-meta">
                      opened {formatOpenedAt(pr.opened_at)}
                      {pr.stale ? " · stale" : ""}
                    </span>
                    <ArrowUpRight size={14} aria-hidden="true" />
                  </li>
                ))}
              </ul>
            </GlassCard>
          ))}
        </div>
      ) : (
        <div className="empty-state"><span>No open pull requests across any tracked repo.</span></div>
      )}
    </section>
  );
}
