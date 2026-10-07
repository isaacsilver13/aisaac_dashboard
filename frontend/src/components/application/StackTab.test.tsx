import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { StackTab } from "./StackTab";

afterEach(cleanup);

describe("StackTab", () => {
  it("maps the known production stack without exposing credentials", () => {
    render(<StackTab appId="vinyl" />);

    expect(screen.getByRole("heading", { name: "Operational stack map" })).toBeTruthy();
    expect(screen.getByText("Fly · vinyl-api")).toBeTruthy();
    expect(screen.getByText("Public health, readiness, and metrics checks")).toBeTruthy();
  });

  it("makes the push-only NBA monitoring boundary explicit", () => {
    render(<StackTab appId="nba-prediction" />);

    expect(screen.getByText("Push heartbeat only; no public health probe")).toBeTruthy();
  });

  it("handles an unregistered application", () => {
    render(<StackTab appId="unknown" />);

    expect(screen.getByText("No stack map is available for this application.")).toBeTruthy();
  });
});
