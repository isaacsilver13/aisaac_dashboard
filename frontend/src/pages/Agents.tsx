import { fetchAgents } from "../api";
import { AgentCard } from "../components/AgentCard";
import { EmptyState } from "../components/primitives/EmptyState";
import { ErrorState } from "../components/primitives/ErrorState";
import { PageHeader } from "../components/primitives/PageHeader";
import { Skeleton } from "../components/primitives/Skeleton";
import { useAsyncData } from "../hooks/useAsyncData";

export default function Agents() {
  const { data: agents, loading, refreshing, error, reload } = useAsyncData(fetchAgents);

  return (
    <>
      <PageHeader
        title="Agents"
        description="Named, scoped Claude Code subagents you invoke on demand — not processes running on their own. Nothing here calls a model until you run it yourself."
      />

      {error ? (
        <ErrorState message={error} onRetry={() => void reload(true)} retrying={refreshing} />
      ) : loading ? (
        <div className="agent-list" aria-label="Loading agent roster">
          {[1, 2, 3, 4].map((item) => <Skeleton height={120} key={item} />)}
        </div>
      ) : agents && agents.length > 0 ? (
        <div className="agent-list">
          {agents.map((agent) => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
        </div>
      ) : (
        <EmptyState message="No agents are registered yet." />
      )}
    </>
  );
}
