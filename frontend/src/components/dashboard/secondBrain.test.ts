import { describe, expect, it } from "vitest";

import {
  headings,
  infoboxRows,
  linkWikilinks,
  MISSING,
  noteHref,
  obsidianUrl,
  pathFromHref,
  portalLabel,
  slugify,
} from "./secondBrain";
import type { Note } from "../../types";

describe("second brain helpers", () => {
  it("round-trips note paths through hrefs, including spaces and parentheses", () => {
    for (const path of ["wikis/apps/index.md", "knowledge/ai/a b (v2).md"]) {
      expect(pathFromHref(noteHref(path))).toBe(path);
    }
    expect(noteHref("wikis/apps/index.md")).toBe("/knowledge/wikis/apps/index");
    expect(pathFromHref("/elsewhere")).toBeNull();
  });

  it("links resolved wikilinks (case, #heading, |label), marks unresolved, leaves unknown text alone", () => {
    const map = { "app list": "wikis/apps/index.md", nope: null };
    expect(linkWikilinks("[[App List]] [[app list#Setup]] [[app list|the list]] [[Nope]] [[Other]]", map)).toBe(
      "[App List](/knowledge/wikis/apps/index) [app list](/knowledge/wikis/apps/index) " +
        `[the list](/knowledge/wikis/apps/index) [Nope](${MISSING}) Other`,
    );
  });

  it("builds an obsidian deep link without the .md extension", () => {
    expect(obsidianUrl("wikis/apps/index.md")).toBe("obsidian://open?vault=second-brain&file=wikis%2Fapps%2Findex");
  });

  it("extracts h2/h3 headings, skipping fenced code, and slugs them", () => {
    const body = "# Title\n## Method\ntext\n```\n## not a heading\n```\n### [[Gym|The Gym]] `x`";
    expect(headings(body)).toEqual([
      { level: 2, text: "Method", id: "method" },
      { level: 3, text: "The Gym x", id: "the-gym-x" },
    ]);
    expect(slugify("A  b/C!")).toBe("a-b-c");
  });

  it("builds infobox rows, omitting empty fields", () => {
    const note: Note = {
      path: "wikis/apps/index.md",
      folder: "wikis",
      title: "Apps",
      aliases: ["Apps", "app list"],
      status: "approved",
      body: "",
      frontmatter: { type: "wiki-index", updated: "2026-10-02" },
      link_map: {},
      links: [],
      backlinks: [],
      previews: {},
      portal: "wikis/apps",
    };
    expect(infoboxRows(note)).toEqual([
      ["Type", "wiki-index"],
      ["Status", "approved"],
      ["Updated", "2026-10-02"],
      ["Wiki", "apps"],
      ["Also known as", "app list"],
    ]);
    expect(portalLabel("projects")).toBe("projects");
  });
});
