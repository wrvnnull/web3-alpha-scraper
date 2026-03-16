"""
scrapers/defillama_scraper.py — DeFiLlama Protocol & Airdrop Scraper
----------------------------------------------------------------------
DeFiLlama is one of the most reliable DeFi data aggregators. It has a
completely FREE, no-auth-required public API that lists protocols,
their TVL, chain, and description.

We use two endpoints:
  1. /protocols  — full list of all tracked protocols (new ones = alpha)
  2. /airdrops   — dedicated airdrop tracking page (scraped via HTML)

The trick with DeFiLlama is that new protocols appear here BEFORE
most news sites cover them, and protocols with low TVL but rapidly
growing signal early-stage opportunities worth farming.

API Reference: https://defillama.com/docs/api
"""

import requests
from datetime import datetime, timezone
from config import WEB3_KEYWORDS, HIGH_VALUE_KEYWORDS
from utils.scorer import score_project
from utils.dedup import is_new


PROTOCOLS_URL = "https://api.llama.fi/protocols"
AIRDROPS_URL  = "https://defillama.com/airdrops"

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (Web3AlphaScraper/1.0)"})


def _fetch_protocols() -> list[dict]:
    """Fetch all protocols from DeFiLlama's public API."""
    try:
        resp = SESSION.get(PROTOCOLS_URL, timeout=20)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"[DeFiLlama] Error fetching protocols: {e}")
        return []


def _is_relevant(protocol: dict) -> bool:
    """
    Quick pre-filter before full scoring — eliminates obviously irrelevant
    protocols and saves computation. We check if any Web3 or reward keyword
    appears in the name, description, or category.
    """
    text = " ".join([
        protocol.get("name", ""),
        protocol.get("description", "") or "",
        protocol.get("category", "") or "",
    ]).lower()

    # Must match at least one keyword to be worth scoring
    all_kw = HIGH_VALUE_KEYWORDS + WEB3_KEYWORDS
    return any(kw in text for kw in all_kw)


def _parse_protocol(p: dict) -> dict:
    """
    Normalise a DeFiLlama protocol object into our standard project dict.
    
    TVL (Total Value Locked) is a useful proxy for "how much money is in
    this protocol" — very low TVL on a new protocol = very early stage.
    """
    # DeFiLlama doesn't expose creation date in the API, but we can use
    # the timestamp of when it was first listed (if available) or default now
    listed_at = None
    if p.get("listedAt"):
        try:
            listed_at = datetime.fromtimestamp(p["listedAt"], tz=timezone.utc)
        except (ValueError, OSError):
            listed_at = None

    tvl = p.get("tvl") or 0
    tvl_str = f"${tvl:,.0f}" if tvl else "N/A"

    return {
        "id":          f"defillama_{p.get('slug', p.get('name', '').lower().replace(' ', '-'))}",
        "title":       p.get("name", "Unknown"),
        "description": (p.get("description") or "") + f" | Category: {p.get('category', '?')} | TVL: {tvl_str}",
        "url":         f"https://defillama.com/protocol/{p.get('slug', '')}",
        "source":      "defillama",
        "published_at": listed_at,
        "stars":       0,
        "forks":       0,
        "tags":        p.get("chains", []),
        "tvl":         tvl,
        "category":    p.get("category", ""),
    }


def scrape() -> list[dict]:
    """
    Fetch DeFiLlama protocols and return new, scored, relevant ones.
    
    We focus on RECENTLY LISTED protocols (listedAt within last 14 days)
    to avoid re-processing the entire 3000+ protocol list every run.
    """
    print("[DeFiLlama] 🔍 Fetching protocols...")
    raw = _fetch_protocols()
    print(f"[DeFiLlama] Total protocols in API: {len(raw)}")

    now = datetime.now(timezone.utc)
    results = []

    for p in raw:
        # Only look at protocols listed in the last 30 days
        listed_at_ts = p.get("listedAt")
        if listed_at_ts:
            age_days = (now.timestamp() - listed_at_ts) / 86400
            if age_days > 30:
                continue  # Too old — skip

        if not _is_relevant(p):
            continue

        project = _parse_protocol(p)

        if not is_new(project["id"]):
            continue

        score = score_project(
            title=project["title"],
            description=project["description"],
            source="defillama",
            published_at=project["published_at"],
        )
        project["score"] = score
        results.append(project)
        print(f"[DeFiLlama] ✅ New: {project['title']} — score {score['total']}")

    print(f"[DeFiLlama] Done — {len(results)} new protocols found")
    return results
