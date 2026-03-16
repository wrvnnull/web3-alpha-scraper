"""
scrapers/news_scraper.py — Crypto News RSS Scraper
----------------------------------------------------
RSS feeds are an underrated goldmine for early alpha because newsrooms
publish articles 1–2 hours before they appear on social media aggregators.
We scrape multiple feeds in parallel and filter by our keyword lists.

The beauty of RSS: no auth required, stable, fast, and parseable with
standard Python libraries. We use `feedparser` which handles all the
nasty XML edge cases for us.

Feeds covered:
  - CoinTelegraph (high volume, broad coverage)
  - Decrypt (DeFi + AI focus)
  - The Block (institutional + protocol launches)
  - Blockworks (institutional DeFi)
  - CryptoBriefing (deep-dive reviews)
  - CryptoSlate (project launches, ICOs)
  - CoinDesk (mainstream + regulatory)
"""

import feedparser
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from config import NEWS_RSS_FEEDS, HIGH_VALUE_KEYWORDS, WEB3_KEYWORDS
from utils.scorer import score_project
from utils.dedup import is_new

# Map RSS feed URL → short source name for the scorer
FEED_SOURCE_MAP = {
    "cointelegraph.com": "cointelegraph",
    "decrypt.co":        "decrypt",
    "theblock.co":       "theblock",
    "blockworks.co":     "blockworks",
    "cryptobriefing.com":"cryptobriefing",
    "cryptoslate.com":   "cryptoslate",
    "coindesk.com":      "coindesk",
}


def _source_name(url: str) -> str:
    """Extract a short source identifier from a feed URL."""
    for domain, name in FEED_SOURCE_MAP.items():
        if domain in url:
            return name
    return "crypto_news"


def _parse_date(entry: dict) -> datetime | None:
    """
    RSS entries can store dates in a variety of formats.
    feedparser usually normalises to a time.struct_time in `published_parsed`.
    If that fails, we fall back to the raw `published` string.
    """
    if entry.get("published_parsed"):
        ts = entry["published_parsed"]
        try:
            return datetime(*ts[:6], tzinfo=timezone.utc)
        except (ValueError, TypeError):
            pass

    raw_date = entry.get("published", "") or entry.get("updated", "")
    if raw_date:
        try:
            return parsedate_to_datetime(raw_date).astimezone(timezone.utc)
        except (ValueError, TypeError):
            pass

    return None


def _is_relevant(entry: dict) -> bool:
    """
    Pre-filter articles before scoring. We need at least one keyword hit
    in either the title or summary/description. This keeps our seen-list
    clean and avoids scoring thousands of irrelevant headlines.
    """
    text = " ".join([
        entry.get("title", ""),
        entry.get("summary", "") or "",
    ]).lower()

    all_keywords = HIGH_VALUE_KEYWORDS + WEB3_KEYWORDS
    return any(kw in text for kw in all_keywords)


def _parse_entry(entry: dict, source: str) -> dict:
    """
    Convert a feedparser entry into our normalised project dict.
    We use the article URL as the unique ID since RSS entries don't have
    stable IDs across all feed implementations.
    """
    url     = entry.get("link", "")
    title   = entry.get("title", "Untitled")
    summary = entry.get("summary", "") or ""

    # Strip HTML tags from summary if present
    import re
    summary = re.sub(r"<[^>]+>", " ", summary).strip()[:500]

    return {
        "id":           f"news_{hash(url) & 0xFFFFFFFF}",
        "title":        title,
        "description":  summary,
        "url":          url,
        "source":       source,
        "published_at": _parse_date(entry),
        "stars":        0,
        "forks":        0,
        "tags":         [tag.get("term", "") for tag in entry.get("tags", [])],
    }


def scrape() -> list[dict]:
    """
    Process all configured RSS feeds and return new, relevant, scored articles.
    
    We parse feeds sequentially (no threading needed at this scale) and
    respect the dedup check so frequent runs don't re-notify old articles.
    Each feed typically has 20–50 entries; we check all of them.
    """
    results = []

    for feed_url in NEWS_RSS_FEEDS:
        source = _source_name(feed_url)
        print(f"[News] 📡 Parsing {source}...")

        feed = feedparser.parse(feed_url)
        entries = feed.get("entries", [])
        print(f"[News] {source} — {len(entries)} entries")

        for entry in entries:
            if not _is_relevant(entry):
                continue

            project = _parse_entry(entry, source)

            if not is_new(project["id"]):
                continue

            score = score_project(
                title=project["title"],
                description=project["description"],
                source=source,
                published_at=project["published_at"],
            )
            project["score"] = score
            results.append(project)
            print(f"[News] ✅ {source}: {project['title'][:60]}... — {score['total']}")

    print(f"[News] Done — {len(results)} new articles found")
    return results
