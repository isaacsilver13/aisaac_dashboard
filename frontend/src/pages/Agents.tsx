import { useCallback, useEffect, useState } from "react";
import { WifiOff } from "lucide-react";

import { fetchAgents } from "../api";
import { AgentCard } from "../components/AgentCard";
import type { AgentSummary } from "../types";

export default function Agents() {
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setError(null);
    try {
      setAgents(await fetchAgents());
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

  return (
    <section className="apps-section" aria-labelledby="agents-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Domain managers</p>
          <h2 id="agents-heading">Agents</h2>
        </div>
      </div>
      <p className="intro-copy" style={{ marginBottom: 32 }}>
        Named, scoped Claude Code subagents you invoke on demand — not processes running on their
        own. Nothing here calls a model until you run it yourself.
      </p>
      {error && (
        <div className="error-banner" role="alert">
          <WifiOff size={18} aria-hidden="true" />
          <span>{error}</span>
          <button type="button" onClick={() => void load()}>Try again</button>
        </div>
      )}
      {loading ? (
        <div className="bento-grid loading-grid" aria-label="Loading agent roster">
          {[1, 2, 3, 4].map((item) => <div className="skeleton-card" key={item} />)}
        </div>
      ) : (
        <div className="bento-grid">
          {agents.map((agent, index) => (
            <AgentCard key={agent.id} agent={agent} index={index} />
          ))}
        </div>
      )}
    </section>
  );
}
