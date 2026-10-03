import { describe, expect, it } from "vitest";

import { linkWikilinks, obsidianUrl } from "./secondBrain";

const notes = [{ path: "wikis/apps/index.md", folder: "wikis", title: "Apps", aliases: ["Apps", "app list"], status: null }];

describe("second brain helpers", () => {
  it("links resolvable wikilinks (by title or alias, with label) and flattens unresolved ones", () => {
    expect(linkWikilinks("[[Apps]] [[app list|the list]] [[Nope]]", notes)).toBe(
      "[Apps](?note=wikis%2Fapps%2Findex.md) [the list](?note=wikis%2Fapps%2Findex.md) Nope",
    );
  });

  it("builds an obsidian deep link without the .md extension", () => {
    expect(obsidianUrl("wikis/apps/index.md")).toBe("obsidian://open?vault=second-brain&file=wikis%2Fapps%2Findex");
  });
});
