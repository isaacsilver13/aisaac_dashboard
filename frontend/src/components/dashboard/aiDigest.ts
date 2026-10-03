import type { DigestItem, DigestSourceStat } from "../../types";

export type HeadlinePart = { text: string } | { id: number };

/**
 * Splits "Lead story [12] and [3]" into text and citation parts. A marker only becomes a citation
 * when its id is one of `ids`; anything else stays as plain text so it can never link somewhere.
 */
export function splitHeadline(headline: string, ids: Set<number>): HeadlinePart[] {
  const parts: HeadlinePart[] = [];
  let last = 0;
  for (const match of headline.matchAll(/\[(\d+)\]/g)) {
    const id = Number(match[1]);
    if (!ids.has(id)) continue;
    const index = match.index ?? 0;
    if (index > last) parts.push({ text: headline.slice(last, index) });
    parts.push({ id });
    last = index + match[0].length;
  }
  if (last < headline.length) parts.push({ text: headline.slice(last) });
  return parts;
}

/** Only http(s) URLs may become links; anything else (javascript:, data:) renders as plain text. */
export const safeHref = (url: string): string | null => (/^https?:\/\//i.test(url) ? url : null);

export function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
}

/** Highest priority first, newest first within a priority. */
export const byPriority = (items: DigestItem[]): DigestItem[] =>
  [...items].sort((a, b) => b.priority - a.priority || (b.published_at ?? "").localeCompare(a.published_at ?? ""));

export function failedSources(stats: Record<string, DigestSourceStat> | undefined): { name: string; error: string }[] {
  return Object.entries(stats ?? {}).flatMap(([name, stat]) => (stat.error ? [{ name, error: stat.error }] : []));
}
