import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { CIEvent } from "../../types";
import { ComEventRow } from "./ComEventRow";
import { EventFilterGroup } from "./EventFilters";

function makeEvent(overrides: Partial<CIEvent>): CIEvent {
  return {
    id: 1,
    app_id: "vinyl",
    repo: "vinyl-api",
    event_type: "push",
    ci_status: "success",
    details: "",
    received_at: "2026-09-25T12:00:00Z",
    notified: true,
    ...overrides,
  };
}

describe("ComEventRow", () => {
  it("renders the repo, event type, and details", () => {
    const { container } = render(
      <ul>
        <ComEventRow event={makeEvent({ repo: "vinyl-api", event_type: "deploy", details: "Deployed v2" })} />
      </ul>,
    );
    expect(within(container).getByText("vinyl-api · deploy")).toBeInTheDocument();
    expect(within(container).getByText("Deployed v2")).toBeInTheDocument();
  });

  it("flags a debounced event", () => {
    const { container } = render(
      <ul>
        <ComEventRow event={makeEvent({ notified: false })} />
      </ul>,
    );
    expect(within(container).getByText(/debounced/)).toBeInTheDocument();
  });
});

describe("EventFilterGroup", () => {
  it("calls onChange with the clicked option", () => {
    const onChange = vi.fn();
    render(
      <EventFilterGroup label="Filter by status" allLabel="All statuses" options={["success", "failure"]} value="all" onChange={onChange} />,
    );
    fireEvent.click(screen.getByText("failure"));
    expect(onChange).toHaveBeenCalledWith("failure");
  });

  it("marks the active option", () => {
    const { container } = render(
      <EventFilterGroup label="Filter by status" allLabel="All statuses" options={["success", "failure"]} value="failure" onChange={vi.fn()} />,
    );
    expect(within(container).getByText("failure")).toHaveClass("active");
  });
});
