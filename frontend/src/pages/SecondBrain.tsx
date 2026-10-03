import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Markdown from "react-markdown";

import { FinancialsAuthError, fetchNote, fetchNotes } from "../api";
import { linkWikilinks, obsidianUrl } from "../components/dashboard/secondBrain";
import { Card } from "../components/primitives/Card";
import { EmptyState } from "../components/primitives/EmptyState";
import { PageHeader } from "../components/primitives/PageHeader";
import { readToken, writeToken } from "../token";
import type { Note, NoteListItem } from "../types";

export default function SecondBrain() {
  const [token, setToken] = useState(readToken);
  const [draft, setDraft] = useState("");
  const [query, setQuery] = useState("");
  const [notes, setNotes] = useState<NoteListItem[]>([]);
  const [all, setAll] = useState<NoteListItem[]>([]);
  const [note, setNote] = useState<Note | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [params] = useSearchParams();
  const path = params.get("note");

  const fail = (err: unknown) => {
    if (err instanceof FinancialsAuthError) {
      writeToken("");
      setToken("");
      setError("That token was not accepted.");
    } else setError(err instanceof Error ? err.message : "Request failed.");
  };

  // The full list resolves wikilinks; the searched list drives the sidebar.
  useEffect(() => {
    if (token) fetchNotes(token).then(setAll).catch(fail);
  }, [token]);
  useEffect(() => {
    if (token) fetchNotes(token, query).then(setNotes).catch(fail);
  }, [token, query]);
  useEffect(() => {
    if (token && path) fetchNote(token, path).then(setNote).catch(fail);
  }, [token, path]);

  const shown = note && note.path === path ? note : null;
  const body = useMemo(() => (shown ? linkWikilinks(shown.body, all) : ""), [shown, all]);
  const grouped = useMemo(() => {
    const out = new Map<string, NoteListItem[]>();
    for (const n of notes) {
      const key = n.folder === "wikis" ? n.path.split("/")[1] : n.folder;
      out.set(key, [...(out.get(key) ?? []), n]);
    }
    return [...out.entries()];
  }, [notes]);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!draft.trim()) return;
    writeToken(draft.trim());
    setToken(draft.trim());
    setDraft("");
  }

  if (!token) {
    return (
      <Card>
        <form className="token-form" onSubmit={submit}>
          <label className="ui-stat-label" htmlFor="sb-token">Access token for the second brain</label>
          <input id="sb-token" type="password" value={draft} onChange={(e) => setDraft(e.target.value)} autoComplete="off" />
          <button className="refresh-button" type="submit">Unlock</button>
          {error && <span role="alert" className="ui-stat-label">{error}</span>}
        </form>
      </Card>
    );
  }

  return (
    <>
      <PageHeader title="Second Brain" description="Read-only copy of the Obsidian vault. Edit notes in Obsidian, then push." />
      {error && <EmptyState message={error} />}
      <div style={{ display: "grid", gridTemplateColumns: "minmax(200px, 280px) 1fr", gap: 16 }}>
        <aside aria-label="Notes">
          <input
            type="search"
            placeholder="Search notes"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            style={{ width: "100%", marginBottom: 12 }}
          />
          {grouped.map(([group, items]) => (
            <section key={group}>
              <h3 className="ui-stat-label">{group}</h3>
              <ul className="cost-by-app">
                {items.map((n) => (
                  <li key={n.path}>
                    <Link to={`?note=${encodeURIComponent(n.path)}`}>{n.title}</Link>
                  </li>
                ))}
              </ul>
            </section>
          ))}
          {notes.length === 0 && <EmptyState message="No notes. Run scripts/second_brain_push.py." />}
        </aside>
        <article aria-label="Note">
          {shown ? (
            <Card>
              <a className="ui-stat-label" href={obsidianUrl(shown.path)}>Open in Obsidian</a>
              <Markdown
                components={{
                  a: ({ href, children }) =>
                    href?.startsWith("?note=") ? <Link to={href}>{children}</Link> : <a href={href}>{children}</a>,
                }}
              >
                {body}
              </Markdown>
            </Card>
          ) : (
            <EmptyState message="Pick a note." />
          )}
        </article>
      </div>
    </>
  );
}
