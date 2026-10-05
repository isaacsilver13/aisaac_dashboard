import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MobileDrawer } from "./MobileDrawer";

afterEach(cleanup);

describe("MobileDrawer", () => {
  it("keeps monitored application links available in the mobile navigation", () => {
    render(
      <MemoryRouter>
        <MobileDrawer open onClose={vi.fn()} apps={[{ id: "vinyl", name: "Vinyl Catalog" }]} />
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: "Vinyl Catalog" })).toHaveAttribute(
      "href",
      "/applications/vinyl/overview",
    );
  });
});
