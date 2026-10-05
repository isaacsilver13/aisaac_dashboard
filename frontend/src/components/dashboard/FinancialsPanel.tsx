import { useEffect, useState, type FormEvent } from "react";

import { FinancialsAuthError, fetchFinancials } from "../../api";
import { readToken, writeToken } from "../../token";
import type { ClaudeUsage, CodexUsage, FinancialSnapshot, NeonUsage, ProviderCost, UsageWindow } from "../../types";
import { Badge } from "../primitives/Badge";
import { Card } from "../primitives/Card";
import { EmptyState } from "../primitives/EmptyState";
import { Skeleton } from "../primitives/Skeleton";
import { Stat } from "../primitives/Stat";
import {
  COST_STALE_MS,
  USAGE_STALE_MS,
  formatHours,
  formatResetAt,
  formatTimeUntil,
  formatUsd,
  isStale,
  usageTone,
} from "./financials";

function UsageMeter({ label, window: win, stale }: { label: string; window: UsageWindow; stale: boolean }) {
  const tone = usageTone(win.used_pct);
  return (
    <Card>
      <Stat label={label} value={`${win.used_pct.toFixed(0)}%`} />
      <div
        className={`usage-meter usage-meter-${tone}`}
        role="progressbar"
        aria-label={`${label} usage`}
        aria-valuenow={Math.round(win.used_pct)}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div style={{ width: `${Math.min(100, win.used_pct)}%` }} />
      </div>
      <div className="ui-stat-label" style={{ marginTop: 10 }}>
        Resets in {formatTimeUntil(win.resets_at)} ({formatResetAt(win.resets_at)})
      </div>
      {stale && <Badge tone="warning" style={{ marginTop: 8 }}>Stale</Badge>}
    </Card>
  );
}

function CostCard({ label, cost }: { label: string; cost: ProviderCost | null }) {
  if (!cost) {
    return (
      <Card>
        <Stat label={label} value="--" />
        <div className="ui-stat-label" style={{ marginTop: 10 }}>Not reporting</div>
      </Card>
    );
  }
  const apps = Object.entries(cost.by_app).sort((a, b) => b[1] - a[1]);
  return (
    <Card>
      <Stat label={`${label} · ${cost.period}`} value={formatUsd(cost.total_usd)} />
      <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
        {cost.estimated && <Badge tone="info">Estimate</Badge>}
        {isStale(cost.reported_at, COST_STALE_MS) && <Badge tone="warning">Stale</Badge>}
      </div>
      <ul className="cost-by-app">
        {apps.map(([app, usd]) => (
          <li key={app}>
            <span>{app}</span>
            <span>{formatUsd(usd)}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function NeonCard({ usage }: { usage: NeonUsage | null }) {
  if (!usage) {
    return (
      <Card>
        <Stat label="Neon" value="--" />
        <div className="ui-stat-label" style={{ marginTop: 10 }}>Not reporting</div>
      </Card>
    );
  }
  const apps = Object.entries(usage.by_app).sort((a, b) => b[1] - a[1]);
  return (
    <Card>
      <Stat label={`Neon compute · ${usage.period}`} value={formatHours(usage.total_compute_hours)} />
      {isStale(usage.reported_at, COST_STALE_MS) && (
        <Badge tone="warning" style={{ marginTop: 8 }}>Stale</Badge>
      )}
      <ul className="cost-by-app">
        {apps.map(([app, hours]) => (
          <li key={app}>
            <span>{app}</span>
            <span>{formatHours(hours)}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function ClaudeUsageCards({ usage }: { usage: ClaudeUsage | null }) {
  if (!usage) {
    return (
      <Card>
        <Stat label="Claude usage" value="--" />
        <div className="ui-stat-label" style={{ marginTop: 10 }}>Not reporting</div>
      </Card>
    );
  }
  const stale = isStale(usage.reported_at, USAGE_STALE_MS);
  return (
    <>
      <UsageMeter label="Claude session" window={usage.session} stale={stale} />
      <UsageMeter label="Claude weekly" window={usage.weekly} stale={stale} />
    </>
  );
}

function CodexUsageCards({ usage }: { usage: CodexUsage | null }) {
  if (!usage) {
    return (
      <Card>
        <Stat label="Codex usage" value="--" />
        <div className="ui-stat-label" style={{ marginTop: 10 }}>Not reporting</div>
      </Card>
    );
  }
  const stale = isStale(usage.reported_at, USAGE_STALE_MS);
  return (
    <>
      <UsageMeter label="Codex primary" window={usage.primary} stale={stale} />
      {usage.secondary && <UsageMeter label="Codex secondary" window={usage.secondary} stale={stale} />}
    </>
  );
}

export function FinancialsPanel() {
  const [token, setToken] = useState(readToken);
  const [draft, setDraft] = useState("");
  const [snapshot, setSnapshot] = useState<FinancialSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    fetchFinancials(token)
      .then((next) => {
        if (cancelled) return;
        setSnapshot(next);
        setError(null);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof FinancialsAuthError) {
          writeToken("");
          setToken("");
          setError("That token was not accepted.");
        } else {
          setError(err instanceof Error ? err.message : "Could not load financial figures.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  function submit(event: FormEvent) {
    event.preventDefault();
    const value = draft.trim();
    if (!value) return;
    writeToken(value);
    setToken(value);
    setDraft("");
  }

  if (!token) {
    return (
      <Card>
        <form className="token-form" onSubmit={submit}>
          <label className="ui-stat-label" htmlFor="dashboard-token">Access token for usage and costs</label>
          <input
            id="dashboard-token"
            type="password"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            autoComplete="off"
          />
          <button className="refresh-button" type="submit">Unlock</button>
          {error && <span role="alert" className="ui-stat-label">{error}</span>}
        </form>
      </Card>
    );
  }

  if (!snapshot) {
    return error ? <EmptyState message={error} /> : <Skeleton height={140} />;
  }

  return (
    <section aria-label="Usage and costs" className="financials-row">
      <ClaudeUsageCards usage={snapshot.claude} />
      <CodexUsageCards usage={snapshot.codex} />
      <NeonCard usage={snapshot.neon} />
      <CostCard label="Fly.io" cost={snapshot.fly} />
    </section>
  );
}
