# Knowledge tab: Obsidian-style, Wikipedia-organized viewer

## Goal
Make the Knowledge tab feel like Obsidian (wikilinks, backlinks, graph, hover previews)
and read like Wikipedia (one article per topic, portals, categories).

## Decisions (agreed)
- "Embed Obsidian" = a native React, **read-only** Obsidian-style viewer. Not an iframe of
  real Obsidian, not Obsidian Publish.
- "Article per topic" = **presentation only**. Existing `wikis/<topic>/*.md` notes are the
  articles; each wiki's `index.md` is its portal. Vault content is not edited or restructured.
- No new infra. Existing push pipeline, `INTERNAL_REPORT_SECRET` write path and
  `DASHBOARD_READ_TOKEN` read path are unchanged. Reads never touch the filesystem.

## Non-goals
Editing in the browser, real Obsidian plugins, vault restructuring or stub drafting,
full-text ranking beyond the current `LIKE` search.

## Design

### 1. Data
- `scripts/second_brain_push.py`: keep full frontmatter (`type`, `wiki`, `updated`, `tags`,
  plus existing title/status/aliases) and resolve each note's outgoing wikilinks to note
  paths at push time (match title, alias or filename; unresolved targets are kept as
  `unresolved`).
- `second_brain_store.py`: add `frontmatter` (JSON) and `links` (JSON, resolved paths +
  unresolved names) columns. Schema migration must tolerate an existing DB
  (`ALTER TABLE ... ADD COLUMN` guarded, or recreate since each sync replaces all rows).
- `get_note(path)` additionally returns `links` and `backlinks` (notes whose `links`
  contain this path), plus short previews (first paragraph, ~200 chars) for linked notes.
- New `GET /api/v1/second-brain/graph` -> `{nodes: [{path,title,folder,wiki}], edges: [[src,dst]]}`,
  behind `DASHBOARD_READ_TOKEN`.
- `meta` gains per-wiki descriptions taken from each `index.md` lead paragraph.

### 2. Article view (replaces the plain Markdown card)
Title and "from the {wiki} wiki" line with updated date; floating infobox from frontmatter;
auto table of contents from headings; `[S:]` source tags and callouts rendered; "See also"
(outgoing links); "What links here" (backlinks); category chips; hover preview on wikilinks;
unresolved wikilinks rendered as red links.

### 3. Browse views
- Landing: portal grid (one card per wiki: count, description), search box, recently updated.
- Portal page: `index.md` as lead, then A-Z article list.
- Graph view: whole vault or current article's neighborhood; small SVG force layout
  (`d3-force` only if hand-rolling exceeds ~80 lines).
- Existing sortable `Table` kept as "All pages".

### 4. Routing
`/knowledge/:wiki/:slug` for articles, `/knowledge/:wiki` for portals. Legacy `?note=path`
URLs redirect. Tokens/unlock flow unchanged.

### 5. Testing
- pytest: link resolution (title/alias/filename/unresolved), backlinks, graph endpoint,
  migration against a pre-existing DB.
- vitest: TOC builder, wikilink resolution, infobox rendering, red links.
- Manual: run `second_brain_push.py --dry-run` data locally and check desktop and mobile
  widths in a browser.

## Risks
- Wikilink resolution ambiguity (duplicate titles/aliases): first match by folder priority
  `wikis` > `knowledge` > `projects` > `questions`; ambiguous cases logged in push output.
- Payload size grows with links/previews; sync is already a single 60s POST, ~hundreds of notes.

## Deviations decided during planning
1. Wikilinks are resolved in `second_brain_store.replace_all` (at sync time) instead of the push script: one resolver, only knows synced notes; the script just forwards frontmatter (and now scans it for secrets).
2. Routing is a single splat `/knowledge/*` (note path without `.md`; a wiki folder id like `wikis/apps` is the portal), because `knowledge/` has nested subfolders.
3. Dropped as YAGNI: callout rendering, `[S:]` tag styling, `tags` (none exist in the vault).
4. Added `GET /api/v1/second-brain/portals` for portal cards.
