import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";

import { Sidebar } from "./Sidebar";

afterEach(cleanup);

// jsdom has no matchMedia, which the theme toggle reads.
window.matchMedia ??= (() => ({ matches: false })) as unknown as typeof window.matchMedia;

function setup() {
  render(
    <MemoryRouter>
      <Sidebar
        status={{ label: "ok", tone: "success" }}
        apps={[{ id: "a", name: "Alpha" }]}
        collapsed={false}
        onToggleCollapsed={() => {}}
      />
    </MemoryRouter>,
  );
}

describe("Sidebar", () => {
  it("lists apps under Applications and toggles the list", async () => {
    setup();
    expect(screen.getByText("Alpha")).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: "Collapse applications" }));
    await waitFor(() => expect(screen.queryByText("Alpha")).toBeNull());
  });
});
