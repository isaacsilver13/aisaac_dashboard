import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { AgentSummary } from "../types";
import { AgentCard } from "./AgentCard";

function makeAgent(overrides: Partial<AgentSummary>): AgentSummary {
  return {
    id: "agent",
    name: "Agent",
    domain: "domain",
    description: "Does things.",
    scope: [],
    last_run_at: null,
    last_run_note: null,
    ...overrides,
  };
}

describe("AgentCard", () => {
  it("renders the agent's name, domain, and description", () => {
    render(<AgentCard agent={makeAgent({ name: "Runbook Writer", domain: "ops", description: "Writes runbooks." })} />);
    expect(screen.getByText("Runbook Writer")).toBeInTheDocument();
    expect(screen.getByText("ops")).toBeInTheDocument();
    expect(screen.getByText("Writes runbooks.")).toBeInTheDocument();
  });

  it("shows 'Never run' when the agent has no last run", () => {
    const { container } = render(<AgentCard agent={makeAgent({ last_run_at: null })} />);
    expect(within(container).getByText("Never run")).toBeInTheDocument();
  });

  it("lists scope tags when present", () => {
    render(<AgentCard agent={makeAgent({ scope: ["vinyl", "gym-tracker"] })} />);
    expect(screen.getByText("vinyl")).toBeInTheDocument();
    expect(screen.getByText("gym-tracker")).toBeInTheDocument();
  });

  it("shows the last run note when present", () => {
    render(<AgentCard agent={makeAgent({ last_run_note: "Resolved a stale incident." })} />);
    expect(screen.getByText("Resolved a stale incident.")).toBeInTheDocument();
  });
});
