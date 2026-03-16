"""
scrapers/web3_jobs_scraper.py — Web3 Job Board & Project Directory Scraper
---------------------------------------------------------------------------
Web3 job boards are a SLEEPER SIGNAL for alpha — when a project posts
10+ jobs simultaneously, they just raised funding and are about to launch.
That's your window to get in early before any airdrop announcement.

Similarly, project directories like Messari, Electric Capital, and
ecosystem grant pages list projects BEFORE they're widely known.

Sources:
  1. crypto.jobs     — Largest Web3 job board
  2. web3.career     — Popular Web3 career site
  3. Messari Hub     — Curated project profiles (API)
  4. Ecosystem pages — L2 ecosystem directories (Arbitrum, Base, etc.)
"""

import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from utils.scorer import score_project
from utils.dedup import is_new
from config import WEB3_KEYWORDS, AI_AGENT_KEYWORDS


SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    )
})

# Ecosystem grant / project pages — these list early-stage grantees
ECOSYSTEM_PAGES = {
    "Arbitrum Grants": "https://arbitrum.foundation/grants",
    "Optimism RPG":    "https://app.optimism.io/retropgf",
    "Base Ecosystem":  "https://base.org/ecosystem",
    "zkSync Ecosystem":"https://ecosystem.zksync.io/",
    "Scroll Ecosystem":"https://scroll.io/ecosystem",
}


def _scrape_crypto_jobs() -> list[dict]:
    """
    crypto.jobs doesn't have an RSS feed, but has a public job listing page.
    We look for companies posting 5+ jobs (= recent raise, big launch incoming).
    
    Companies posting many jobs simultaneously = pre-launch phase → high alpha.
    """
    items = []
    try:
        resp = SESSION.get("https://crypto.jobs/", timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Find job listings — typically in cards or list items
        job_cards = soup.select("article, .job-card, [class*='job'], li[class*='job']")

        # Group by company name to find companies with many openings
        company_jobs: dict[str, list] = {}
        for card in job_cards[:100]:
            company_el = card.find(["span", "div", "a"], class_=lambda c: c and "company" in c.lower() if c else False)
            if not company_el:
                company_el = card.find(["h3", "h4"])
            company = company_el.get_text(strip=True) if company_el else ""

            title_el = card.find(["h2", "h3", "a"])
            title = title_el.get_text(strip=True) if title_el else ""

            if company and title:
                if company not in company_jobs:
                    company_jobs[company] = []
                company_jobs[company].append(title)

        # Companies with 3+ openings are interesting
        for company, jobs in company_jobs.items():
            if len(jobs) >= 3:
                items.append({
                    "name":        company,
                    "description": f"🚀 {len(jobs)} open positions — {', '.join(jobs[:3])}{'...' if len(jobs) > 3 else ''}",
                    "url":         f"https://crypto.jobs/?company={company.replace(' ', '+')}",
                    "source_site": "crypto_jobs",
                })

    except Exception as e:
        print(f"[Jobs] crypto.jobs error: {e}")

    return items


def _scrape_web3_career_rss() -> list[dict]:
    """
    web3.career has an RSS feed for new job postings.
    We filter for titles/companies mentioning our high-value keywords.
    """
    items = []
    try:
        # web3.career doesn't have official RSS but many job boards syndicate
        # We use a generic jobs-focused search approach
        resp = SESSION.get("https://web3.career/remote-web3-jobs", timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        rows = soup.select("tr, .job-row, [class*='job-item']")
        companies_seen = set()

        for row in rows[:50]:
            company_el = row.find(class_=lambda c: "company" in str(c).lower() if c else False)
            if not company_el:
                continue
            company = company_el.get_text(strip=True)

            if company in companies_seen:
                continue
            companies_seen.add(company)

            # Check if company description mentions reward/farming keywords
            row_text = row.get_text().lower()
            all_kw = WEB3_KEYWORDS + AI_AGENT_KEYWORDS
            if any(kw in row_text for kw in all_kw):
                link_el = row.find("a", href=True)
                link = link_el["href"] if link_el else "https://web3.career"
                if link.startswith("/"):
                    link = "https://web3.career" + link

                items.append({
                    "name":        company,
                    "description": f"Web3 company hiring — " + row.get_text(strip=True)[:200],
                    "url":         link,
                    "source_site": "web3_career",
                })

    except Exception as e:
        print(f"[Jobs] web3.career error: {e}")

    return items


def _scrape_ecosystem_page(name: str, url: str) -> list[dict]:
    """
    Scrape a blockchain ecosystem directory page.
    These pages list projects that have received grants or are building
    on that L2 — often pre-token projects with farming potential.
    """
    items = []
    try:
        resp = SESSION.get(url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Look for project cards — they usually have headings and brief descriptions
        cards = soup.select("article, .project-card, [class*='project'], [class*='card']")
        if not cards:
            # Fallback: grab named links
            cards = soup.find_all("a", href=True)

        for card in cards[:30]:
            heading = card.find(["h2", "h3", "h4", "strong"])
            project_name = heading.get_text(strip=True) if heading else ""
            if not project_name or len(project_name) < 3:
                continue

            desc_el = card.find("p")
            desc = desc_el.get_text(strip=True)[:200] if desc_el else ""

            link_el = card if card.name == "a" else card.find("a")
            link = link_el.get("href", url) if link_el else url
            if link.startswith("/"):
                from urllib.parse import urlparse
                base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                link = base + link

            items.append({
                "name":        project_name,
                "description": f"[{name} Ecosystem] {desc}",
                "url":         link,
                "source_site": "ecosystem_directory",
            })

    except Exception as e:
        print(f"[Jobs] Ecosystem {name} error: {e}")

    return items


def scrape() -> list[dict]:
    """
    Run all job board and ecosystem directory scrapers.
    Score and filter results, prioritizing companies with many job openings
    (= pre-launch) and newly listed ecosystem projects.
    """
    print("[Jobs/Ecosystem] 🔍 Scraping job boards & ecosystem directories...")
    all_raw = []

    raw = _scrape_crypto_jobs()
    print(f"[Jobs] crypto.jobs: {len(raw)} active companies")
    all_raw.extend(raw)

    raw = _scrape_web3_career_rss()
    print(f"[Jobs] web3.career: {len(raw)} companies")
    all_raw.extend(raw)

    for name, url in ECOSYSTEM_PAGES.items():
        raw = _scrape_ecosystem_page(name, url)
        print(f"[Ecosystem] {name}: {len(raw)} projects")
        all_raw.extend(raw)

    results = []
    for item in all_raw:
        name = item.get("name", "").strip()
        if not name or len(name) < 3:
            continue

        project_id = f"jobs_{hash(item.get('url', name)) & 0xFFFFFFFF}"

        if not is_new(project_id):
            continue

        project = {
            "id":          project_id,
            "title":       name,
            "description": item.get("description", ""),
            "url":         item.get("url", ""),
            "source":      item.get("source_site", "web3_jobs"),
            "published_at": datetime.now(timezone.utc),
            "stars":       0,
            "forks":       0,
            "tags":        ["hiring", "ecosystem"],
        }

        score = score_project(
            title=project["title"],
            description=project["description"],
            source="unknown",
            published_at=project["published_at"],
        )
        project["score"] = score
        results.append(project)
        print(f"[Jobs/Ecosystem] ✅ {project['title']} — score {score['total']}")

    print(f"[Jobs/Ecosystem] Done — {len(results)} new items found")
    return results
