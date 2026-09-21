import { useCallback, useEffect, useState } from "react";
import { RefreshCw, WifiOff } from "lucide-react";

import { fetchAnalytics } from "../api";
import { RepoActivityCard } from "../components/RepoActivityCard";
import type { RepoActivity } from "../types";

export default function Analytics() {
  const [activity, setActivity] = useState<RepoActivity[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async (forceRefresh = false) => {
    setError(null);
    if (forceRefresh) setRefreshing(true);
    try {
      setActivity(await fetchAnalytics(forceRefresh));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to reach the dashboard service.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  return (
    <section className="apps-section" aria-labelledby="analytics-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Build &amp; deploy health</p>
          <h2 id="analytics-heading">Analytics</h2>
        </div>
        <button className="refresh-button" type="button" onClick={() => void load(true)} disabled={refreshing}>
          <RefreshCw size={16} className={refreshing ? "spin" : ""} aria-hidden="true" />
          <span>{refreshing ? "Checking" : "Refresh"}</span>
        </button>
      </div>
      {error && (
        <div className="error-banner" role="alert">
          <WifiOff size={18} aria-hidden="true" />
          <span>{error}</span>
          <button type="button" onClick={() => void load(true)}>Try again</button>
        </div>
      )}
      {loading ? (
        <div className="bento-grid loading-grid" aria-label="Loading repo activity">
          {[1, 2, 3, 4].map((item) => <div className="skeleton-card" key={item} />)}
        </div>
      ) : (
        <div className="bento-grid">
          {activity.map((item, index) => (
            <RepoActivityCard key={item.repo_id} activity={item} index={index} />
          ))}
        </div>
      )}
    </section>
  );
}
