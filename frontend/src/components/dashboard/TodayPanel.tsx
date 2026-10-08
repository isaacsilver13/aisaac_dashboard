import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { fetchShoes, fetchSports } from "../../api";
import { centralTimestamp } from "../../time";
import { readToken } from "../../token";
import type { ShoeListing, SportsEvent } from "../../types";
import { Card } from "../primitives/Card";

const DAY_MS = 24 * 60 * 60 * 1000;
const line = (e: SportsEvent) => `${e.away} at ${e.home}`;

/** Compact "Today" card: Chicago-team games and shoe changes from stored snapshots (never refreshes). */
export function TodayPanel() {
  const [token] = useState(readToken);
  const [games, setGames] = useState<SportsEvent[]>([]);
  const [changes, setChanges] = useState<ShoeListing[]>([]);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    fetchSports(token)
      .then((s) => !cancelled && setGames(s.priority))
      .catch(() => undefined);
    fetchShoes(token)
      .then((s) => !cancelled && setChanges(s.listings.filter((l) => l.changed_at && Date.now() - new Date(l.changed_at).getTime() < DAY_MS)))
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [token]);

  if (games.length === 0 && changes.length === 0) return null;
  return (
    <Card aria-label="Today">
      <h2>Today</h2>
      {games.length > 0 && (
        <ul>
          {games.slice(0, 5).map((e) => (
            <li key={e.id}>
              <Link to="/sports">{line(e)}</Link> · {centralTimestamp(e.start_at)}
            </li>
          ))}
        </ul>
      )}
      {changes.length > 0 && (
        <ul>
          {changes.slice(0, 5).map((l) => (
            <li key={l.id}>
              <Link to="/shoes">{l.title}</Link> · {l.price === null ? "price n/a" : `$${l.price.toFixed(2)}`}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
