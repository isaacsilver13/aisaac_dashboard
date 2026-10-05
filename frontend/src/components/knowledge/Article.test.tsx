import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";

import type { Note } from "../../types";
import { Article } from "./Article";

afterEach(cleanup);

const base: Note = {
  path: "wikis/apps/index.md",
  folder: "wikis",
  title: "Apps Wiki",
  aliases: ["Apps Wiki", "app list"],
  status: "approved",
  frontmatter: { updated: "2026-10-02" },
  portal: "wikis/apps",
  body: "# Apps\n\nLead.\n\n## One\nSee [[Gym Tracker]] and [[Nope]].\n\n## Two\nx\n\n## Three\ny",
  link_map: { "gym tracker": "projects/gym-tracker.md", nope: null },
  links: [{ path: "projects/gym-tracker.md", title: "Gym Tracker", folder: "projects" }],
  backlinks: [{ path: "projects/other.md", title: "Other", folder: "projects" }],
  previews: { "projects/gym-tracker.md": "A gym app." },
};
const renderIt = (note: Note) =>
  render(
    <MemoryRouter>
      <Article note={note} />
    </MemoryRouter>,
  );

describe("Article", () => {
  it("renders infobox, TOC, linked and red wikilinks, hover preview, see-also and backlinks", () => {
    renderIt(base);
    expect(screen.getByRole("heading", { level: 1, name: "Apps Wiki" })).toBeInTheDocument();
    expect(screen.getByText("2026-10-02")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "One" })).toHaveAttribute("href", "#one");
    expect(screen.getAllByRole("link", { name: "Gym Tracker" })[0]).toHaveAttribute(
      "href",
      "/knowledge/projects/gym-tracker",
    );
    expect(screen.getByText("A gym app.")).toBeInTheDocument();
    expect(screen.getByText("Nope")).toHaveClass("wiki-redlink");
    expect(screen.getByRole("heading", { name: "See also" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Other" })).toHaveAttribute("href", "/knowledge/projects/other");
  });

  it("omits see-also, backlinks and TOC when there is nothing to show", () => {
    renderIt({ ...base, body: "", links: [], backlinks: [], link_map: {}, frontmatter: {}, aliases: [] });
    expect(screen.queryByRole("heading", { name: "See also" })).toBeNull();
    expect(screen.queryByRole("heading", { name: "What links here" })).toBeNull();
    expect(screen.queryByText("Contents")).toBeNull();
  });
});
