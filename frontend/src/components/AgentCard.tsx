import { Clock3 } from "lucide-react";

import type { AgentSummary } from "../types";
import { GlassCard } from "./GlassCard";

interface AgentCardProps {
  agent: AgentSummary;
  index: number;
}

function formatLastRun(value: string | null): string {
  if (!value) return "Never run";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export function AgentCard({ agent, index }: AgentCardProps) {
  return (
    <GlassCard className="agent-card" style={{ "--card-index": index } as React.CSSProperties}>
      <div className="card-topline">
        <span className="card-category">{agent.domain}</span>
      </div>
      <div className="card-heading">
        <div>
          <h2>{agent.name}</h2>
          <p>{agent.description}</p>
        </div>
      </div>
      <div className="card-rule" />
      {agent.scope.length > 0 && (
        <div className="agent-scope">
          {agent.scope.map((appId) => (
            <span className="agent-scope-tag" key={appId}>{appId}</span>
          ))}
        </div>
      )}
      <div className="card-facts">
        <div className="fact">
          <Clock3 size={15} aria-hidden="true" />
          <span>Last run: {formatLastRun(agent.last_run_at)}</span>
        </div>
      </div>
      {agent.last_run_note && <p className="card-detail">{agent.last_run_note}</p>}
    </GlassCard>
  );
}
