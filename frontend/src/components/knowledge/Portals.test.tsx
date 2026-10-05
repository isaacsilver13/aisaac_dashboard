import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";

import type { NoteListItem, Portal } from "../../types";
import { Landing, PortalPage } from "./Portals";

afterEach(cleanup);

const portals: Portal[] = [
  { id: "wikis/apps", title: "Apps Wiki", count: 2, index_path: "wikis/apps/index.md", description: "Map of apps." },
  { id: "projects", title: "Projects", count: 1, index_path: null, description: "" },
];
const note = (path: string, title: string, updated: string | null = null): NoteListItem => ({
  path,
  folder: path.split("/")[0],
  title,
  aliases: [],
  status: null,
  updated,
});
const notes = [
  note("wikis/apps/index.md", "Apps Wiki", "2026-10-02"),
  note("wikis/apps/zeta.md", "Zeta"),
  note("projects/p.md", "P"),
];
const wrap = (ui: ReactElement) => render(<MemoryRouter>{ui}</MemoryRouter>);

describe("Portals", () => {
  it("lists portal cards and filters notes by search", () => {
    wrap(<Landing portals={portals} notes={notes} />);
    expect(screen.getByRole("link", { name: /Apps Wiki 2 articles/ })).toHaveAttribute(
      "href",
      "/knowledge/wikis/apps",
    );
    expect(screen.getByText("Map of apps.")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "zeta" } });
    expect(screen.getByRole("link", { name: "Zeta" })).toBeInTheDocument();
  });

  it("shows a portal's articles A-Z", () => {
    wrap(<PortalPage portal={portals[0]} notes={notes} />);
    const links = screen.getAllByRole("link").map((l) => l.textContent);
    expect(links.indexOf("Apps Wiki")).toBeLessThan(links.indexOf("Zeta"));
    expect(links).not.toContain("P");
  });

  it("shows an empty state for a portal with no articles", () => {
    wrap(<PortalPage portal={{ ...portals[1], count: 0 }} notes={[]} />);
    expect(screen.getByText(/No articles/)).toBeInTheDocument();
  });
});
