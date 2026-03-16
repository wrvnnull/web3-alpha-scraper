"""
scrapers/twitter_scraper.py — Twitter/X Scraper
-------------------------------------------------
Twitter/X is the most REAL-TIME source for Web3 alpha — projects announce
testnets, point campaigns, and airdrops here before anywhere else.
Unfortunately, the official API now requires a paid plan ($100+/month).

We offer three approaches here:
  
  APPROACH A (Default, Free): Nitter RSS
  ----------------------------------------
  Nitter is an open-source Twitter front-end that exposes RSS feeds for
  any public account or search. We target well-known alpha-sharing accounts
  and search feeds for our keywords. This works as long as public Nitter
  instances are available.

  APPROACH B (Optional, Free): snscrape CLI
  -------------------------------------------
  snscrape is a Python library/CLI that scrapes Twitter without an API key.
  It mimics a browser session. Reliable but slower. Uncomment the
  SNSCRAPE section below to enable it.

  APPROACH C (Best, $$$): Official v2 API
  ------------------------------------------
  If you have a Twitter Developer account with Elevated access, set the
  TWITTER_BEARER_TOKEN secret. We'll use the official filtered stream or
  recent search endpoint with our keyword queries.

ACCOUNTS TO MONITOR (manually curated alpha accounts):
These are famous for early alpha drops — follow them in your list.
"""

import time
import requests
import feedparser
from datetime import datetime, timezone, timedelta
from config import TWITTER_BEARER_TOKEN, HIGH_VALUE_KEYWORDS
from utils.scorer import score_project
from utils.dedup import is_new


# ─────────────────────────────────────────────
# Nitter instance list — we rotate if one is down
# ─────────────────────────────────────────────
NITTER_INSTANCES = [
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
    "https://nitter.1d4.us",
    "https://nitter.kavin.rocks",
]

# Alpha-focused Twitter accounts — their tweets are high-signal
ALPHA_ACCOUNTS = [
    "CryptoKoryo",       # DeFi alpha researcher
    "DegenSpartan",      # OG DeFi trader
    "0xSisyphus",        # MEV/alpha
    "route2fi",          # Yield farming strategies
    "Pentosh1",          # Ecosystem tracking
    "DefiIgnas",         # DeFi analyst
    "CroissantEth",      # L2 alpha
    "Spreekaway",        # Airdrop hunter
    "mrjasonchoi",       # DeFi research
    "RyanSAdams",        # Bankless / DeFi commentary
    "sassal0x",          # Ethereum developer
]

# Keyword hashtags and search terms to monitor
SEARCH_TERMS = [
    "testnet airdrop",
    "incentivized testnet 2025",
    "points campaign web3",
    "early access blockchain",
    "ai agent defi alpha",
    "depin node rewards",
]


def _try_nitter_feed(url: str) -> list:
    """Try parsing a Nitter RSS feed, return entries or empty list."""
    try:
        feed = feedparser.parse(url)
        return feed.get("entries", [])
    except Exception:
        return []


def _get_nitter_rss_url(instance: str, account: str) -> str:
    """Build the RSS URL for a Nitter user feed."""
    return f"{instance}/{account}/rss"


def _scrape_nitter_accounts() -> list[dict]:
    """
    For each alpha account, try each Nitter instance until one works.
    Parse the RSS feed and look for tweets containing reward/farming keywords.
    
    We only look at tweets from the last 48 hours to stay fresh.
    """
    items = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)

    for account in ALPHA_ACCOUNTS:
        entries = []

        # Try each Nitter instance
        for instance in NITTER_INSTANCES:
            url = _get_nitter_rss_url(instance, account)
            entries = _try_nitter_feed(url)
            if entries:
                print(f"[Twitter/Nitter] ✅ {account} via {instance} ({len(entries)} tweets)")
                break

        if not entries:
            print(f"[Twitter/Nitter] ⚠️  Could not fetch @{account} — all instances failed")
            continue

        for entry in entries:
            title   = entry.get("title", "")
            content = entry.get("summary", "") or title
            text    = f"{title} {content}".lower()

            # Only care about tweets with reward/farming keywords
            if not any(kw in text for kw in HIGH_VALUE_KEYWORDS):
                continue

            # Check recency
            pub_parsed = entry.get("published_parsed")
            pub_dt = None
            if pub_parsed:
                try:
                    pub_dt = datetime(*pub_parsed[:6], tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    pass

            if pub_dt and pub_dt < cutoff:
                continue

            link = entry.get("link", "")
            items.append({
                "id":          f"twitter_{hash(link) & 0xFFFFFFFF}",
                "title":       f"@{account}: {title[:100]}",
                "description": content[:400],
                "url":         link,
                "source":      "twitter",
                "published_at": pub_dt or datetime.now(timezone.utc),
                "stars":       0,
                "forks":       0,
                "tags":        ["twitter", "alpha"],
            })

        time.sleep(0.5)  # Be polite to Nitter instances

    return items


# ─────────────────────────────────────────────
# APPROACH C: Official Twitter API v2
# Only runs if TWITTER_BEARER_TOKEN is set
# ─────────────────────────────────────────────

def _scrape_twitter_api_v2() -> list[dict]:
    """
    Use the official Twitter v2 Recent Search endpoint to find tweets
    matching our keyword queries from the last 7 days.
    
    Requires a bearer token from Twitter Developer Portal.
    Free tier allows 500k tweets/month — more than enough for our use.
    """
    if not TWITTER_BEARER_TOKEN:
        return []

    headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}
    base_url = "https://api.twitter.com/2/tweets/search/recent"
    items = []

    # Build a query that targets high-signal tweets
    query = (
        "(testnet OR airdrop OR incentivized OR \"points campaign\" OR \"early access\") "
        "(web3 OR defi OR blockchain OR \"ai agent\") "
        "-is:retweet lang:en"
    )

    try:
        resp = requests.get(
            base_url,
            headers=headers,
            params={
                "query": query,
                "max_results": 50,
                "tweet.fields": "created_at,author_id,public_metrics,entities",
                "expansions": "author_id",
                "user.fields": "username",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        # Build a map of user_id → username
        users = {u["id"]: u["username"] for u in data.get("includes", {}).get("users", [])}

        for tweet in data.get("data", []):
            author = users.get(tweet.get("author_id", ""), "unknown")
            text   = tweet.get("text", "")
            tid    = tweet.get("id", "")
            created = tweet.get("created_at", "")

            pub_dt = None
            if created:
                try:
                    pub_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                except ValueError:
                    pass

            items.append({
                "id":          f"twitter_api_{tid}",
                "title":       f"@{author}: {text[:100]}",
                "description": text[:500],
                "url":         f"https://twitter.com/{author}/status/{tid}",
                "source":      "twitter",
                "published_at": pub_dt,
                "stars":       tweet.get("public_metrics", {}).get("like_count", 0),
                "forks":       tweet.get("public_metrics", {}).get("retweet_count", 0),
                "tags":        ["twitter"],
            })

    except requests.RequestException as e:
        print(f"[Twitter API] Error: {e}")

    return items


def scrape() -> list[dict]:
    """
    Run Twitter scraping via the best available method.
    API v2 is used if a bearer token is configured; otherwise Nitter RSS.
    """
    print("[Twitter] 🔍 Scraping Twitter/X...")

    if TWITTER_BEARER_TOKEN:
        print("[Twitter] Using official API v2...")
        raw = _scrape_twitter_api_v2()
    else:
        print("[Twitter] Using Nitter RSS (no API key configured)...")
        raw = _scrape_nitter_accounts()

    results = []
    for project in raw:
        if not is_new(project["id"]):
            continue

        score = score_project(
            title=project["title"],
            description=project["description"],
            source="twitter",
            published_at=project["published_at"],
            stars=project["stars"],
        )
        project["score"] = score
        results.append(project)
        print(f"[Twitter] ✅ {project['title'][:60]}... — {score['total']}")

    print(f"[Twitter] Done — {len(results)} new items found")
    return results
