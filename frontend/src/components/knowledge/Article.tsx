import { isValidElement, type ReactNode } from "react";
import Markdown from "react-markdown";
import { Link } from "react-router-dom";

import {
  headings,
  infoboxRows,
  linkWikilinks,
  MISSING,
  noteHref,
  obsidianUrl,
  pathFromHref,
  portalLabel,
  slugify,
} from "../dashboard/secondBrain";
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
          <li key={r.path}>
            <Link to={noteHref(r.path)}>{r.title}</Link>
          </li>
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
                <div key={k}>
                  <dt>{k}</dt>
                  <dd>{v}</dd>
                </div>
              ))}
            </dl>
          </aside>
        )}
        {toc.length >= 3 && (
          <nav className="wiki-toc" aria-label="Contents">
            <strong>Contents</strong>
            <ol>
              {toc.map((h) => (
                <li key={h.id} className={`toc-${h.level}`}>
                  <a href={`#${h.id}`}>{h.text}</a>
                </li>
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
                if (href === MISSING) {
                  return (
                    <span className="wiki-redlink" title="No article yet">
                      {children}
                    </span>
                  );
                }
                const path = pathFromHref(href);
                if (!path) return <a href={href}>{children}</a>;
                const preview = note.previews[path];
                return (
                  <span className="wiki-link">
                    <Link to={href}>{children}</Link>
                    {preview && (
                      <span role="tooltip" className="wiki-preview">
                        {preview}
                      </span>
                    )}
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
