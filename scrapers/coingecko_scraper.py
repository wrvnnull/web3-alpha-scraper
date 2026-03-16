"""
scrapers/coingecko_scraper.py — CoinGecko New Listings Scraper
----------------------------------------------------------------
CoinGecko's free API gives us access to recently listed coins and
trending tokens. New listings on CoinGecko often represent projects
that have JUST launched their token — prime territory for early
farming if they still have ongoing incentive programs.

We use two strategies:
  1. /coins/list + /coins/{id}  — find new coins and get their details
  2. /search/trending            — trending searches = community buzz

Free API is rate-limited to 10-30 calls/min, so we're careful.

API Docs: https://docs.coingecko.com/v3.0.1/reference
"""

import time
import requests
from datetime import datetime, timezone
from utils.scorer import score_project
from utils.dedup import is_new


BASE_URL   = "https://api.coingecko.com/api/v3"
SESSION    = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (Web3AlphaScraper/1.0)"})

# How many new coins to inspect in detail (API rate limit is tight)
MAX_DETAIL_LOOKUPS = 20


def _get_trending() -> list[dict]:
    """
    Fetch trending coins from CoinGecko (top-7 searched in last 24h).
    These are HIGH-SIGNAL: if something is trending, the community
    is actively looking it up — often because of a new campaign or airdrop.
    """
    try:
        resp = SESSION.get(f"{BASE_URL}/search/trending", timeout=15)
        resp.raise_for_status()
        return resp.json().get("coins", [])
    except requests.RequestException as e:
        print(f"[CoinGecko] Error fetching trending: {e}")
        return []


def _get_coin_detail(coin_id: str) -> dict | None:
    """
    Fetch full detail for a specific coin — includes description, links,
    categories, and genesis_date which tells us when the project started.
    We need this to filter genuinely NEW projects.
    """
    try:
        resp = SESSION.get(
            f"{BASE_URL}/coins/{coin_id}",
            params={
                "localization": "false",
                "tickers": "false",
                "market_data": "false",
                "community_data": "false",
                "developer_data": "false",
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"[CoinGecko] Error fetching detail for {coin_id}: {e}")
        return None


def _parse_trending_coin(item: dict) -> dict:
    """
    CoinGecko's trending endpoint returns a nested structure.
    Flatten it into our normalised project dict.
    """
    coin = item.get("item", {})
    return {
        "id":          f"coingecko_trending_{coin.get('id', '')}",
        "title":       f"{coin.get('name', 'Unknown')} ({coin.get('symbol', '?').upper()})",
        "description": f"Trending on CoinGecko — Rank #{coin.get('market_cap_rank', '?')} | Score: {coin.get('score', 0)}",
        "url":         f"https://www.coingecko.com/en/coins/{coin.get('id', '')}",
        "source":      "coingecko",
        "published_at": datetime.now(timezone.utc),  # Trending = now
        "stars":       0,
        "forks":       0,
        "tags":        [],
        "coin_id":     coin.get("id", ""),
    }


def _parse_coin_detail(detail: dict) -> dict:
    """
    Build a richer project entry from CoinGecko's full coin detail endpoint.
    We pull the project's website, whitepaper, and description to give
    the scorer better material to work with.
    """
    genesis_raw = detail.get("genesis_date")
    genesis = None
    if genesis_raw:
        try:
            genesis = datetime.fromisoformat(genesis_raw).replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    links  = detail.get("links", {})
    website = (links.get("homepage") or [""])[0]
    github  = (links.get("repos_url", {}).get("github") or [""])[0]

    desc = detail.get("description", {}).get("en", "") or ""
    cats = detail.get("categories", [])

    return {
        "id":          f"coingecko_{detail.get('id', '')}",
        "title":       f"{detail.get('name', 'Unknown')} ({detail.get('symbol', '?').upper()})",
        "description": desc[:400] + f" | Categories: {', '.join(cats[:5])}",
        "url":         f"https://www.coingecko.com/en/coins/{detail.get('id', '')}",
        "extra_url":   website,
        "source":      "coingecko",
        "published_at": genesis,
        "stars":       0,
        "forks":       0,
        "tags":        cats,
        "github_url":  github,
    }


def scrape() -> list[dict]:
    """
    1. Grab trending coins (always 7 items — fast)
    2. For each trending coin, fetch full details to enrich scoring
    3. Also process non-trending new coins if we have API budget left
    
    We pause between calls to stay under CoinGecko's free tier limit.
    """
    print("[CoinGecko] 🔍 Fetching trending coins...")
    trending = _get_trending()
    results  = []

    for item in trending:
        base = _parse_trending_coin(item)
        coin_id = item.get("item", {}).get("id", "")

        # Enrich with full details
        time.sleep(2)  # CoinGecko free tier needs breathing room
        detail = _get_coin_detail(coin_id) if coin_id else None

        if detail:
            project = _parse_coin_detail(detail)
            # Merge trending signal into detail-based project
            project["description"] = "📈 TRENDING NOW — " + project["description"]
        else:
            project = base

        if not is_new(project["id"]):
            continue

        score = score_project(
            title=project["title"],
            description=project["description"],
            source="coingecko",
            published_at=project["published_at"],
        )
        project["score"] = score
        results.append(project)
        print(f"[CoinGecko] ✅ {project['title']} — score {score['total']}")

    print(f"[CoinGecko] Done — {len(results)} new items found")
    return results
