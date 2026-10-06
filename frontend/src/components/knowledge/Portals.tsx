import { useState } from "react";
import { Link } from "react-router-dom";

import type { NoteListItem, Portal } from "../../types";
import { noteHref, portalLabel } from "../dashboard/secondBrain";
import { Card } from "../primitives/Card";
import { EmptyState } from "../primitives/EmptyState";
import { PageHeader } from "../primitives/PageHeader";

// "wikis/apps" holds notes under that folder; a bare "projects" holds notes directly in projects/.
const inPortal = (n: NoteListItem, id: string) => n.path.startsWith(`${id}/`);

const byTitle = (a: NoteListItem, b: NoteListItem) => a.title.localeCompare(b.title);

function NoteLinks({ notes }: { notes: NoteListItem[] }) {
  return (
    <ul className="wiki-refs">
      {notes.map((n) => (
        <li key={n.path}>
          <Link to={noteHref(n.path)}>{n.title}</Link>
        </li>
      ))}
    </ul>
  );
}

export function Landing({ portals, notes }: { portals: Portal[]; notes: NoteListItem[] }) {
  const [q, setQ] = useState("");
  const needle = q.trim().toLowerCase();
  const hits = needle
    ? notes
        .filter((n) => `${n.title} ${n.aliases.join(" ")}`.toLowerCase().includes(needle))
        .sort(byTitle)
        .slice(0, 50)
    : [];
  const recent = notes
    .filter((n) => n.updated)
    .sort((a, b) => (b.updated! > a.updated! ? 1 : -1))
    .slice(0, 8);
  return (
    <>
      <PageHeader
        title="Knowledge"
        description="Read-only copy of the Obsidian vault, organised as wiki portals. Edit in Obsidian, then push."
      />
      <input
        className="kb-search"
        type="search"
        placeholder="Search articles"
        aria-label="Search articles"
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />
      {needle ? (
        hits.length ? <NoteLinks notes={hits} /> : <EmptyState message="No matching articles." />
      ) : (
        <>
          <div className="portal-grid">
            {[...portals]
              .sort((a, b) => Number(b.id.startsWith("wikis/")) - Number(a.id.startsWith("wikis/")))
              .map((p) => (
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
          <p className="ui-stat-label">
            <Link to="/knowledge/graph">Graph view</Link> · <Link to="/knowledge/all">All pages</Link>
          </p>
        </>
      )}
    </>
  );
}

export function PortalPage({ portal, notes }: { portal: Portal; notes: NoteListItem[] }) {
  const articles = notes.filter((n) => inPortal(n, portal.id)).sort(byTitle);
  return (
    <>
      <Link className="ui-stat-label" to="/knowledge">
        ← Portals
      </Link>
      <PageHeader title={portal.title} description={portal.description || `Articles in ${portalLabel(portal.id)}`} />
      {articles.length ? <NoteLinks notes={articles} /> : <EmptyState message="No articles in this portal." />}
    </>
  );
}
