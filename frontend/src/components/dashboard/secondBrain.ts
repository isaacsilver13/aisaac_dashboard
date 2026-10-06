import type { Note } from "../../types";

export const VAULT = "second-brain";
export const MISSING = "#missing";
const PREFIX = "/knowledge/";

export const obsidianUrl = (path: string): string =>
  `obsidian://open?vault=${encodeURIComponent(VAULT)}&file=${encodeURIComponent(path.replace(/\.md$/, ""))}`;

const encodeSegment = (s: string) =>
  encodeURIComponent(s).replace(/[()]/g, (c) => `%${c.charCodeAt(0).toString(16).toUpperCase()}`);

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
  return body.replace(/\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]+))?\]\]/g, (_m, target: string, label?: string) => {
    const key = target.trim().toLowerCase();
    const text = (label ?? target).trim();
    if (!(key in linkMap)) return text;
    const path = linkMap[key];
    return `[${text}](${path ? noteHref(path) : MISSING})`;
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
