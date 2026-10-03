import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { fetchAiDigest } from "../../api";
import { readToken } from "../../token";
import type { Digest } from "../../types";
import { Badge } from "../primitives/Badge";
import { Card } from "../primitives/Card";
import { Stat } from "../primitives/Stat";
import { byPriority, safeHref } from "./aiDigest";

/** Today's top items. Needs the dashboard token; shows nothing until a digest has been pushed. */
export function AiDigestPanel() {
  const [token] = useState(readToken);
  const [digest, setDigest] = useState<Digest | null>(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    fetchAiDigest(token)
      .then((next) => !cancelled && setDigest(next))
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [token]);

  if (!digest || digest.items.length === 0) return null;
  return (
    <Card aria-label="AI digest">
      <Stat label={`AI digest · ${digest.digest_date}`} value={`${digest.items.length} items`} />
      <ul className="digest-top">
        {byPriority(digest.items).slice(0, 3).map((item) => {
          const href = safeHref(item.url);
          return (
            <li key={item.id}>
              <Badge tone={item.priority >= 4 ? "info" : "neutral"}>P{item.priority}</Badge>
              {href ? (
                <a href={href} target="_blank" rel="noopener noreferrer">{item.title}</a>
              ) : (
                <span>{item.title}</span>
              )}
              <span className="ui-stat-label">{item.source}</span>
            </li>
          );
        })}
      </ul>
      <div className="ui-stat-label" style={{ marginTop: 10 }}>
        <Link to="/ai-digest">Open the full digest</Link>
      </div>
    </Card>
  );
}
