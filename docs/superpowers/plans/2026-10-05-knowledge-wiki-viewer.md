# Knowledge Wiki Viewer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the Knowledge tab into an Obsidian-style, Wikipedia-organized read-only viewer (articles, infobox, TOC, backlinks, hover previews, portals, graph).

**Architecture:** The backend store resolves wikilinks once at sync time into a `links` table plus a per-note `link_map`, and serves article, portal and graph payloads. The React page is split into small components (Article, Portals, Graph) behind a single `/knowledge/*` splat route. Vault content and the push/auth model are unchanged.

**Tech Stack:** FastAPI + SQLite (pytest), React + react-router + react-markdown (vitest + Testing Library). No new dependencies.

**Spec:** `docs/superpowers/specs/2026-10-05-knowledge-wiki-viewer-design.md`

## Global Constraints

- Read-only: the dashboard never writes to the vault; sync stays `POST /internal/second-brain/sync` (`INTERNAL_REPORT_SECRET`), reads stay behind `DASHBOARD_READ_TOKEN`.
- Reads never touch the filesystem; paths are only used as DB keys.
- `NoteIn.path` pattern `^(wikis|knowledge|projects|questions)/.+\.md$` is unchanged.
- Icons: Iconoir only. Tokens from `frontend/src/theme/theme.css` (`--bg --surface --subtle --hover --border --text --text-muted --accent --error`); no zebra stripes or vertical borders in lists; lists use `components/primitives/Table`.
- Wikilink resolution priority on duplicate names: `wikis` > `knowledge` > `projects` > `questions`.
- Frontend lint (`npm run lint`), build (`npm run build`), tests (`npm run test`) and backend `pytest` + `ruff check .` must pass after every task.
- Work on branch `feat/knowledge-wiki-viewer`. Do not stage the untracked `aisaac-claude-handoff.md`.

## Deviations from the spec (decided while planning, all smaller than the spec)

1. Wikilinks are resolved in `second_brain_store.replace_all` (at sync time) instead of in the push script: one resolver, only knows synced notes, and the script just forwards frontmatter.
2. Routing is a single splat `/knowledge/*` (note path without `.md`; a wiki folder id like `wikis/apps` is the portal) because `knowledge/` has nested subfolders and does not fit `:wiki/:slug`.
3. Dropped as YAGNI: callout rendering (2 uses in the vault), `[S:]` source-tag styling, `tags` (the vault has none). Wikis' categories come from folder path.
4. Added `GET /api/v1/second-brain/portals` (portal cards need counts and a lead blurb).

## Review Focus

- Note with no wikilinks / empty body: article renders with no empty "See also" / "What links here" sections.
- Wikilink with different case, `#heading` suffix or `|label`: resolves to the same note.
- Note path with spaces or parentheses: route href round-trips back to the exact path.
- Production DB still on the old schema before the first re-sync: endpoints return 200 with empty links, not 500.
- Mistyped URL or a portal with no `index.md`: friendly empty state, not a crash.

---

### Task 1: Backend store, endpoints and push-script frontmatter

**Files:**
- Modify: `backend/app/second_brain_store.py`
- Modify: `backend/app/schemas.py:219-225` (`NoteIn`)
- Modify: `backend/app/main.py:333-343`
- Modify: `scripts/second_brain_push.py:45-61`
- Test: `backend/tests/test_second_brain.py`, `backend/tests/test_second_brain_push.py`

**Interfaces:**
- Produces (store): `portal_of(path: str) -> str`, `portals() -> list[dict]`, `graph() -> dict`, extended `get_note(path)` and `list_notes(...)`.
- `get_note(path)` returns: `path, folder, title, aliases, status, body, frontmatter: dict[str,str], link_map: dict[str, str|None], links: list[Ref], backlinks: list[Ref], previews: dict[str,str], portal: str`, where `Ref = {path, title, folder}` and `link_map` keys are lowercased wikilink target text (a `None` value = unresolved).
- `list_notes` items gain `updated: str|None`.
- `portals()` items: `{id, title, count, index_path: str|None, description: str}`.
- `graph()` returns `{nodes: [{path,title,folder}], edges: [[src,dst]]}`.
- New routes: `GET /api/v1/second-brain/portals`, `GET /api/v1/second-brain/graph`.

- [ ] **Step 1: Create the branch**

```bash
git -C C:/Users/justj/nba_prediction/repos/aisaac_dashboard checkout -b feat/knowledge-wiki-viewer
```

- [ ] **Step 2: Write the failing backend tests**

Append to `backend/tests/test_second_brain.py`:

```python
import sqlite3

APPS = {
    "path": "wikis/apps/index.md",
    "folder": "wikis",
    "title": "Apps Wiki",
    "aliases": ["Apps Wiki"],
    "status": "approved",
    "frontmatter": {"type": "wiki-index", "updated": "2026-10-02"},
    "body": "# Apps\n\nMap of apps. See [[Gym Tracker|gym]], [[gym tracker#Setup]], [[Nope]] and [[Apps Wiki]].",
}
GYM = {
    "path": "projects/gym-tracker.md",
    "folder": "projects",
    "title": "Gym Tracker",
    "aliases": ["Gym Tracker"],
    "status": "active",
    "frontmatter": {},
    "body": "# Gym\n\nBack to [[Apps Wiki]].",
}
LONE = {**GYM, "path": "questions/lone.md", "folder": "questions", "title": "Lone", "aliases": [], "body": ""}


def _api(*notes):
    assert _sync({"meta": {}, "notes": list(notes)}).status_code == 204


def test_links_backlinks_unresolved_and_previews():
    _api(APPS, GYM)
    note = _get("/api/v1/second-brain/notes/wikis/apps/index.md").json()
    assert note["link_map"] == {
        "gym tracker": GYM["path"],
        "nope": None,
        "apps wiki": APPS["path"],
    }
    assert [r["path"] for r in note["links"]] == [GYM["path"]]  # self-link excluded
    assert [r["path"] for r in note["backlinks"]] == [GYM["path"]]
    assert note["previews"][GYM["path"]] == "Back to Apps Wiki."
    assert note["frontmatter"]["updated"] == "2026-10-02"
    assert note["portal"] == "wikis/apps"


def test_note_without_links_has_empty_lists():
    _api(LONE)
    note = _get("/api/v1/second-brain/notes/questions/lone.md").json()
    assert note["links"] == [] and note["backlinks"] == [] and note["link_map"] == {}


def test_duplicate_names_prefer_wikis_over_projects():
    clash = {**GYM, "path": "wikis/apps/gym.md", "folder": "wikis", "title": "Gym Tracker", "body": ""}
    _api(GYM, clash, APPS)
    note = _get("/api/v1/second-brain/notes/wikis/apps/index.md").json()
    assert note["link_map"]["gym tracker"] == "wikis/apps/gym.md"


def test_graph_portals_and_list_updated():
    _api(APPS, GYM, LONE)
    g = _get("/api/v1/second-brain/graph").json()
    assert {n["path"] for n in g["nodes"]} == {APPS["path"], GYM["path"], LONE["path"]}
    assert sorted(g["edges"]) == [[APPS["path"], GYM["path"]], [GYM["path"], APPS["path"]]]
    ids = {p["id"]: p for p in _get("/api/v1/second-brain/portals").json()}
    assert ids["wikis/apps"]["index_path"] == APPS["path"]
    assert ids["wikis/apps"]["title"] == "Apps Wiki" and ids["wikis/apps"]["count"] == 1
    assert ids["wikis/apps"]["description"].startswith("Map of apps.")
    assert ids["projects"]["index_path"] is None
    listed = {n["path"]: n for n in _get("/api/v1/second-brain/notes").json()}
    assert listed[APPS["path"]]["updated"] == "2026-10-02"


def test_old_schema_db_still_serves_before_resync(tmp_path):
    db = tmp_path / "old.db"
    conn = sqlite3.connect(db)
    conn.executescript(
        "CREATE TABLE notes (path TEXT PRIMARY KEY, folder TEXT NOT NULL, title TEXT NOT NULL,"
        " aliases TEXT NOT NULL, status TEXT, body TEXT NOT NULL);"
        "INSERT INTO notes VALUES ('wikis/apps/index.md','wikis','Apps','[]',NULL,'# Apps');"
    )
    conn.commit()
    conn.close()
    second_brain_store.configure(str(db))
    note = _get("/api/v1/second-brain/notes/wikis/apps/index.md").json()
    assert note["frontmatter"] == {} and note["link_map"] == {} and note["links"] == []
    assert _get("/api/v1/second-brain/graph").json()["edges"] == []
    assert _get("/api/v1/second-brain/portals").status_code == 200


def test_new_endpoints_require_the_read_token():
    for url in ("/api/v1/second-brain/graph", "/api/v1/second-brain/portals"):
        assert _get(url, token="bad").status_code == 401
        assert _get(url, token=None).status_code == 401
```

Append to `backend/tests/test_second_brain_push.py`:

```python
def test_frontmatter_forwarded_without_the_fields_stored_elsewhere(tmp_path):
    vault = _vault(tmp_path, "body")
    (vault / "wikis" / "apps" / "index.md").write_text(
        '---\ntype: wiki-index\ntitle: "Apps"\naliases: [Apps]\nstatus: draft\nupdated: 2026-10-02\n---\nbody'
    )
    note = sbp.load_vault(vault)[0]
    assert note["frontmatter"] == {"type": "wiki-index", "updated": "2026-10-02"}
```

- [ ] **Step 3: Run tests, verify they fail**

Run (from `backend/`): `pytest tests/test_second_brain.py tests/test_second_brain_push.py -q`
Expected: new tests FAIL (KeyError `link_map`, 404 on `/graph`, `frontmatter` missing).

- [ ] **Step 4: Implement the store**

In `backend/app/second_brain_store.py` replace the imports/schema/`configure` and `replace_all`, `list_notes`, `get_note`, and add `portal_of`, `portals`, `graph`. Final relevant parts:

```python
import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator, Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
    path TEXT PRIMARY KEY, folder TEXT NOT NULL, title TEXT NOT NULL,
    aliases TEXT NOT NULL, status TEXT, body TEXT NOT NULL,
    frontmatter TEXT NOT NULL DEFAULT '{}', link_map TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS links (
    src TEXT NOT NULL, dst TEXT NOT NULL, PRIMARY KEY (src, dst)
);
CREATE TABLE IF NOT EXISTS meta (
    id INTEGER PRIMARY KEY CHECK (id = 1), payload TEXT NOT NULL, pushed_at TEXT NOT NULL
);
"""
_NEW_COLUMNS = (("frontmatter", "'{}'"), ("link_map", "'{}'"))
_WIKILINK = re.compile(r"\[\[([^\]|#]+)")
_INLINE_LINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]+))?\]\]")
_PRIORITY = {"wikis": 0, "knowledge": 1, "projects": 2, "questions": 3}


def configure(db_path: str) -> None:
    global _db_path
    _db_path = db_path
    with _connect() as conn:
        conn.executescript(_SCHEMA)
        # Existing prod volumes hold the old notes table; add columns until the next sync.
        have = {r["name"] for r in conn.execute("PRAGMA table_info(notes)")}
        for col, default in _NEW_COLUMNS:
            if col not in have:
                conn.execute(f"ALTER TABLE notes ADD COLUMN {col} TEXT NOT NULL DEFAULT {default}")


def portal_of(path: str) -> str:
    """`wikis/apps/x.md` -> `wikis/apps`, `knowledge/ai/x.md` -> `knowledge/ai`, `projects/x.md` -> `projects`."""
    parts = path.split("/")
    return "/".join(parts[:2]) if parts[0] in ("wikis", "knowledge") and len(parts) > 2 else parts[0]


def _name_map(notes: list[dict]) -> dict[str, str]:
    names: dict[str, str] = {}
    for n in sorted(notes, key=lambda n: _PRIORITY.get(n["folder"], 9)):
        stem = n["path"].rsplit("/", 1)[-1].removesuffix(".md")
        for name in (stem, n["title"], *n["aliases"]):
            names.setdefault(name.strip().lower(), n["path"])
    return names


def _preview(body: str, limit: int = 200) -> str:
    for para in body.split("\n\n"):
        p = para.strip()
        if p and not p.startswith(("#", "|", "-", ">", "*", "```", "1.")):
            flat = _INLINE_LINK.sub(lambda m: m.group(2) or m.group(1), p)
            return " ".join(flat.split())[:limit]
    return ""


def replace_all(meta: dict, notes: list[dict]) -> None:
    names = _name_map(notes)
    rows, edges = [], set()
    for n in notes:
        link_map: dict[str, Optional[str]] = {}
        for target in _WIKILINK.findall(n["body"]):
            dst = names.get(target.strip().lower())
            link_map[target.strip().lower()] = dst
            if dst and dst != n["path"]:
                edges.add((n["path"], dst))
        rows.append(
            (
                n["path"], n["folder"], n["title"], json.dumps(n["aliases"]), n["status"],
                n["body"], json.dumps(n.get("frontmatter", {})), json.dumps(link_map),
            )
        )
    with _connect() as conn:
        conn.execute("DELETE FROM notes")
        conn.execute("DELETE FROM links")
        conn.executemany(
            "INSERT INTO notes (path, folder, title, aliases, status, body, frontmatter, link_map)"
            " VALUES (?,?,?,?,?,?,?,?)",
            rows,
        )
        conn.executemany("INSERT INTO links (src, dst) VALUES (?,?)", sorted(edges))
        conn.execute(
            "INSERT INTO meta (id, payload, pushed_at) VALUES (1, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET payload = excluded.payload, "
            "pushed_at = excluded.pushed_at",
            (json.dumps(meta), datetime.now(timezone.utc).isoformat()),
        )
```

`list_notes`: change the SELECT to include `frontmatter` and shape rows:

```python
def list_notes(q: str = "", folder: str = "") -> list[dict]:
    sql, args = "SELECT path, folder, title, aliases, status, frontmatter FROM notes WHERE 1=1", []
    if folder:
        sql += " AND folder = ?"
        args.append(folder)
    if q:
        sql += " AND (title LIKE ? OR aliases LIKE ? OR body LIKE ?)"
        args += [f"%{q}%"] * 3
    with _connect() as conn:
        rows = conn.execute(sql + " ORDER BY folder, title LIMIT 500", args).fetchall()
    return [
        {
            **{k: r[k] for k in ("path", "folder", "title", "status")},
            "aliases": json.loads(r["aliases"]),
            "updated": json.loads(r["frontmatter"]).get("updated"),
        }
        for r in rows
    ]
```

`get_note` and the new functions:

```python
def get_note(path: str) -> Optional[dict]:
    with _connect() as conn:
        r = conn.execute("SELECT * FROM notes WHERE path = ?", (path,)).fetchone()
        if r is None:
            return None
        out = [x["dst"] for x in conn.execute("SELECT dst FROM links WHERE src = ? ORDER BY dst", (path,))]
        back = [x["src"] for x in conn.execute("SELECT src FROM links WHERE dst = ? ORDER BY src", (path,))]
        wanted = sorted(set(out) | set(back))
        refs = {
            x["path"]: x
            for x in conn.execute(
                f"SELECT path, title, folder, body FROM notes WHERE path IN ({','.join('?' * len(wanted))})",
                wanted,
            )
        } if wanted else {}
    ref = lambda p: {k: refs[p][k] for k in ("path", "title", "folder")}  # noqa: E731
    note = {k: r[k] for k in ("path", "folder", "title", "status", "body")}
    return {
        **note,
        "aliases": json.loads(r["aliases"]),
        "frontmatter": json.loads(r["frontmatter"]),
        "link_map": json.loads(r["link_map"]),
        "links": [ref(p) for p in out],
        "backlinks": [ref(p) for p in back],
        "previews": {p: _preview(refs[p]["body"]) for p in wanted},
        "portal": portal_of(path),
    }


def graph() -> dict:
    with _connect() as conn:
        nodes = [dict(r) for r in conn.execute("SELECT path, title, folder FROM notes ORDER BY path")]
        edges = [[r["src"], r["dst"]] for r in conn.execute("SELECT src, dst FROM links ORDER BY src, dst")]
    return {"nodes": nodes, "edges": edges}


def portals() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute("SELECT path, title, body FROM notes ORDER BY path").fetchall()
    out: dict[str, dict] = {}
    for r in rows:
        pid = portal_of(r["path"])
        p = out.setdefault(
            pid,
            {"id": pid, "title": pid.rsplit("/", 1)[-1].replace("-", " ").title(),
             "count": 0, "index_path": None, "description": ""},
        )
        p["count"] += 1
        if r["path"] == f"{pid}/index.md":
            p.update(index_path=r["path"], title=r["title"], description=_preview(r["body"]))
    return list(out.values())
```

(If ruff objects to the `ref` lambda, make it a nested `def`.)

In `backend/app/schemas.py` add to `NoteIn`: `frontmatter: dict[str, str] = {}`.

In `backend/app/main.py`, directly above the `/notes/{path:path}` route add:

```python
@app.get("/api/v1/second-brain/portals", dependencies=[Depends(_require_read_token)])
def second_brain_portals() -> list[dict]:
    return second_brain_store.portals()


@app.get("/api/v1/second-brain/graph", dependencies=[Depends(_require_read_token)])
def second_brain_graph() -> dict:
    return second_brain_store.graph()
```

- [ ] **Step 5: Implement the push-script change**

In `scripts/second_brain_push.py` `load_vault`, add to the note dict (after `"status"`):

```python
                    "frontmatter": {
                        k: v for k, v in fm.items() if k not in ("title", "aliases", "status")
                    },
```

- [ ] **Step 6: Run the full backend suite and lint**

Run (from `backend/`): `pytest -q && ruff check .`
Expected: all pass (existing `test_second_brain.py` tests included; its `NOTE` has no `frontmatter`, which defaults to `{}`).

- [ ] **Step 7: Commit**

```bash
git add backend scripts
git commit -m "feat(second-brain): resolve wikilinks at sync; serve links, backlinks, portals, graph"
```

---

### Task 2: Frontend types and pure helpers

**Files:**
- Modify: `frontend/src/types.ts:136-146`
- Modify: `frontend/src/api.ts` (imports line 1, append after `fetchNote`)
- Modify: `frontend/src/components/dashboard/secondBrain.ts` (rewrite `linkWikilinks`, add helpers)
- Modify (rewrite): `frontend/src/components/dashboard/secondBrain.test.ts`

**Interfaces:**
- Produces (`secondBrain.ts`): `noteHref(path): string`, `pathFromHref(href): string | null`, `linkWikilinks(body, linkMap: Record<string,string|null>): string`, `slugify(s): string`, `headings(body): Heading[]`, `infoboxRows(note): [string,string][]`, `portalLabel(id): string`, `MISSING = "#missing"`.
- Produces (`types.ts`): `NoteRef`, `NoteListItem.updated`, `Note` (extended), `Portal`, `VaultGraph`.
- Produces (`api.ts`): `fetchPortals(token): Promise<Portal[]>`, `fetchGraph(token): Promise<VaultGraph>`.

- [ ] **Step 1: Write the failing tests**

Replace `secondBrain.test.ts` with:

```ts
import { describe, expect, it } from "vitest";

import { headings, infoboxRows, linkWikilinks, MISSING, noteHref, obsidianUrl, pathFromHref, portalLabel, slugify } from "./secondBrain";
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
    const note = {
      path: "wikis/apps/index.md", folder: "wikis", title: "Apps", aliases: ["Apps", "app list"],
      status: "approved", updated: null, body: "", frontmatter: { type: "wiki-index", updated: "2026-10-02" },
      link_map: {}, links: [], backlinks: [], previews: {}, portal: "wikis/apps",
    } as Note;
    expect(infoboxRows(note)).toEqual([
      ["Type", "wiki-index"], ["Status", "approved"], ["Updated", "2026-10-02"],
      ["Wiki", "apps"], ["Also known as", "app list"],
    ]);
    expect(portalLabel("projects")).toBe("projects");
  });
});
```

- [ ] **Step 2: Run, verify failure**

Run (from `frontend/`): `npm run test -- secondBrain`
Expected: FAIL (missing exports).

- [ ] **Step 3: Types and API**

`types.ts` — replace the `NoteListItem` / `Note` block with:

```ts
export interface NoteListItem {
  path: string;
  folder: string;
  title: string;
  aliases: string[];
  status: string | null;
  updated: string | null;
}

export interface NoteRef {
  path: string;
  title: string;
  folder: string;
}

export interface Note extends Omit<NoteListItem, "updated"> {
  updated?: string | null;
  body: string;
  frontmatter: Record<string, string>;
  /** Lowercased wikilink target -> note path (null = no such note). */
  link_map: Record<string, string | null>;
  links: NoteRef[];
  backlinks: NoteRef[];
  previews: Record<string, string>;
  portal: string;
}

export interface Portal {
  id: string;
  title: string;
  count: number;
  index_path: string | null;
  description: string;
}

export interface VaultGraph {
  nodes: NoteRef[];
  edges: [string, string][];
}
```

`api.ts`: add `Portal, VaultGraph` to the type import on line 1 and append:

```ts
export const fetchPortals = (token: string) => secondBrainGet<Portal[]>("portals", token);

export const fetchGraph = (token: string) => secondBrainGet<VaultGraph>("graph", token);
```

- [ ] **Step 4: Implement helpers**

Replace `secondBrain.ts` with:

```ts
import type { Note } from "../../types";

export const VAULT = "second-brain";
export const MISSING = "#missing";
const PREFIX = "/knowledge/";

export const obsidianUrl = (path: string): string =>
  `obsidian://open?vault=${encodeURIComponent(VAULT)}&file=${encodeURIComponent(path.replace(/\.md$/, ""))}`;

const encodeSegment = (s: string) => encodeURIComponent(s).replace(/[()]/g, (c) => `%${c.charCodeAt(0).toString(16).toUpperCase()}`);

/** In-app URL for a note path (`wikis/apps/x.md` -> `/knowledge/wikis/apps/x`). */
export const noteHref = (path: string): string =>
  PREFIX + path.replace(/\.md$/, "").split("/").map(encodeSegment).join("/");

/** Inverse of noteHref; null for hrefs that are not note links. */
export function pathFromHref(href: string): string | null {
  if (!href.startsWith(PREFIX)) return null;
  return href.slice(PREFIX.length).split("/").map(decodeURIComponent).join("/") + ".md";
}

/** Rewrites [[Target|Label]] to in-app links using the server-resolved map; null targets become red links. */
export function linkWikilinks(body: string, linkMap: Record<string, string | null>): string {
  return body.replace(/\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]+))?\]\]/g, (m, target: string, label?: string) => {
    const key = target.trim().toLowerCase();
    if (!(key in linkMap)) return (label ?? target).trim();
    const path = linkMap[key];
    return `[${(label ?? target).trim()}](${path ? noteHref(path) : MISSING})`;
  });
}

export const slugify = (s: string): string => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

export interface Heading {
  level: 2 | 3;
  text: string;
  id: string;
}

const plain = (s: string) =>
  s
    .replace(/\[\[(?:[^\]|]*\|)?([^\]]+)\]\]/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/[`*_]/g, "")
    .trim();

/** h2/h3 headings for the table of contents (fenced code blocks skipped). */
export function headings(body: string): Heading[] {
  const out: Heading[] = [];
  let fenced = false;
  for (const line of body.split("\n")) {
    if (line.trimStart().startsWith("```")) fenced = !fenced;
    const m = !fenced && /^(#{2,3})\s+(.+?)\s*$/.exec(line);
    if (m) {
      const text = plain(m[2]);
      out.push({ level: m[1].length as 2 | 3, text, id: slugify(text) });
    }
  }
  return out;
}

export const portalLabel = (id: string): string => id.split("/").pop() ?? id;

export function infoboxRows(note: Note): [string, string][] {
  const rows: [string, string | null | undefined][] = [
    ["Type", note.frontmatter.type],
    ["Status", note.status],
    ["Updated", note.frontmatter.updated],
    ["Wiki", portalLabel(note.portal)],
    ["Also known as", note.aliases.filter((a) => a !== note.title).join(", ")],
  ];
  return rows.filter((r): r is [string, string] => Boolean(r[1]));
}
```

- [ ] **Step 5: Run tests, lint, typecheck**

Run (from `frontend/`): `npm run test -- secondBrain && npm run lint`
Expected: helper tests PASS. `tsc` errors in `SecondBrain.tsx` (old `linkWikilinks` signature, `NoteListItem.updated`) are expected until Task 4; do not fix them here. Run only `npm run test -- secondBrain` and `npx eslint src/components/dashboard/secondBrain.ts` in this task.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types.ts frontend/src/api.ts frontend/src/components/dashboard/secondBrain.ts frontend/src/components/dashboard/secondBrain.test.ts
git commit -m "feat(knowledge): note types, api calls and article helpers"
```

---

### Task 3: Article component

**Files:**
- Create: `frontend/src/components/knowledge/Article.tsx`
- Create: `frontend/src/components/knowledge/Article.test.tsx`
- Modify: `frontend/src/styles.css` (append wiki styles)

**Interfaces:**
- Consumes: `linkWikilinks, headings, infoboxRows, noteHref, pathFromHref, slugify, obsidianUrl, MISSING, portalLabel` from `components/dashboard/secondBrain`; `Note` from types.
- Produces: `export function Article({ note }: { note: Note })`.

- [ ] **Step 1: Write the failing test**

`Article.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import type { Note } from "../../types";
import { Article } from "./Article";

const base: Note = {
  path: "wikis/apps/index.md", folder: "wikis", title: "Apps Wiki", aliases: ["Apps Wiki", "app list"],
  status: "approved", updated: null, frontmatter: { updated: "2026-10-02" }, portal: "wikis/apps",
  body: "# Apps\n\nLead.\n\n## One\nSee [[Gym Tracker]] and [[Nope]].\n\n## Two\nx\n\n## Three\ny",
  link_map: { "gym tracker": "projects/gym-tracker.md", nope: null },
  links: [{ path: "projects/gym-tracker.md", title: "Gym Tracker", folder: "projects" }],
  backlinks: [{ path: "projects/other.md", title: "Other", folder: "projects" }],
  previews: { "projects/gym-tracker.md": "A gym app." },
};
const renderIt = (note: Note) => render(<MemoryRouter><Article note={note} /></MemoryRouter>);

describe("Article", () => {
  it("renders infobox, TOC, linked and red wikilinks, hover preview, see-also and backlinks", () => {
    renderIt(base);
    expect(screen.getByRole("heading", { level: 1, name: "Apps Wiki" })).toBeInTheDocument();
    expect(screen.getByText("2026-10-02")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "One" })).toHaveAttribute("href", "#one");
    expect(screen.getAllByRole("link", { name: "Gym Tracker" })[0]).toHaveAttribute("href", "/knowledge/projects/gym-tracker");
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
```

- [ ] **Step 2: Run, verify failure**

Run: `npm run test -- Article` → FAIL (module not found).

- [ ] **Step 3: Implement**

`Article.tsx`:

```tsx
import type { ReactNode } from "react";
import { isValidElement } from "react";
import Markdown from "react-markdown";
import { Link } from "react-router-dom";

import { headings, infoboxRows, linkWikilinks, MISSING, noteHref, obsidianUrl, pathFromHref, portalLabel, slugify } from "../dashboard/secondBrain";
import type { Note, NoteRef } from "../../types";

const textOf = (node: ReactNode): string =>
  typeof node === "string" || typeof node === "number"
    ? String(node)
    : Array.isArray(node)
      ? node.map(textOf).join("")
      : isValidElement<{ children?: ReactNode }>(node)
        ? textOf(node.props.children)
        : "";

function RefList({ title, refs }: { title: string; refs: NoteRef[] }) {
  if (!refs.length) return null;
  return (
    <section className="wiki-refs">
      <h2>{title}</h2>
      <ul>
        {refs.map((r) => (
          <li key={r.path}><Link to={noteHref(r.path)}>{r.title}</Link></li>
        ))}
      </ul>
    </section>
  );
}

export function Article({ note }: { note: Note }) {
  const body = linkWikilinks(note.body, note.link_map);
  const toc = headings(note.body);
  const infobox = infoboxRows(note);
  return (
    <article className="wiki-article">
      <header>
        <h1>{note.title}</h1>
        <p className="ui-stat-label">
          From the <Link to={`/knowledge/${note.portal}`}>{portalLabel(note.portal)}</Link> wiki
          {" · "}
          <a href={obsidianUrl(note.path)}>Open in Obsidian</a>
        </p>
      </header>
      <div className="wiki-layout">
        {infobox.length > 0 && (
          <aside className="wiki-infobox" aria-label="Article details">
            <dl>
              {infobox.map(([k, v]) => (
                <div key={k}><dt>{k}</dt><dd>{v}</dd></div>
              ))}
            </dl>
          </aside>
        )}
        {toc.length >= 3 && (
          <nav className="wiki-toc" aria-label="Contents">
            <strong>Contents</strong>
            <ol>
              {toc.map((h) => (
                <li key={h.id} className={`toc-${h.level}`}><a href={`#${h.id}`}>{h.text}</a></li>
              ))}
            </ol>
          </nav>
        )}
        <div className="wiki-body">
          <Markdown
            components={{
              h2: ({ children }) => <h2 id={slugify(textOf(children))}>{children}</h2>,
              h3: ({ children }) => <h3 id={slugify(textOf(children))}>{children}</h3>,
              a: ({ href = "", children }) => {
                if (href === MISSING) return <span className="wiki-redlink" title="No article yet">{children}</span>;
                const path = pathFromHref(href);
                if (!path) return <a href={href}>{children}</a>;
                const preview = note.previews[path];
                return (
                  <span className="wiki-link">
                    <Link to={href}>{children}</Link>
                    {preview && <span role="tooltip" className="wiki-preview">{preview}</span>}
                  </span>
                );
              },
            }}
          >
            {body}
          </Markdown>
        </div>
      </div>
      <RefList title="See also" refs={note.links} />
      <RefList title="What links here" refs={note.backlinks} />
      <footer className="wiki-categories">
        <span className="ui-stat-label">Categories:</span>
        <Link to={`/knowledge/${note.portal}`}>{note.portal}</Link>
      </footer>
    </article>
  );
}
```

Portal ids are plain folder names, so `/knowledge/${note.portal}` needs no encoding; if a folder name ever needs it, switch both uses to `encodeURI`.

Append to `frontend/src/styles.css`:

```css
/* Knowledge: wiki article, portals, graph */
.wiki-article { max-width: 960px; }
.wiki-article h1 { margin: 0 0 4px; font-family: var(--font-sans); }
.wiki-layout { display: block; }
.wiki-infobox { float: right; width: 260px; margin: 0 0 16px 24px; padding: 12px 16px; background: var(--subtle); border: 1px solid var(--border); border-radius: var(--radius); }
.wiki-infobox dl { margin: 0; }
.wiki-infobox div { display: flex; justify-content: space-between; gap: 12px; padding: 4px 0; }
.wiki-infobox dt { color: var(--text-muted); }
.wiki-infobox dd { margin: 0; text-align: right; }
.wiki-toc { display: inline-block; margin: 0 0 16px; padding: 12px 16px; background: var(--subtle); border: 1px solid var(--border); border-radius: var(--radius); }
.wiki-toc ol { margin: 8px 0 0; padding-left: 20px; }
.wiki-toc .toc-3 { margin-left: 16px; list-style: circle; }
.wiki-body h2 { border-bottom: 1px solid var(--border); padding-bottom: 4px; margin-top: 28px; }
.wiki-link { position: relative; display: inline-block; }
.wiki-preview { display: none; position: absolute; left: 0; top: 1.5em; z-index: 5; width: 280px; padding: 10px 12px; background: var(--surface); border: 1px solid var(--border-strong); border-radius: var(--radius); font-size: 0.85em; color: var(--text-muted); }
.wiki-link:hover .wiki-preview, .wiki-link:focus-within .wiki-preview { display: block; }
.wiki-redlink { color: var(--error); cursor: help; }
.wiki-refs ul { columns: 2; padding-left: 20px; }
.wiki-categories { margin-top: 24px; padding-top: 12px; border-top: 1px solid var(--border); display: flex; gap: 12px; flex-wrap: wrap; }
.portal-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 12px; margin: 16px 0; }
.portal-grid a { text-decoration: none; color: inherit; }
.portal-grid p { color: var(--text-muted); margin: 4px 0 0; }
.kb-search { width: 100%; max-width: 420px; }
.kb-graph { width: 100%; height: 480px; background: var(--subtle); border: 1px solid var(--border); border-radius: var(--radius); }
.kb-graph text { fill: var(--text-muted); font-size: 10px; pointer-events: none; }
.kb-graph .node-wikis { fill: var(--accent); } .kb-graph .node-knowledge { fill: var(--info); }
.kb-graph .node-projects { fill: var(--success); } .kb-graph .node-questions { fill: var(--warning); }
.kb-graph .node-current { stroke: var(--text); stroke-width: 2; }
.kb-graph line { stroke: var(--border-strong); }
@media (max-width: 700px) {
  .wiki-infobox { float: none; width: auto; margin: 0 0 16px; }
  .wiki-refs ul { columns: 1; }
  .wiki-preview { width: 220px; }
}
```

- [ ] **Step 4: Run tests**

Run: `npm run test -- Article` → PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/knowledge frontend/src/styles.css
git commit -m "feat(knowledge): Wikipedia-style article view"
```

---

### Task 4: Landing, portal pages, routing and page shell

**Files:**
- Create: `frontend/src/components/knowledge/Portals.tsx`
- Create: `frontend/src/components/knowledge/Portals.test.tsx`
- Modify (rewrite): `frontend/src/pages/SecondBrain.tsx`
- Modify: `frontend/src/App.tsx:28`

**Interfaces:**
- Consumes: `fetchNotes, fetchNote, fetchPortals, FinancialsAuthError` (api), `useAsyncData`, `Article`, `Table`, `Portal`, `NoteListItem`, `noteHref`.
- Produces: `Landing({ portals, notes })`, `PortalPage({ portal, notes })` from `Portals.tsx`; route `/knowledge/*` handled by `SecondBrain`; Task 5 adds `/knowledge/graph`.

- [ ] **Step 1: Write the failing tests**

`Portals.test.tsx`:

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import type { NoteListItem, Portal } from "../../types";
import { Landing, PortalPage } from "./Portals";

const portals: Portal[] = [
  { id: "wikis/apps", title: "Apps Wiki", count: 2, index_path: "wikis/apps/index.md", description: "Map of apps." },
  { id: "projects", title: "Projects", count: 1, index_path: null, description: "" },
];
const note = (path: string, title: string, updated: string | null = null): NoteListItem => ({
  path, folder: path.split("/")[0], title, aliases: [], status: null, updated,
});
const notes = [note("wikis/apps/index.md", "Apps Wiki", "2026-10-02"), note("wikis/apps/zeta.md", "Zeta"), note("projects/p.md", "P")];
const wrap = (ui: React.ReactElement) => render(<MemoryRouter>{ui}</MemoryRouter>);

describe("Portals", () => {
  it("lists portal cards and filters notes by search", () => {
    wrap(<Landing portals={portals} notes={notes} />);
    expect(screen.getByRole("link", { name: /Apps Wiki/ })).toHaveAttribute("href", "/knowledge/wikis/apps");
    expect(screen.getByText("Map of apps.")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "zeta" } });
    expect(screen.getByRole("link", { name: "Zeta" })).toBeInTheDocument();
  });

  it("shows a portal's articles A-Z, and an empty state when it has none", () => {
    wrap(<PortalPage portal={portals[0]} notes={notes} />);
    const links = screen.getAllByRole("link").map((l) => l.textContent);
    expect(links.indexOf("Apps Wiki")).toBeLessThan(links.indexOf("Zeta"));
    wrap(<PortalPage portal={{ ...portals[1], count: 0 }} notes={[]} />);
    expect(screen.getByText(/No articles/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run, verify failure** — `npm run test -- Portals` → FAIL.

- [ ] **Step 3: Implement `Portals.tsx`**

```tsx
import { useState } from "react";
import { Link } from "react-router-dom";

import type { NoteListItem, Portal } from "../../types";
import { noteHref, portalLabel } from "../dashboard/secondBrain";
import { Card } from "../primitives/Card";
import { EmptyState } from "../primitives/EmptyState";
import { PageHeader } from "../primitives/PageHeader";

const inPortal = (n: NoteListItem, id: string) =>
  n.path.startsWith(`${id}/`) && (id.includes("/") || !["wikis", "knowledge"].includes(id));

const byTitle = (a: NoteListItem, b: NoteListItem) => a.title.localeCompare(b.title);

function NoteLinks({ notes }: { notes: NoteListItem[] }) {
  return (
    <ul className="wiki-refs">
      {notes.map((n) => (
        <li key={n.path}><Link to={noteHref(n.path)}>{n.title}</Link></li>
      ))}
    </ul>
  );
}

export function Landing({ portals, notes }: { portals: Portal[]; notes: NoteListItem[] }) {
  const [q, setQ] = useState("");
  const needle = q.trim().toLowerCase();
  const hits = needle
    ? notes.filter((n) => `${n.title} ${n.aliases.join(" ")}`.toLowerCase().includes(needle)).sort(byTitle).slice(0, 50)
    : [];
  const recent = notes.filter((n) => n.updated).sort((a, b) => (b.updated! > a.updated! ? 1 : -1)).slice(0, 8);
  return (
    <>
      <PageHeader title="Knowledge" description="Read-only copy of the Obsidian vault, organised as wiki portals. Edit in Obsidian, then push." />
      <input className="kb-search" type="search" placeholder="Search articles" aria-label="Search articles" value={q} onChange={(e) => setQ(e.target.value)} />
      {needle ? (
        hits.length ? <NoteLinks notes={hits} /> : <EmptyState message="No matching articles." />
      ) : (
        <>
          <div className="portal-grid">
            {portals.map((p) => (
              <Link key={p.id} to={`/knowledge/${p.id}`}>
                <Card variant="interactive">
                  <strong>{p.title}</strong> <span className="ui-stat-label">{p.count} articles</span>
                  {p.description && <p>{p.description}</p>}
                </Card>
              </Link>
            ))}
          </div>
          {recent.length > 0 && (
            <>
              <h2>Recently updated</h2>
              <NoteLinks notes={recent} />
            </>
          )}
          <p className="ui-stat-label"><Link to="/knowledge/graph">Graph view</Link> · <Link to="/knowledge/all">All pages</Link></p>
        </>
      )}
    </>
  );
}

export function PortalPage({ portal, notes }: { portal: Portal; notes: NoteListItem[] }) {
  const articles = notes.filter((n) => inPortal(n, portal.id)).sort(byTitle);
  return (
    <>
      <Link className="ui-stat-label" to="/knowledge">← Portals</Link>
      <PageHeader title={portal.title} description={portal.description || `Articles in ${portalLabel(portal.id)}`} />
      {articles.length ? <NoteLinks notes={articles} /> : <EmptyState message="No articles in this portal." />}
    </>
  );
}
```

Verify `EmptyState` takes `message` (used that way in the old `SecondBrain.tsx`). The test's empty-state regex `/No articles/` matches "No articles in this portal."

- [ ] **Step 4: Rewrite `pages/SecondBrain.tsx`**

```tsx
import { useCallback, useState, type FormEvent } from "react";
import { Link, Navigate, useParams, useSearchParams } from "react-router-dom";

import { FinancialsAuthError, fetchNote, fetchNotes, fetchPortals } from "../api";
import { noteHref } from "../components/dashboard/secondBrain";
import { Article } from "../components/knowledge/Article";
import { Landing, PortalPage } from "../components/knowledge/Portals";
import { Card } from "../components/primitives/Card";
import { EmptyState } from "../components/primitives/EmptyState";
import { PageHeader } from "../components/primitives/PageHeader";
import { Table, type Column } from "../components/primitives/Table";
import { useAsyncData } from "../hooks/useAsyncData";
import { readToken, writeToken } from "../token";
import type { NoteListItem } from "../types";

const noteColumns: Column<NoteListItem>[] = [
  { key: "title", header: "Title", sortValue: (n) => n.title, render: (n) => <Link to={noteHref(n.path)}>{n.title}</Link> },
  { key: "folder", header: "Folder", sortValue: (n) => n.folder, render: (n) => n.folder },
  { key: "status", header: "Status", sortValue: (n) => n.status ?? "", render: (n) => n.status ?? "—" },
];

function Gate({ onToken }: { onToken: (t: string) => void }) {
  const [draft, setDraft] = useState("");
  function submit(event: FormEvent) {
    event.preventDefault();
    if (!draft.trim()) return;
    writeToken(draft.trim());
    onToken(draft.trim());
  }
  return (
    <Card>
      <form className="token-form" onSubmit={submit}>
        <label className="ui-stat-label" htmlFor="sb-token">Access token for the second brain</label>
        <input id="sb-token" type="password" value={draft} onChange={(e) => setDraft(e.target.value)} autoComplete="off" />
        <button className="refresh-button" type="submit">Unlock</button>
      </form>
    </Card>
  );
}

export default function SecondBrain() {
  const [token, setToken] = useState(readToken);
  if (!token) return <Gate onToken={setToken} />;
  return <Vault token={token} onAuthError={() => { writeToken(""); setToken(""); }} />;
}

function Vault({ token, onAuthError }: { token: string; onAuthError: () => void }) {
  const guard = useCallback(
    async <T,>(call: Promise<T>): Promise<T> => {
      try {
        return await call;
      } catch (err) {
        if (err instanceof FinancialsAuthError) onAuthError();
        throw err;
      }
    },
    [onAuthError],
  );
  const notes = useAsyncData(useCallback(() => guard(fetchNotes(token)), [guard, token]));
  const portals = useAsyncData(useCallback(() => guard(fetchPortals(token)), [guard, token]));
  const splat = useParams()["*"] ?? "";
  const [params] = useSearchParams();

  const legacy = params.get("note");
  if (legacy) return <Navigate replace to={noteHref(legacy)} />;

  const error = notes.error ?? portals.error;
  if (error) return <EmptyState message={error} />;
  if (!notes.data || !portals.data) return <EmptyState message="Loading…" />;

  if (!splat) return <Landing portals={portals.data} notes={notes.data} />;
  if (splat === "all") {
    return (
      <>
        <Link className="ui-stat-label" to="/knowledge">← Portals</Link>
        <Table columns={noteColumns} rows={notes.data} rowKey={(n) => n.path}
          searchText={(n) => `${n.title} ${n.path} ${n.aliases.join(" ")}`}
          filters={[{ label: "Folder", value: (n) => n.folder }]}
          emptyMessage="No notes. Run scripts/second_brain_push.py." />
      </>
    );
  }
  const portal = portals.data.find((p) => p.id === splat);
  if (portal) return <PortalPage portal={portal} notes={notes.data} />;
  return <ArticlePage token={token} path={`${splat}.md`} guard={guard} />;
}

function ArticlePage({ token, path, guard }: { token: string; path: string; guard: <T>(p: Promise<T>) => Promise<T> }) {
  const { data, error } = useAsyncData(useCallback(() => guard(fetchNote(token, path)), [guard, token, path]));
  if (error) return (
    <>
      <Link className="ui-stat-label" to="/knowledge">← Portals</Link>
      <EmptyState message="No such article." />
    </>
  );
  if (!data || data.path !== path) return <EmptyState message="Loading…" />;
  return (
    <>
      <Link className="ui-stat-label" to={`/knowledge/${data.portal}`}>← {data.portal}</Link>
      <Article note={data} />
    </>
  );
}
```

Implementation notes: `useParams()["*"]` is already decoded by the router; `noteHref` encodes, and `fetchNote` encodes per segment, so `path` is the raw note path. `PageHeader`, `Card`, `Table` imports must all be used or lint fails (remove unused ones). The `ArticlePage` hook re-fetches on `path` change because the callback identity changes.

In `App.tsx` change line 28 to `<Route path="/knowledge/*" element={<SecondBrain />} />`. (React Router v6/v7 `/knowledge/*` also matches `/knowledge`.)

- [ ] **Step 5: Run everything**

Run (from `frontend/`): `npm run test && npm run lint && npm run build`
Expected: all PASS. Fix lint (`react-hooks` rules) if the generic `guard` arrow in `.tsx` trips the parser (`<T,>` form is intentional).

- [ ] **Step 6: Commit**

```bash
git add frontend/src
git commit -m "feat(knowledge): portal landing, portal pages and splat routing"
```

---

### Task 5: Graph view

**Files:**
- Create: `frontend/src/components/knowledge/graphLayout.ts`
- Create: `frontend/src/components/knowledge/graphLayout.test.ts`
- Create: `frontend/src/components/knowledge/Graph.tsx`
- Modify: `frontend/src/pages/SecondBrain.tsx` (graph route + article neighborhood)

**Interfaces:**
- Produces: `neighborhood(g: VaultGraph, path: string): VaultGraph`, `layout(nodes: NoteRef[], edges: [string,string][], size: {w:number;h:number}): Record<string,{x:number;y:number}>`, `Graph({ graph, current?, onNavigate? })`.

- [ ] **Step 1: Write the failing tests**

```ts
import { describe, expect, it } from "vitest";

import { layout, neighborhood } from "./graphLayout";

const n = (path: string) => ({ path, title: path, folder: "wikis" });
const graph = {
  nodes: ["a", "b", "c", "d"].map(n),
  edges: [["a", "b"], ["c", "a"], ["c", "d"]] as [string, string][],
};

describe("graph layout", () => {
  it("keeps the note, its direct neighbours and the edges between them", () => {
    const g = neighborhood(graph, "a");
    expect(g.nodes.map((x) => x.path).sort()).toEqual(["a", "b", "c"]);
    expect(g.edges).toEqual([["a", "b"], ["c", "a"]]);
  });

  it("places every node at finite, distinct coordinates inside the box", () => {
    const pos = layout(graph.nodes, graph.edges, { w: 400, h: 300 });
    const pts = Object.values(pos);
    expect(pts).toHaveLength(4);
    for (const p of pts) {
      expect(Number.isFinite(p.x) && Number.isFinite(p.y)).toBe(true);
      expect(p.x).toBeGreaterThanOrEqual(0); expect(p.x).toBeLessThanOrEqual(400);
      expect(p.y).toBeGreaterThanOrEqual(0); expect(p.y).toBeLessThanOrEqual(300);
    }
    expect(new Set(pts.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`)).size).toBe(4);
  });

  it("handles an empty and a single-node graph", () => {
    expect(layout([], [], { w: 10, h: 10 })).toEqual({});
    expect(Object.keys(layout([n("a")], [], { w: 10, h: 10 }))).toEqual(["a"]);
  });
});
```

- [ ] **Step 2: Run, verify failure** — `npm run test -- graphLayout` → FAIL.

- [ ] **Step 3: Implement `graphLayout.ts`**

```ts
import type { NoteRef, VaultGraph } from "../../types";

type Pos = { x: number; y: number };

export function neighborhood(g: VaultGraph, path: string): VaultGraph {
  const keep = new Set([path]);
  for (const [s, d] of g.edges) {
    if (s === path) keep.add(d);
    if (d === path) keep.add(s);
  }
  return {
    nodes: g.nodes.filter((n) => keep.has(n.path)),
    edges: g.edges.filter(([s, d]) => keep.has(s) && keep.has(d)),
  };
}

/** Deterministic force layout: circle start, pairwise repulsion, edge springs, centring. O(n^2 * iterations). */
export function layout(nodes: NoteRef[], edges: [string, string][], { w, h }: { w: number; h: number }, iterations = 200): Record<string, Pos> {
  const pos: Record<string, Pos> = {};
  nodes.forEach((n, i) => {
    const a = (2 * Math.PI * i) / nodes.length;
    pos[n.path] = { x: w / 2 + (w / 3) * Math.cos(a), y: h / 2 + (h / 3) * Math.sin(a) };
  });
  const k = Math.sqrt((w * h) / Math.max(nodes.length, 1));
  for (let it = 0; it < iterations; it++) {
    const cool = 1 - it / iterations;
    const move: Record<string, Pos> = Object.fromEntries(nodes.map((n) => [n.path, { x: 0, y: 0 }]));
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = pos[nodes[i].path], b = pos[nodes[j].path];
        const dx = a.x - b.x || 0.01, dy = a.y - b.y || 0.01;
        const d = Math.hypot(dx, dy);
        const f = (k * k) / d / d;
        move[nodes[i].path].x += dx * f; move[nodes[i].path].y += dy * f;
        move[nodes[j].path].x -= dx * f; move[nodes[j].path].y -= dy * f;
      }
    }
    for (const [s, d] of edges) {
      const a = pos[s], b = pos[d];
      if (!a || !b) continue;
      const dx = a.x - b.x, dy = a.y - b.y, f = Math.hypot(dx, dy) / k;
      move[s].x -= dx * f; move[s].y -= dy * f; move[d].x += dx * f; move[d].y += dy * f;
    }
    for (const n of nodes) {
      const p = pos[n.path], m = move[n.path];
      const step = Math.min(Math.hypot(m.x, m.y), 20 * cool + 1) / (Math.hypot(m.x, m.y) || 1);
      p.x = Math.min(w, Math.max(0, p.x + m.x * step + (w / 2 - p.x) * 0.01));
      p.y = Math.min(h, Math.max(0, p.y + m.y * step + (h / 2 - p.y) * 0.01));
    }
  }
  return pos;
}
```

- [ ] **Step 4: Implement `Graph.tsx`**

```tsx
import { useMemo } from "react";
import { Link } from "react-router-dom";

import type { VaultGraph } from "../../types";
import { noteHref } from "../dashboard/secondBrain";
import { layout } from "./graphLayout";

const SIZE = { w: 800, h: 480 };

export function Graph({ graph, current }: { graph: VaultGraph; current?: string }) {
  const pos = useMemo(() => layout(graph.nodes, graph.edges, SIZE), [graph]);
  return (
    <svg className="kb-graph" viewBox={`0 0 ${SIZE.w} ${SIZE.h}`} role="img" aria-label="Note graph">
      {graph.edges.map(([s, d]) => pos[s] && pos[d] && <line key={`${s}>${d}`} x1={pos[s].x} y1={pos[s].y} x2={pos[d].x} y2={pos[d].y} />)}
      {graph.nodes.map((n) => (
        <Link key={n.path} to={noteHref(n.path)}>
          <circle cx={pos[n.path].x} cy={pos[n.path].y} r={n.path === current ? 7 : 5} className={`node-${n.folder}${n.path === current ? " node-current" : ""}`}>
            <title>{n.title}</title>
          </circle>
          {(current || n.path === current) && <text x={pos[n.path].x + 8} y={pos[n.path].y + 3}>{n.title}</text>}
        </Link>
      ))}
    </svg>
  );
}
```

Labels are drawn only in neighbourhood mode (when `current` is set); the full-vault view relies on the `<title>` hover tooltip to stay legible.

- [ ] **Step 5: Wire into `SecondBrain.tsx`**

Add `fetchGraph` to the api import, and import `Graph` and `neighborhood`. In `Vault`, add a third fetch and a `splat === "graph"` branch (place before the `portal` lookup):

```tsx
const graph = useAsyncData(useCallback(() => guard(fetchGraph(token)), [guard, token]));
...
if (splat === "graph") {
  return (
    <>
      <Link className="ui-stat-label" to="/knowledge">← Portals</Link>
      <PageHeader title="Graph" description="Every note and the wikilinks between them." />
      {graph.data ? <Graph graph={graph.data} /> : <EmptyState message={graph.error ?? "Loading…"} />}
    </>
  );
}
```

Pass `graph={graph.data}` into `ArticlePage` (add prop `graph: VaultGraph | null`) and render under the article, only when the neighbourhood has more than one node:

```tsx
{graph && neighborhood(graph, path).nodes.length > 1 && (
  <section><h2>Local graph</h2><Graph graph={neighborhood(graph, path)} current={path} /></section>
)}
```

- [ ] **Step 6: Run everything**

Run (from `frontend/`): `npm run test && npm run lint && npm run build` → all PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src
git commit -m "feat(knowledge): vault and local graph views"
```

---

### Task 6: Docs, real-vault check and final verification

**Files:**
- Modify: `README.md`, `CLAUDE.md` (second-brain exception paragraph: new read endpoints), `scripts/README.md` (frontmatter now forwarded)
- Modify: `docs/superpowers/specs/2026-10-05-knowledge-wiki-viewer-design.md` (append the "Deviations" list from this plan)

- [ ] **Step 1: Update docs.** In `CLAUDE.md` extend the second-brain exception sentence: reads now also include `GET /api/v1/second-brain/portals` and `/graph`, and wikilinks are resolved at sync time into a `links` table in the same SQLite file. In `README.md` document the new routes (`/knowledge`, `/knowledge/<portal>`, `/knowledge/<note path>`, `/knowledge/graph`, `/knowledge/all`). Append the Deviations list to the spec.

- [ ] **Step 2: Full automated verification**

```bash
cd backend && pytest -q && ruff check .
cd ../frontend && npm run test && npm run lint && npm run build
```
Expected: all green.

- [ ] **Step 3: Check against the real vault locally**

Start the backend with a throwaway DB, push the real vault to it, and open the UI (do not touch production):

```powershell
cd backend
$env:INTERNAL_REPORT_SECRET="dev-write"; $env:DASHBOARD_READ_TOKEN="dev-read"; $env:SECOND_BRAIN_DB_PATH="$env:TEMP\sb-dev.db"
uvicorn app.main:app --port 8000
```
In a second terminal set `AISAAC_DASHBOARD_URL=http://localhost:8000` and `AISAAC_INTERNAL_SECRET=dev-write` (see `scripts/push_common.py` for how config is read), run `python scripts/second_brain_push.py`, then `npm run dev` in `frontend/` (token `dev-read`). Check with the browser tools at 1280px and 390px wide:
- `/knowledge`: portal cards with counts/descriptions, search finds "scale to zero", recently updated list.
- A wiki article (e.g. `wikis/deployment-ops/fly-scale-to-zero`): infobox, TOC anchors scroll, a hover preview appears, a red link renders for a missing target, See also / What links here populated, local graph shows.
- `/knowledge/wikis/apps` portal page; `/knowledge/graph`; `/knowledge/all`; `/knowledge/nope/missing` shows "No such article."; old `/knowledge?note=wikis%2Fapps%2Findex.md` redirects.
- Mobile: no horizontal scroll, infobox stacks above content.

- [ ] **Step 4: Commit and report.** Commit docs, then summarize results (including anything in Step 3 that did not work) to the user before any push, PR or deploy. Deploy to Fly and the first production re-sync (`python scripts/second_brain_push.py`) are separate, user-approved actions.

```bash
git add README.md CLAUDE.md scripts/README.md docs
git commit -m "docs: knowledge wiki viewer"
```
