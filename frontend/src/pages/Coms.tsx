import { useCallback, useEffect, useState } from "react";
import { RefreshCw, WifiOff } from "lucide-react";

import { fetchComsEvents } from "../api";
import { CiStatusBadge } from "../components/CiStatusBadge";
import { GlassCard } from "../components/GlassCard";
import type { CIEvent } from "../types";

function formatReceivedAt(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

export default function Coms() {
  const [events, setEvents] = useState<CIEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async (forceRefresh = false) => {
    setError(null);
    if (forceRefresh) setRefreshing(true);
    try {
      setEvents(await fetchComsEvents());
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
    <section className="apps-section" aria-labelledby="coms-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Push notifications</p>
          <h2 id="coms-heading">Coms</h2>
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
        <div className="bento-grid loading-grid" aria-label="Loading Coms events">
          {[1, 2, 3].map((item) => <div className="skeleton-card" key={item} />)}
        </div>
      ) : events.length > 0 ? (
        <div className="task-groups">
          <GlassCard className="task-group">
            <ul className="task-list">
              {events.map((event) => (
                <li className="task-item" key={event.id}>
                  <CiStatusBadge status={event.ci_status} />
                  <span>
                    {event.repo} · {event.event_type}
                  </span>
                  {event.details && <span className="card-detail">{event.details}</span>}
                  <span className="task-meta">
                    {formatReceivedAt(event.received_at)}
                    {!event.notified ? " · debounced" : ""}
                  </span>
                </li>
              ))}
            </ul>
          </GlassCard>
        </div>
      ) : (
        <div className="empty-state"><span>No Coms events recorded yet.</span></div>
      )}
    </section>
  );
}
