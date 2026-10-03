import type { NoteListItem } from "../../types";

export const VAULT = "second-brain";

export const obsidianUrl = (path: string): string =>
  `obsidian://open?vault=${encodeURIComponent(VAULT)}&file=${encodeURIComponent(path.replace(/\.md$/, ""))}`;

/** Rewrites [[Target|Label]] to in-app links; targets that match no synced note become plain text. */
export function linkWikilinks(body: string, notes: NoteListItem[]): string {
  const byName = new Map<string, string>();
  for (const note of notes) {
    for (const name of [note.title, ...note.aliases]) byName.set(name.toLowerCase(), note.path);
  }
  return body.replace(/\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]+))?\]\]/g, (_m, target: string, label?: string) => {
    const path = byName.get(target.trim().toLowerCase());
    const text = (label ?? target).trim();
    return path ? `[${text}](?note=${encodeURIComponent(path)})` : text;
  });
}
