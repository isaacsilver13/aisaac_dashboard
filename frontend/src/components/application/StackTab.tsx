import { Card } from "../primitives/Card";
import { EmptyState } from "../primitives/EmptyState";

interface FlowNode {
  label: string;
  detail: string;
}

interface StackFlow {
  description: string;
  nodes: FlowNode[];
  monitoring: string;
}

const FLOWS: Record<string, StackFlow> = {
  vinyl: {
    description: "The catalog UI and API run as separate Fly applications; the API owns the persistent collection data.",
    nodes: [
      { label: "Browser", detail: "Catalog UI" },
      { label: "Fly · vinyl-catalog", detail: "Streamlit" },
      { label: "Fly · vinyl-api", detail: "FastAPI" },
      { label: "Fly volume", detail: "SQLite" },
    ],
    monitoring: "Public health, readiness, and metrics checks",
  },
  "nfl-confidence": {
    description: "The deployed host serves the React experience and FastAPI endpoints from one Fly application.",
    nodes: [
      { label: "Browser", detail: "Web experience" },
      { label: "Fly · nfl-confidence-web", detail: "React + FastAPI" },
      { label: "PostgreSQL", detail: "Application data" },
    ],
    monitoring: "Public health, readiness, and metrics checks",
  },
  "betting-aggregator": {
    description: "One Fly host serves the UI and API, which combines provider responses with its application database and cache.",
    nodes: [
      { label: "Browser", detail: "Odds comparison" },
      { label: "Fly · betting-aggregator-api", detail: "React + FastAPI" },
      { label: "Odds provider", detail: "External API" },
      { label: "Neon", detail: "Postgres + cache state" },
    ],
    monitoring: "Public health and allowlisted metrics checks",
  },
  "nba-prediction": {
    description: "This is intentionally local-only: its dashboard and experiments do not expose a production product endpoint.",
    nodes: [
      { label: "Local browser", detail: "Streamlit dashboard" },
      { label: "Python experiments", detail: "Models + backtests" },
      { label: "Local data", detail: "Datasets + artifacts" },
    ],
    monitoring: "Push heartbeat only; no public health probe",
  },
  "gym-tracker": {
    description: "The production Fly application serves the workout interface and its API from the same deployed host.",
    nodes: [
      { label: "Browser", detail: "Workout interface" },
      { label: "Fly · isilver-gym-tracker-api", detail: "UI + API" },
      { label: "Application data", detail: "Private system boundary" },
    ],
    monitoring: "Public health, readiness, and metrics checks",
  },
  "portfolio-analysis": {
    description: "The deployed application owns private portfolio data; AIsaac reads only a scoped aggregate health-metrics endpoint.",
    nodes: [
      { label: "Browser", detail: "Portfolio interface" },
      { label: "Fly · portfolio-analysis-api", detail: "UI + API" },
      { label: "Private portfolio data", detail: "Not read by AIsaac" },
    ],
    monitoring: "Health, readiness, and scoped aggregate metrics checks",
  },
};

export function StackTab({ appId }: { appId: string }) {
  const flow = FLOWS[appId];
  if (!flow) return <EmptyState message="No stack map is available for this application." />;

  return (
    <section aria-labelledby="stack-map-heading">
      <div className="stack-tab-heading">
        <div>
          <h2 id="stack-map-heading">Operational stack map</h2>
          <p>{flow.description}</p>
        </div>
      </div>
      <Card className="stack-flow-card">
        <ol className="stack-flow" aria-label="Request flow">
          {flow.nodes.map((node, index) => (
            <li key={node.label} className="stack-flow-step">
              <div className="stack-flow-node">
                <span>{node.label}</span>
                <strong>{node.detail}</strong>
              </div>
              {index < flow.nodes.length - 1 && <span className="stack-flow-arrow" aria-hidden="true">→</span>}
            </li>
          ))}
        </ol>
        <div className="stack-monitoring">
          <span>AIsaac Dashboard</span>
          <strong>{flow.monitoring}</strong>
        </div>
      </Card>
    </section>
  );
}
