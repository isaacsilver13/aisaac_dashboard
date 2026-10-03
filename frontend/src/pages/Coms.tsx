import { useCallback, useMemo, useState } from "react";
import { Refresh } from "iconoir-react";

import { fetchComsEvents } from "../api";
import { ComEventRow } from "../components/coms/ComEventRow";
import { EventFilterGroup } from "../components/coms/EventFilters";
import { Card } from "../components/primitives/Card";
import { EmptyState } from "../components/primitives/EmptyState";
import { ErrorState } from "../components/primitives/ErrorState";
import { PageHeader } from "../components/primitives/PageHeader";
import { Skeleton } from "../components/primitives/Skeleton";
import { useAsyncData } from "../hooks/useAsyncData";
import type { CiStatus } from "../types";

export default function Coms() {
  const loadEvents = useCallback(() => fetchComsEvents(), []);
  const { data: events, loading, refreshing, error, reload } = useAsyncData(loadEvents);

  const [statusFilter, setStatusFilter] = useState<CiStatus | "all">("all");
  const [typeFilter, setTypeFilter] = useState<string>("all");

  const allEvents = useMemo(() => events ?? [], [events]);
  const statuses = useMemo(() => Array.from(new Set(allEvents.map((event) => event.ci_status))), [allEvents]);
  const eventTypes = useMemo(() => Array.from(new Set(allEvents.map((event) => event.event_type))), [allEvents]);

  const filteredEvents = allEvents.filter(
    (event) =>
      (statusFilter === "all" || event.ci_status === statusFilter) &&
      (typeFilter === "all" || event.event_type === typeFilter),
  );

  return (
    <>
      <PageHeader
        title="Coms"
        description="Push notifications received from tracked repos."
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
        <div className="task-groups" aria-label="Loading Coms events">
          <Skeleton height={220} />
        </div>
      ) : allEvents.length > 0 ? (
        <>
          {(statuses.length > 1 || eventTypes.length > 1) && (
            <div className="coms-filters">
              {statuses.length > 1 && (
                <EventFilterGroup
                  label="Filter by status"
                  allLabel="All statuses"
                  options={statuses}
                  value={statusFilter}
                  onChange={setStatusFilter}
                />
              )}
              {eventTypes.length > 1 && (
                <EventFilterGroup
                  label="Filter by event type"
                  allLabel="All types"
                  options={eventTypes}
                  value={typeFilter}
                  onChange={setTypeFilter}
                />
              )}
            </div>
          )}

          {filteredEvents.length > 0 ? (
            <div className="task-groups">
              <Card className="task-group">
                <ul className="task-list">
                  {filteredEvents.map((event) => (
                    <ComEventRow key={event.id} event={event} />
                  ))}
                </ul>
              </Card>
            </div>
          ) : (
            <EmptyState message="No events match the selected filters." />
          )}
        </>
      ) : (
        <EmptyState message="No Coms events recorded yet." />
      )}
    </>
  );
}
