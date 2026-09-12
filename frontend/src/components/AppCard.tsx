import { ArrowUpRight, Clock3, Gauge, Radio, ShieldCheck } from "lucide-react";

import type { CheckResult } from "../types";
import { GlassCard } from "./GlassCard";
import { StatusBadge } from "./StatusBadge";

interface AppCardProps {
  result: CheckResult;
  index: number;
}

function formatCheckedAt(value: string): string {
  return new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(
    new Date(value),
  );
}

function formatMetric(value: string | number | boolean): string {
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

export function AppCard({ result, index }: AppCardProps) {
  const metricEntries = Object.entries(result.metrics).slice(0, 3);
  return (
    <GlassCard className={`app-card state-${result.state}`} style={{ "--card-index": index } as React.CSSProperties}>
      <div className="card-topline">
        <span className="card-category">{result.category}</span>
        <StatusBadge state={result.state} compact />
      </div>
      <div className="card-heading">
        <div>
          <h2>{result.name}</h2>
          <p>{result.description}</p>
        </div>
        {result.product_url ? (
          <a className="launch-button" href={result.product_url} target="_blank" rel="noreferrer" aria-label={`Open ${result.name}`}>
            <ArrowUpRight size={18} aria-hidden="true" />
          </a>
        ) : (
          <span className="launch-button launch-button-disabled" aria-hidden="true">
            <ArrowUpRight size={18} />
          </span>
        )}
      </div>
      <div className="card-rule" />
      <div className="card-facts">
        <div className="fact">
          <Clock3 size={15} aria-hidden="true" />
          <span>Checked {formatCheckedAt(result.checked_at)}</span>
        </div>
        <div className="fact">
          <Gauge size={15} aria-hidden="true" />
          <span>{result.response_ms === null ? "No response" : `${result.response_ms} ms`}</span>
        </div>
        {result.readiness && (
          <div className="fact">
            <ShieldCheck size={15} aria-hidden="true" />
            <span>Readiness {result.readiness}</span>
          </div>
        )}
        {result.page_state && (
          <div className="fact">
            <Radio size={15} aria-hidden="true" />
            <span>Page {result.page_state}</span>
          </div>
        )}
        {result.metrics_state && (
          <div className="fact">
            <Gauge size={15} aria-hidden="true" />
            <span>Metrics {result.metrics_state}</span>
          </div>
        )}
        {result.provider_state && (
          <div className="fact">
            <Radio size={15} aria-hidden="true" />
            <span>Provider {result.provider_state}</span>
          </div>
        )}
      </div>
      {result.detail && <p className="card-detail">{result.detail}</p>}
      {metricEntries.length > 0 && (
        <div className="metric-strip">
          {metricEntries.map(([key, value]) => (
            <div className="metric" key={key}>
              <span>{key.replaceAll("_", " ")}</span>
              <strong>{formatMetric(value)}</strong>
            </div>
          ))}
        </div>
      )}
    </GlassCard>
  );
}
