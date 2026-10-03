import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Markdown from "react-markdown";

import { FinancialsAuthError, fetchNote, fetchNotes } from "../api";
import { linkWikilinks, obsidianUrl } from "../components/dashboard/secondBrain";
import { Card } from "../components/primitives/Card";
import { EmptyState } from "../components/primitives/EmptyState";
import { PageHeader } from "../components/primitives/PageHeader";
import { Table, type Column } from "../components/primitives/Table";
import { readToken, writeToken } from "../token";
import type { Note, NoteListItem } from "../types";

const noteColumns: Column<NoteListItem>[] = [
  {
    key: "title",
    header: "Title",
    sortValue: (n) => n.title,
    render: (n) => <Link to={`?note=${encodeURIComponent(n.path)}`}>{n.title}</Link>,
  },
  { key: "folder", header: "Folder", sortValue: (n) => n.folder, render: (n) => n.folder },
  { key: "status", header: "Status", sortValue: (n) => n.status, render: (n) => n.status ?? "—" },
];

export default function SecondBrain() {
  const [token, setToken] = useState(readToken);
  const [draft, setDraft] = useState("");
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
    if (token && path) fetchNote(token, path).then(setNote).catch(fail);
  }, [token, path]);

  const shown = note && note.path === path ? note : null;
  const body = useMemo(() => (shown ? linkWikilinks(shown.body, all) : ""), [shown, all]);
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
      {shown ? (
        <>
          <Link className="ui-stat-label" to="/knowledge">← All notes</Link>
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
        </>
      ) : (
        <Table
          columns={noteColumns}
          rows={all}
          rowKey={(n) => n.path}
          searchText={(n) => `${n.title} ${n.path} ${n.aliases.join(" ")}`}
          filters={[{ label: "Folder", value: (n) => n.folder }]}
          emptyMessage="No notes. Run scripts/second_brain_push.py."
        />
      )}
    </>
  );
}
