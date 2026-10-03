import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { fetchSecondBrainSummary } from "../../api";
import { readToken } from "../../token";
import type { SecondBrainSummary } from "../../types";
import { Badge } from "../primitives/Badge";
import { Card } from "../primitives/Card";
import { Stat } from "../primitives/Stat";
import { obsidianUrl } from "./secondBrain";

/** Vault status card. Needs the same dashboard token as the financials panel; shows nothing until set. */
export function SecondBrainPanel() {
  const [token] = useState(readToken);
  const [summary, setSummary] = useState<SecondBrainSummary | null>(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    fetchSecondBrainSummary(token)
      .then((next) => !cancelled && setSummary(next))
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [token]);

  if (!summary) return null;
  const total = Object.values(summary.counts).reduce((a, b) => a + b, 0);
  return (
    <Card aria-label="Second brain">
      <Stat label="Second brain · notes" value={String(total)} />
      <ul className="cost-by-app">
        {Object.entries(summary.counts).map(([folder, n]) => (
          <li key={folder}>
            <span>{folder}</span>
            <span>{n}</span>
          </li>
        ))}
      </ul>
      <div style={{ display: "flex", gap: 6, marginTop: 8, flexWrap: "wrap" }}>
        {!!summary.drafts && <Badge tone="warning">{summary.drafts} drafts</Badge>}
        {!!summary.broken_links && <Badge tone="warning">{summary.broken_links} broken links</Badge>}
      </div>
      <div className="ui-stat-label" style={{ marginTop: 10 }}>
        {summary.last_commit ?? "no commit info"}
      </div>
      <div className="ui-stat-label" style={{ marginTop: 6, display: "flex", gap: 12 }}>
        <Link to="/second-brain">Browse wikis</Link>
        <a href={obsidianUrl("Home.md")}>Open in Obsidian</a>
      </div>
    </Card>
  );
}
