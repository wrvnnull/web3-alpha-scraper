"""
scrapers/twitter_scraper.py — Twitter Alpha via Google News RSS
----------------------------------------------------------------
Nitter sudah mati total. Kita pakai Google News RSS sebagai proxy.

Fix dari versi sebelumnya:
  - URL di-resolve dari Google News redirect → URL artikel asli
    Sehingga link yang dikirim ke Telegram bisa langsung dibuka
  - Timeout per URL resolve singkat (3s) agar tidak memperlambat run
"""

import time
import requests
import feedparser
from datetime import datetime, timezone, timedelta
from config import TWITTER_BEARER_TOKEN, HIGH_VALUE_KEYWORDS
from utils.scorer import score_project
from utils.dedup import is_new


GOOGLE_NEWS_QUERIES = [
    "crypto airdrop testnet 2025",
    "incentivized testnet web3",
    "defi points program rewards",
    "blockchain ai agent launch",
    "depin node runner rewards",
    "crypto bounty program",
    "web3 early access whitelist",
    "new layer2 testnet launch",
    "restaking protocol airdrop",
    "crypto farming rewards season",
]

GOOGLE_NEWS_BASE = "https://news.google.com/rss/search"


def _resolve_google_url(redirect_url: str) -> str:
    """
    Google News RSS memberikan URL berbentuk:
    https://news.google.com/rss/articles/CBMi...
    
    Ini adalah redirect ke artikel asli. Kita follow redirect-nya
    (tanpa download body) untuk dapat URL final yang bisa diklik.
    Kalau gagal/timeout, kembalikan URL asli sebagai fallback.
    """
    try:
        resp = requests.head(
            redirect_url,
            allow_redirects=True,
            timeout=3,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        final_url = resp.url
        # Kalau masih di domain google, coba GET singkat
        if "google.com" in final_url:
            resp2 = requests.get(redirect_url, timeout=3, headers={"User-Agent": "Mozilla/5.0"})
            return resp2.url
        return final_url
    except Exception:
        return redirect_url   # Fallback ke URL redirect


def _scrape_google_news_rss() -> list[dict]:
    items  = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    seen_urls = set()  # dedup dalam satu run

    for query in GOOGLE_NEWS_QUERIES:
        try:
            resp = requests.get(
                GOOGLE_NEWS_BASE,
                params={"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"},
                headers={"User-Agent": "Mozilla/5.0 (compatible; AlphaScraper/1.0)"},
                timeout=15,
            )
            resp.raise_for_status()
            feed    = feedparser.parse(resp.text)
            entries = feed.get("entries", [])
            print(f"[Twitter/GNews] ↳ {len(entries)} results: {query!r}")

            for entry in entries[:8]:
                raw_url = entry.get("link", "")
                title   = entry.get("title", "")
                summary = entry.get("summary", "") or ""

                # Dedup berdasarkan title (lebih stable dari URL redirect)
                title_key = title.lower().strip()[:80]
                if title_key in seen_urls:
                    continue
                seen_urls.add(title_key)

                # Parse tanggal
                pub_dt = None
                if entry.get("published_parsed"):
                    try:
                        pub_dt = datetime(*entry["published_parsed"][:6], tzinfo=timezone.utc)
                    except Exception:
                        pass

                if pub_dt and pub_dt < cutoff:
                    continue

                # Resolve URL redirect → URL artikel asli
                final_url = _resolve_google_url(raw_url) if raw_url else raw_url

                items.append({
                    "id":           f"gnews_{hash(title_key) & 0xFFFFFFFF}",
                    "title":        title,
                    "description":  summary[:400],
                    "url":          final_url,
                    "source":       "twitter",
                    "published_at": pub_dt or datetime.now(timezone.utc),
                    "stars":        0,
                    "forks":        0,
                    "tags":         ["alpha", "web3"],
                })

        except Exception as e:
            print(f"[Twitter/GNews] Error {query!r}: {e}")

        time.sleep(1)

    return items


def _scrape_twitter_api_v2() -> list[dict]:
    if not TWITTER_BEARER_TOKEN:
        return []

    headers  = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}
    base_url = "https://api.twitter.com/2/tweets/search/recent"
    items    = []

    query = (
        '(testnet OR airdrop OR incentivized OR "points campaign" '
        'OR "bounty program" OR "early access" OR "node rewards") '
        '(web3 OR defi OR blockchain OR "ai agent" OR depin) '
        '-is:retweet lang:en'
    )

    try:
        resp = requests.get(
            base_url,
            headers=headers,
            params={
                "query":        query,
                "max_results":  100,
                "tweet.fields": "created_at,author_id,public_metrics",
                "expansions":   "author_id",
                "user.fields":  "username",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data  = resp.json()
        users = {u["id"]: u["username"] for u in data.get("includes", {}).get("users", [])}

        for tweet in data.get("data", []):
            author  = users.get(tweet.get("author_id", ""), "unknown")
            text    = tweet.get("text", "")
            tid     = tweet.get("id", "")
            created = tweet.get("created_at", "")

            pub_dt = None
            if created:
                try:
                    pub_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                except ValueError:
                    pass

            metrics = tweet.get("public_metrics", {})
            items.append({
                "id":           f"twitter_api_{tid}",
                "title":        f"@{author}: {text[:100]}",
                "description":  text[:500],
                "url":          f"https://x.com/{author}/status/{tid}",
                "source":       "twitter",
                "published_at": pub_dt,
                "stars":        metrics.get("like_count", 0),
                "forks":        metrics.get("retweet_count", 0),
                "tags":         ["twitter", "alpha"],
            })

        print(f"[Twitter API] ✅ {len(items)} tweets fetched")

    except requests.RequestException as e:
        print(f"[Twitter API] Error: {e}")

    return items


def scrape() -> list[dict]:
    print("[Twitter] 🔍 Scraping Twitter alpha signals...")

    if TWITTER_BEARER_TOKEN:
        print("[Twitter] → Mode: Official API v2")
        raw = _scrape_twitter_api_v2()
    else:
        print("[Twitter] → Mode: Google News RSS")
        raw = _scrape_google_news_rss()

    results = []
    for project in raw:
        if not is_new(project["id"]):
            continue
        score = score_project(
            title=project["title"],
            description=project["description"],
            source="twitter",
            published_at=project["published_at"],
            stars=project.get("stars", 0),
        )
        project["score"] = score
        results.append(project)
        print(f"[Twitter] ✅ {project['title'][:70]}... — {score['total']}")

    print(f"[Twitter] Done — {len(results)} new items found")
    return results
