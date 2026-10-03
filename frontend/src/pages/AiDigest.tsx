import { useCallback, useState, type ReactNode } from "react";
import { ArrowUpRight } from "iconoir-react";

import { fetchAiDigest, fetchAiDigestDates } from "../api";
import { byPriority, failedSources, hostOf, safeHref, splitHeadline } from "../components/dashboard/aiDigest";
import { Badge } from "../components/primitives/Badge";
import { Card } from "../components/primitives/Card";
import { EmptyState } from "../components/primitives/EmptyState";
import { ErrorState } from "../components/primitives/ErrorState";
import { PageHeader } from "../components/primitives/PageHeader";
import { Table, type Column } from "../components/primitives/Table";
import { useAsyncData } from "../hooks/useAsyncData";
import { readToken } from "../token";
import type { Digest, DigestItem } from "../types";

const day = (iso: string | null) => (iso ? new Date(iso).toLocaleDateString([], { month: "short", day: "numeric" }) : "—");
const stamp = (iso: string) => new Date(iso).toLocaleString([], { dateStyle: "short", timeStyle: "short" });

function SourceLink({ item, children }: { item: DigestItem; children: ReactNode }) {
  const href = safeHref(item.url);
  if (!href) return <>{children}</>;
  return (
    <a href={href} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  );
}

function Cite({ item }: { item: DigestItem }) {
  const href = safeHref(item.url);
  return href ? (
    <a className="digest-cite" href={href} target="_blank" rel="noopener noreferrer" title={item.title}>
      [{item.id}]
    </a>
  ) : (
    <span className="digest-cite">[{item.id}]</span>
  );
}

function Headline({ digest }: { digest: Digest }) {
  const byId = new Map(digest.items.map((item) => [item.id, item]));
  const parts = splitHeadline(digest.headline ?? "", new Set(byId.keys()));
  if (parts.length === 0) return null;
  return (
    <p className="digest-headline">
      {parts.map((part, index) => {
        if ("text" in part) return <span key={index}>{part.text}</span>;
        const item = byId.get(part.id);
        return item ? <Cite key={index} item={item} /> : null;
      })}
    </p>
  );
}

const columns: Column<DigestItem>[] = [
  {
    key: "priority",
    header: "Priority",
    sortValue: (i) => i.priority,
    render: (i) => <Badge tone={i.priority >= 4 ? "info" : "neutral"}>P{i.priority}</Badge>,
  },
  {
    key: "item",
    header: "Item",
    sortValue: (i) => i.title,
    render: (i) => (
      <div className="digest-item">
        <span className="digest-id">[{i.id}]</span>
        <SourceLink item={i}>
          {i.title}
          {safeHref(i.url) && <ArrowUpRight width={12} height={12} aria-hidden="true" />}
        </SourceLink>
        <p className="digest-summary">{i.summary}</p>
        {i.why_it_matters && <p className="digest-why">{i.why_it_matters}</p>}
      </div>
    ),
  },
  { key: "category", header: "Category", sortValue: (i) => i.category, render: (i) => i.category },
  {
    key: "source",
    header: "Source",
    sortValue: (i) => i.source,
    render: (i) => (
      <>
        {i.source}
        <span className="digest-host">{hostOf(i.url)}</span>
      </>
    ),
  },
  { key: "published", header: "Published", sortValue: (i) => i.published_at, render: (i) => day(i.published_at) },
];

export default function AiDigest() {
  const token = readToken();
  const [date, setDate] = useState("");
  const { data, loading, error, reload } = useAsyncData(
    useCallback(async () => {
      const [digest, dates] = await Promise.all([fetchAiDigest(token, date || undefined), fetchAiDigestDates(token)]);
      return { digest, dates };
    }, [token, date]),
  );

  const digest = data?.digest;
  const dates = data?.dates ?? [];
  const failed = failedSources(digest?.source_stats);

  return (
    <>
      <PageHeader
        title="AI Digest"
        description="Daily AI news and practice, summarized and ranked. Every item links to its original source so you can check it yourself."
        lastUpdated={digest?.generated_at ? stamp(digest.generated_at) : undefined}
        actions={
          dates.length > 1 ? (
            <select
              className="digest-date-select"
              aria-label="Digest date"
              value={date || dates[0]}
              onChange={(event) => setDate(event.target.value === dates[0] ? "" : event.target.value)}
            >
              {dates.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          ) : undefined
        }
      />
      {!token ? (
        <EmptyState message="Add your dashboard token in Settings to view the AI digest." />
      ) : error ? (
        <ErrorState message={error} onRetry={() => void reload()} />
      ) : loading || !data ? null : !digest || digest.items.length === 0 ? (
        <EmptyState message="No digest yet. The AI Digest workflow runs daily; run it from the GitHub Actions tab to build the first one." />
      ) : (
        <>
          <Card aria-label="Briefing">
            <p className="eyebrow">{digest.digest_date}</p>
            <Headline digest={digest} />
            <div className="digest-meta">
              <span>
                {digest.items.length} items{digest.model ? ` · summarized by ${digest.model}` : ""}
              </span>
              {failed.length > 0 && (
                <Badge tone="warning">{failed.length === 1 ? "1 source failed" : `${failed.length} sources failed`}</Badge>
              )}
            </div>
            {failed.length > 0 && (
              <details className="digest-failures">
                <summary>Source problems</summary>
                <ul>
                  {failed.map((f) => (
                    <li key={f.name}>{f.name}: {f.error}</li>
                  ))}
                </ul>
              </details>
            )}
          </Card>
          <div className="digest-section">
            <Table
              columns={columns}
              rows={byPriority(digest.items)}
              rowKey={(i) => String(i.id)}
              searchText={(i) => `${i.title} ${i.summary} ${i.why_it_matters} ${i.source}`}
              filters={[{ label: "Category", value: (i) => i.category }, { label: "Source", value: (i) => i.source }]}
              emptyMessage="No items match."
            />
          </div>
        </>
      )}
    </>
  );
}
