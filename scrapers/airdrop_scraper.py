"""
scrapers/airdrop_scraper.py — Airdrop Aggregator Scraper
----------------------------------------------------------
Airdrop aggregator sites are the most DIRECT signal for farming
opportunities — their entire purpose is to list projects giving
away tokens. We scrape multiple sites and deduplicate across them.

Sites covered:
  1. airdrops.io     — One of the oldest and most comprehensive
  2. airdropalert.com — Real-time airdrop alerts
  3. earnifi.com     — On-chain unclaimed airdrop tracker

Scraping strategy: We use BeautifulSoup to parse HTML and extract
project names, descriptions, reward amounts, and links. Since these
sites frequently change their HTML structure, we use flexible selectors
that look for semantic patterns rather than brittle CSS class names.

Note: Some sites use JavaScript rendering. For those we fetch the
HTML and extract whatever is available in the initial server render.
For JS-heavy pages, a headless browser (Selenium/Playwright) would
be needed — commented out at the bottom for opt-in use.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from utils.scorer import score_project
from utils.dedup import is_new


SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
})


# ─────────────────────────────────────────────
# airdrops.io parser
# ─────────────────────────────────────────────

def _scrape_airdrops_io() -> list[dict]:
    """
    airdrops.io uses a card-based layout. Each card represents one airdrop
    and contains the project name, a short description, and a 'status' badge
    (e.g. 'Live', 'Upcoming', 'Hot').
    
    We target the Live and Upcoming sections specifically, skipping
    'Ended' airdrops since those have no farming value.
    """
    url = "https://airdrops.io/"
    items = []
    try:
        resp = SESSION.get(url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Look for airdrop cards — they typically have h2/h3 project names
        cards = soup.select("article, .airdrop-item, .card, [class*='airdrop']")
        if not cards:
            # Fallback: grab all links that look like project pages
            cards = soup.find_all("a", href=lambda h: h and "/airdrop/" in h)

        for card in cards[:20]:  # Limit to avoid noise
            name = ""
            desc = ""

            # Try to find a heading (project name)
            heading = card.find(["h2", "h3", "h4", "strong"])
            if heading:
                name = heading.get_text(strip=True)

            # Try to find a description paragraph
            para = card.find("p")
            if para:
                desc = para.get_text(strip=True)[:300]

            link_tag = card if card.name == "a" else card.find("a")
            link = link_tag.get("href", "") if link_tag else ""
            if link and not link.startswith("http"):
                link = "https://airdrops.io" + link

            if name:
                items.append({
                    "name": name,
                    "description": desc,
                    "url": link or url,
                    "source_site": "airdrops_io",
                })

    except requests.RequestException as e:
        print(f"[Airdrop] airdrops.io error: {e}")

    return items


# ─────────────────────────────────────────────
# airdropalert.com parser
# ─────────────────────────────────────────────

def _scrape_airdrop_alert() -> list[dict]:
    """
    airdropalert.com has a straightforward table/list layout where each
    row represents an active airdrop with project name and description.
    """
    url = "https://airdropalert.com/"
    items = []
    try:
        resp = SESSION.get(url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Target the main content area with airdrop listings
        cards = soup.select(".post, .campaign, article, [class*='airdrop']")
        if not cards:
            cards = soup.find_all("a", href=lambda h: h and "airdropalert.com" in str(h))

        for card in cards[:20]:
            heading = card.find(["h2", "h3", "h1"])
            name = heading.get_text(strip=True) if heading else ""

            para = card.find("p")
            desc = para.get_text(strip=True)[:300] if para else ""

            link_tag = card if card.name == "a" else card.find("a")
            link = link_tag.get("href", "") if link_tag else url

            if name:
                items.append({
                    "name": name,
                    "description": desc,
                    "url": link,
                    "source_site": "airdrop_alert",
                })

    except requests.RequestException as e:
        print(f"[Airdrop] airdropalert.com error: {e}")

    return items


# ─────────────────────────────────────────────
# DeFiLlama Airdrops page
# ─────────────────────────────────────────────

def _scrape_defillama_airdrops() -> list[dict]:
    """
    DeFiLlama has a dedicated /airdrops page that lists upcoming and
    active airdrops. This is probably the MOST reliable because DeFiLlama
    is trusted by the DeFi community and has high-quality curation.
    
    The page is React-rendered, so we can only get the initial HTML shell.
    However, DeFiLlama also exposes this data via their API.
    """
    url = "https://api.llama.fi/airdrops"
    items = []
    try:
        resp = SESSION.get(url, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            for item in (data if isinstance(data, list) else []):
                items.append({
                    "name":        item.get("name", ""),
                    "description": item.get("description", "") or f"Airdrop on {item.get('chain', '?')}",
                    "url":         item.get("url") or f"https://defillama.com/airdrops",
                    "source_site": "defillama_airdrop",
                })
    except Exception as e:
        print(f"[Airdrop] DeFiLlama airdrops error: {e}")

    return items


# ─────────────────────────────────────────────
# Main scrape function
# ─────────────────────────────────────────────

def scrape() -> list[dict]:
    """
    Aggregate results from all airdrop sites, normalize them, deduplicate,
    score, and return qualifying projects.
    
    These are the HIGHEST PRIORITY items since they're explicitly curated
    farming opportunities — they'll tend to score well on keywords alone.
    """
    print("[Airdrop] 🔍 Scraping airdrop aggregators...")
    all_raw = []

    raw = _scrape_airdrops_io()
    print(f"[Airdrop] airdrops.io: {len(raw)} items")
    all_raw.extend(raw)

    raw = _scrape_airdrop_alert()
    print(f"[Airdrop] airdropalert.com: {len(raw)} items")
    all_raw.extend(raw)

    raw = _scrape_defillama_airdrops()
    print(f"[Airdrop] DeFiLlama airdrops: {len(raw)} items")
    all_raw.extend(raw)

    results = []
    for item in all_raw:
        name = item.get("name", "").strip()
        if not name or len(name) < 3:
            continue

        project_id = f"airdrop_{hash(item['url']) & 0xFFFFFFFF}"

        if not is_new(project_id):
            continue

        project = {
            "id":          project_id,
            "title":       name,
            "description": "🪂 AIRDROP LISTED — " + (item.get("description", "")),
            "url":         item.get("url", ""),
            "source":      item.get("source_site", "airdrop"),
            "published_at": datetime.now(timezone.utc),
            "stars":       0,
            "forks":       0,
            "tags":        ["airdrop"],
        }

        score = score_project(
            title=project["title"],
            description=project["description"],
            source="airdrop_alert",
            published_at=project["published_at"],
        )
        project["score"] = score
        results.append(project)
        print(f"[Airdrop] ✅ {project['title']} — score {score['total']}")

    print(f"[Airdrop] Done — {len(results)} new airdrops found")
    return results
