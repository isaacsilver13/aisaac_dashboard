"""Source-linked news from an allowlist of public RSS/Atom feeds.

Headlines and links only (never excerpts or images), always pointing back to the
publisher. Ranking is transparent: recency plus topic-keyword hits, with the
reason stored per item. No scraping, no undocumented endpoints, no LLM.
"""

from __future__ import annotations

import logging
import math
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Callable, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

from . import personal_store

logger = logging.getLogger("aisaac.personal")

# (feed url, publisher, topic). Edit here to change sources; the browser never supplies a URL.
FEEDS: tuple[tuple[str, str, str], ...] = (
    ("https://www.federalreserve.gov/feeds/press_all.xml", "Federal Reserve", "economics"),
    ("https://feeds.npr.org/1017/rss.xml", "NPR Economy", "economics"),
    ("https://feeds.npr.org/1006/rss.xml", "NPR Business", "finance"),
    ("https://www.sec.gov/news/pressreleases.rss", "SEC", "finance"),
    ("https://feeds.arstechnica.com/arstechnica/index", "Ars Technica", "technology"),
    ("https://feeds.npr.org/1019/rss.xml", "NPR Technology", "technology"),
    ("https://rss.arxiv.org/rss/math", "arXiv math", "mathematics"),
    ("https://www.quantamagazine.org/feed/", "Quanta Magazine", "mathematics"),
    ("https://rss.arxiv.org/rss/stat.ML", "arXiv stat.ML", "data science"),
    ("https://feeds.npr.org/1014/rss.xml", "NPR Politics", "politics"),
)
TOPICS = ("economics", "finance", "technology", "mathematics", "data science", "politics")

KEYWORDS: dict[str, tuple[str, ...]] = {
    "economics": ("inflation", "gdp", "rates", "recession", "jobs", "tariff", "economy"),
    "finance": ("stocks", "market", "bond", "bank", "earnings", "ipo", "sec"),
    "technology": ("ai", "chip", "software", "cloud", "cyber", "open source", "model"),
    "mathematics": ("theorem", "proof", "conjecture", "prime", "geometry", "algebra"),
    "data science": ("data", "learning", "statistic", "dataset", "regression", "neural"),
    "politics": ("congress", "senate", "election", "white house", "supreme court", "bill"),
}

MAX_AGE = timedelta(days=7)
MAX_BYTES = 2_000_000
_TRACKING = ("utm_", "fbclid", "gclid", "mc_", "ref")

Fetch = Callable[[str], bytes]


def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [(k, v) for k, v in parse_qsl(parts.query) if not k.lower().startswith(_TRACKING)]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _parse_date(text: Optional[str]) -> Optional[datetime]:
    if not text:
        return None
    text = text.strip()
    try:
        parsed = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def parse_feed(xml_bytes: bytes) -> list[dict]:
    """Return [{title, url, published_at}] from RSS 2.0, RSS 1.0 or Atom; raises on bad XML."""
    # Feeds never need a DTD; refusing one rules out entity-expansion/XXE without a new dependency.
    # NUL bytes mean UTF-16/32, which would hide "<!DOCTYPE" from the byte match below.
    upper = xml_bytes.upper()
    if b"\x00" in xml_bytes or b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise ValueError("DTD not allowed")
    root = ET.fromstring(xml_bytes)
    out = []
    for entry in root.iter():
        if _local(entry.tag) not in ("item", "entry"):
            continue
        fields: dict[str, str] = {}
        for child in entry:
            name = _local(child.tag)
            if name == "link":
                fields.setdefault("link", child.get("href") or (child.text or ""))
            elif name in ("title", "pubDate", "published", "updated", "date"):
                fields.setdefault(name, child.text or "")
        published = _parse_date(
            fields.get("pubDate") or fields.get("published")
            or fields.get("date") or fields.get("updated")
        )
        title, link = fields.get("title", "").strip(), fields.get("link", "").strip()
        if title and link.startswith(("http://", "https://")):
            out.append({"title": title, "url": canonical_url(link), "published_at": published})
    return out


def score_item(title: str, topic: str, published_at: datetime, now: datetime) -> tuple[float, str]:
    age_hours = max((now - published_at).total_seconds() / 3600, 0)
    lowered = title.lower()
    hits = [k for k in KEYWORDS[topic] if re.search("(?<![a-z0-9])" + re.escape(k), lowered)]
    score = 1 / (1 + age_hours / 24) + 0.5 * min(len(hits), 3)
    age = f"{math.floor(age_hours)}h old" if age_hours < 48 else f"{round(age_hours / 24)}d old"
    why = f"{topic} source, {age}" + (f", matches: {', '.join(hits)}" if hits else "")
    return round(score, 3), why


def _http_fetch(url: str) -> bytes:
    with httpx.stream(
        "GET", url, timeout=10.0, follow_redirects=True,
        headers={"User-Agent": "aisaac-dashboard/0.1 (personal feed reader)"},
    ) as response:
        response.raise_for_status()
        body = b""
        for chunk in response.iter_bytes():
            body += chunk
            if len(body) > MAX_BYTES:
                raise ValueError("feed too large")
        return body


def _refresh_feed(feed: tuple[str, str, str], fetch: Fetch, now: datetime) -> None:
    url, source, topic = feed
    try:
        entries = parse_feed(fetch(url))
    except (httpx.HTTPError, ET.ParseError, ValueError) as exc:
        # Store a short code only; the exception text could echo upstream content.
        code = "parse_failed" if isinstance(exc, (ET.ParseError, ValueError)) else "fetch_failed"
        logger.warning("News feed %s failed: %s", source, type(exc).__name__)
        personal_store.record_feed(url, source, code)
        return
    seen: set[str] = set()
    for entry in entries:
        if entry["url"] in seen:  # feeds list newest first; keep the first occurrence
            continue
        seen.add(entry["url"])
        published = entry["published_at"] or now
        if now - published > MAX_AGE:
            continue
        score, why = score_item(entry["title"], topic, published, now)
        personal_store.upsert_item({
            "url": entry["url"], "title": entry["title"], "source": source, "topic": topic,
            "published_at": published.isoformat(), "score": score, "why": why,
        })
    personal_store.record_feed(url, source, None)


def refresh(fetch: Fetch = _http_fetch, now: Optional[datetime] = None) -> None:
    """Fetch every allowlisted feed (bounded parallelism); one failing feed never affects others."""
    now = now or datetime.now(timezone.utc)
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda feed: _refresh_feed(feed, fetch, now), FEEDS))
