import { useCallback, useEffect, useState } from "react";
import { Activity, ArrowDownRight, RefreshCw, Server, WifiOff } from "lucide-react";

import { fetchDashboard } from "./api";
import { AppCard } from "./components/AppCard";
import { GlassCard } from "./components/GlassCard";
import type { DashboardResponse, HealthState } from "./types";

const stateOrder: HealthState[] = ["up", "degraded", "down", "unavailable"];

function formatRefreshTime(value: string): string {
  return new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit", second: "2-digit" }).format(
    new Date(value),
  );
}

function formatCheckedTime(value: string): string {
  return new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(
    new Date(value),
  );
}

function countByState(results: DashboardResponse["results"], state: HealthState): number {
  return results.filter((result) => result.state === state).length;
}

export default function App() {
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadDashboard = useCallback(async (forceRefresh = false) => {
    setError(null);
    if (forceRefresh) setRefreshing(true);
    try {
      setDashboard(await fetchDashboard(forceRefresh));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to reach the dashboard service.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadDashboard(), 0);
    return () => window.clearTimeout(timer);
  }, [loadDashboard]);

  const results = dashboard?.results ?? [];
  const activeCount = results.length - countByState(results, "unavailable");
  const downCount = countByState(results, "down");
  const degradedCount = countByState(results, "degraded");

  return (
    <main className="shell">
      <div className="ambient-grid" aria-hidden="true" />
      <header className="masthead">
        <div className="brand-lockup">
          <div className="brand-mark"><Activity size={20} strokeWidth={2.4} /></div>
          <div>
            <p className="eyebrow">Personal systems / {dashboard?.profile ?? "loading"}</p>
            <h1>AIsaac Dashboard</h1>
          </div>
        </div>
        <button className="refresh-button" type="button" onClick={() => void loadDashboard(true)} disabled={refreshing}>
          <RefreshCw size={16} className={refreshing ? "spin" : ""} aria-hidden="true" />
          <span>{refreshing ? "Checking" : "Refresh"}</span>
        </button>
      </header>

      <section className="intro" aria-labelledby="page-title">
        <div>
          <p className="eyebrow">Control room / 01</p>
          <h2 id="page-title">Everything in one <em>glance.</em></h2>
          <p className="intro-copy">A quiet pulse check for the apps that keep the week moving.</p>
        </div>
        <div className="pulse-summary" aria-label="Dashboard summary">
          <div className="pulse-orbit"><span /></div>
          <div>
            <span className="summary-label">Reachable systems</span>
            <strong>{loading ? "--" : `${activeCount - downCount}/${activeCount}`}</strong>
          </div>
        </div>
      </section>

      <section className="summary-row" aria-label="Status summary">
        <div className="summary-cell"><span>Monitored</span><strong>{loading ? "--" : results.length}</strong></div>
        <div className="summary-cell summary-cell-alert"><span>Needs attention</span><strong>{loading ? "--" : downCount + degradedCount}</strong></div>
        <div className="summary-cell"><span>Last sweep</span><strong>{dashboard ? formatRefreshTime(dashboard.refreshed_at) : "--"}</strong></div>
      </section>

      {error && (
        <div className="error-banner" role="alert">
          <WifiOff size={18} aria-hidden="true" />
          <span>{error}</span>
          <button type="button" onClick={() => void loadDashboard(true)}>Try again</button>
        </div>
      )}

      <section className="apps-section" aria-labelledby="apps-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Service registry</p>
            <h2 id="apps-heading">Your applications</h2>
          </div>
          <span className="section-index"><Server size={15} aria-hidden="true" /> {results.length.toString().padStart(2, "0")} tracked</span>
        </div>
        {loading ? (
          <div className="bento-grid loading-grid" aria-label="Loading application statuses">
            {[1, 2, 3, 4].map((item) => <div className="skeleton-card" key={item} />)}
          </div>
        ) : results.length > 0 ? (
          <div className="bento-grid">
            <GlassCard className="overview-card">
              <div className="tile-kicker">System overview</div>
              <div className="overview-value">{activeCount ? `${activeCount - downCount}/${activeCount}` : "--"}</div>
              <p>Reachable systems across the current monitoring profile.</p>
              <div className="overview-stats">
                <div><span>Operational</span><strong>{countByState(results, "up")}</strong></div>
                <div><span>Degraded</span><strong>{degradedCount}</strong></div>
                <div><span>Unavailable</span><strong>{countByState(results, "unavailable")}</strong></div>
              </div>
            </GlassCard>
            {stateOrder.flatMap((state) => results.filter((result) => result.state === state)).map((result, index) => (
              <AppCard key={result.app_id} result={result} index={index} />
            ))}
            <GlassCard className="activity-card">
              <div className="tile-kicker">Recent activity</div>
              <div className="activity-list">
                {results.slice(0, 6).map((result) => (
                  <div className="activity-item" key={result.app_id}>
                    <span className={`activity-dot activity-${result.state}`} />
                    <div><strong>{result.name}</strong><span>{result.detail ?? `${result.state} check completed`}</span></div>
                    <time>{formatCheckedTime(result.checked_at)}</time>
                  </div>
                ))}
              </div>
            </GlassCard>
          </div>
        ) : (
          <div className="empty-state"><ArrowDownRight size={18} /><span>No applications are configured for this profile.</span></div>
        )}
      </section>

      <footer className="footer-note">
        <span>Server-side checks / no private data</span>
        <span>AIsaac Dashboard v0.1</span>
      </footer>
    </main>
  );
}
