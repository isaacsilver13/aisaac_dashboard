import { useCallback, useState, type FormEvent } from "react";
import { Link, Navigate, useParams, useSearchParams } from "react-router-dom";

import { FinancialsAuthError, fetchNote, fetchNotes, fetchPortals } from "../api";
import { noteHref } from "../components/dashboard/secondBrain";
import { Article } from "../components/knowledge/Article";
import { Landing, PortalPage } from "../components/knowledge/Portals";
import { Card } from "../components/primitives/Card";
import { EmptyState } from "../components/primitives/EmptyState";
import { Table, type Column } from "../components/primitives/Table";
import { useAsyncData } from "../hooks/useAsyncData";
import { readToken, writeToken } from "../token";
import type { NoteListItem } from "../types";

const noteColumns: Column<NoteListItem>[] = [
  {
    key: "title",
    header: "Title",
    sortValue: (n) => n.title,
    render: (n) => <Link to={noteHref(n.path)}>{n.title}</Link>,
  },
  { key: "folder", header: "Folder", sortValue: (n) => n.folder, render: (n) => n.folder },
  { key: "status", header: "Status", sortValue: (n) => n.status ?? "", render: (n) => n.status ?? "—" },
];

type Guard = <T>(call: Promise<T>) => Promise<T>;

function Gate({ onToken }: { onToken: (token: string) => void }) {
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
        <label className="ui-stat-label" htmlFor="sb-token">
          Access token for the second brain
        </label>
        <input
          id="sb-token"
          type="password"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          autoComplete="off"
        />
        <button className="refresh-button" type="submit">
          Unlock
        </button>
      </form>
    </Card>
  );
}

export default function SecondBrain() {
  const [token, setToken] = useState(readToken);
  const onAuthError = useCallback(() => {
    writeToken("");
    setToken("");
  }, []);
  if (!token) return <Gate onToken={setToken} />;
  return <Vault token={token} onAuthError={onAuthError} />;
}

function Vault({ token, onAuthError }: { token: string; onAuthError: () => void }) {
  const guard = useCallback<Guard>(
    async (call) => {
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
        <Link className="ui-stat-label" to="/knowledge">
          ← Portals
        </Link>
        <Table
          columns={noteColumns}
          rows={notes.data}
          rowKey={(n) => n.path}
          searchText={(n) => `${n.title} ${n.path} ${n.aliases.join(" ")}`}
          filters={[{ label: "Folder", value: (n) => n.folder }]}
          emptyMessage="No notes. Run scripts/second_brain_push.py."
        />
      </>
    );
  }
  const portal = portals.data.find((p) => p.id === splat);
  if (portal) return <PortalPage portal={portal} notes={notes.data} />;
  return <ArticlePage token={token} path={`${splat}.md`} guard={guard} />;
}

function ArticlePage({ token, path, guard }: { token: string; path: string; guard: Guard }) {
  const { data, error } = useAsyncData(useCallback(() => guard(fetchNote(token, path)), [guard, token, path]));
  if (error) {
    return (
      <>
        <Link className="ui-stat-label" to="/knowledge">
          ← Portals
        </Link>
        <EmptyState message="No such article." />
      </>
    );
  }
  if (!data || data.path !== path) return <EmptyState message="Loading…" />;
  return (
    <>
      <Link className="ui-stat-label" to={`/knowledge/${data.portal}`}>
        ← {data.portal}
      </Link>
      <Article note={data} />
    </>
  );
}
