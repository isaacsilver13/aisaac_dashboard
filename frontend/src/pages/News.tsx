import { useCallback, useState } from "react";
import { Bookmark, BookmarkSolid, Refresh, Xmark } from "iconoir-react";

import { fetchNews, setNewsState } from "../api";
import { Badge } from "../components/primitives/Badge";
import { EmptyState } from "../components/primitives/EmptyState";
import { ErrorState } from "../components/primitives/ErrorState";
import { PageHeader } from "../components/primitives/PageHeader";
import { Table, type Column } from "../components/primitives/Table";
import { useAsyncData } from "../hooks/useAsyncData";
import { centralTimestamp } from "../time";
import { readToken, readWriteToken } from "../token";
import type { NewsItem, NewsState } from "../types";

export default function News() {
  const token = readToken();
  const { data, loading, refreshing, error, reload } = useAsyncData(
    useCallback((force: boolean) => fetchNews(token, force), [token]),
  );
  const [actionError, setActionError] = useState<string | null>(null);
  const canWrite = Boolean(readWriteToken());

  async function mark(item: NewsItem, state: NewsState) {
    setActionError(null);
    try {
      await setNewsState(item.id, state);
      await reload();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Update failed.");
    }
  }

  const columns: Column<NewsItem>[] = [
    {
      key: "title",
      header: "Headline",
      sortValue: (n) => n.title,
      render: (n) => (
        <>
          <a href={n.url} target="_blank" rel="noopener noreferrer">{n.title}</a>
          <div className="muted" style={{ fontSize: 12 }}>{n.source} · {n.why}</div>
        </>
      ),
    },
    { key: "topic", header: "Topic", sortValue: (n) => n.topic, render: (n) => <Badge tone="info">{n.topic}</Badge> },
    { key: "published", header: "Published", sortValue: (n) => n.published_at, render: (n) => centralTimestamp(n.published_at) },
    { key: "score", header: "Score", align: "right", sortValue: (n) => n.score, render: (n) => n.score.toFixed(2) },
    {
      key: "actions",
      header: "",
      render: (n) => (
        <span style={{ display: "inline-flex", gap: 8 }}>
          <button
            type="button"
            className="refresh-button"
            disabled={!canWrite}
            title={canWrite ? undefined : "Add your write token in Settings"}
            aria-label={n.state === "saved" ? `Unsave ${n.title}` : `Save ${n.title}`}
            onClick={() => void mark(n, n.state === "saved" ? "new" : "saved")}
          >
            {n.state === "saved" ? <BookmarkSolid width={16} height={16} /> : <Bookmark width={16} height={16} />}
          </button>
          <button
            type="button"
            className="refresh-button"
            disabled={!canWrite}
            title={canWrite ? undefined : "Add your write token in Settings"}
            aria-label={`Dismiss ${n.title}`}
            onClick={() => void mark(n, "dismissed")}
          >
            <Xmark width={16} height={16} />
          </button>
        </span>
      ),
    },
  ];

  const failing = data?.sources.filter((s) => s.last_error) ?? [];

  return (
    <>
      <PageHeader
        title="News"
        description="Source-linked reading picks ranked by recency and topic keywords. Headlines link to the publisher."
        lastUpdated={data?.freshness_at ? centralTimestamp(data.freshness_at) : undefined}
        actions={
          <button className="refresh-button" type="button" onClick={() => void reload(true)} disabled={refreshing || !token}>
            <Refresh width={16} height={16} className={refreshing ? "spin" : ""} aria-hidden="true" />
            {refreshing ? "Refreshing" : "Refresh"}
          </button>
        }
      />
      {!token ? (
        <EmptyState message="Add your dashboard token in Settings to view news." />
      ) : error ? (
        <ErrorState message={error} onRetry={() => void reload()} />
      ) : loading || !data ? null : (
        <>
          {!data.freshness_at && <EmptyState message="No feed has refreshed successfully yet." />}
          {data.freshness_at && failing.length > 0 && (
            <p role="status" className="muted">
              Showing last saved items; {failing.length} source{failing.length === 1 ? "" : "s"} failed to refresh:{" "}
              {failing.map((s) => s.source).join(", ")}.
            </p>
          )}
          {actionError && <p role="alert">{actionError}</p>}
          <Table
            columns={columns}
            rows={data.items}
            rowKey={(n) => String(n.id)}
            searchText={(n) => `${n.title} ${n.source} ${n.topic}`}
            filters={[
              { label: "Topic", value: (n) => n.topic },
              { label: "Saved", value: (n) => (n.state === "saved" ? "saved" : "other") },
            ]}
            emptyMessage="No articles match."
          />
        </>
      )}
    </>
  );
}
