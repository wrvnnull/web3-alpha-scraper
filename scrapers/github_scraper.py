"""
scrapers/github_scraper.py — GitHub New Repos Scraper
-------------------------------------------------------
Searches GitHub for brand-new repositories matching our Web3/AI Agent
keyword queries. GitHub is one of the BEST early signals because devs
push code before the marketing team writes a single tweet.

Strategy: search for repos created in the last 7 days with our keywords,
sorted by "best match" and then by stars. We look for:
  - Low star count but recent push (very early stage)
  - README mentions of testnet, airdrop, incentivized

API Docs: https://docs.github.com/en/rest/search/search
Rate limits: 30 requests/min authenticated, 10/min unauthenticated
"""

import time
import requests
from datetime import datetime, timedelta, timezone
from config import GITHUB_TOKEN, GITHUB_SEARCH_QUERIES
from utils.scorer import score_project
from utils.dedup import is_new


HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"

BASE_URL = "https://api.github.com/search/repositories"


def _build_date_filter() -> str:
    """Return a date string for repos created in the last 7 days."""
    cutoff = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    return f"created:>{cutoff}"


def _fetch_repos(query: str, per_page: int = 10) -> list[dict]:
    """Fetch repos from GitHub Search API for a single query string."""
    date_filter = _build_date_filter()
    full_query = f"{query} {date_filter}"

    try:
        resp = requests.get(
            BASE_URL,
            headers=HEADERS,
            params={
                "q": full_query,
                "sort": "updated",
                "order": "desc",
                "per_page": per_page,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("items", [])
    except requests.RequestException as e:
        print(f"[GitHub] Error fetching '{query}': {e}")
        return []


def _parse_repo(repo: dict) -> dict:
    """
    Translate a raw GitHub API repo object into our normalised
    project dict that the scorer and notifier understand.
    """
    pushed_at = repo.get("pushed_at")
    if pushed_at:
        pushed_at = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))

    return {
        "id":          f"github_{repo['id']}",
        "title":       repo.get("full_name", ""),
        "description": repo.get("description") or "",
        "url":         repo.get("html_url", ""),
        "source":      "github",
        "published_at": pushed_at,
        "stars":       repo.get("stargazers_count", 0),
        "forks":       repo.get("forks_count", 0),
        "tags":        repo.get("topics", []),
        "language":    repo.get("language", ""),
        "extra_url":   repo.get("homepage") or "",  # project website if set
    }


def scrape() -> list[dict]:
    """
    Run all configured GitHub search queries and return a list of new,
    scored projects that exceed the minimum threshold.
    
    We rate-limit ourselves to one request per second across all queries
    to stay well within GitHub's 30 req/min limit.
    """
    results = []

    for query in GITHUB_SEARCH_QUERIES:
        print(f"[GitHub] 🔍 Searching: '{query}'")
        raw_repos = _fetch_repos(query, per_page=15)

        for repo in raw_repos:
            project = _parse_repo(repo)

            # Skip if we've already seen this repo
            if not is_new(project["id"]):
                continue

            # Score the project
            score = score_project(
                title=project["title"],
                description=project["description"] + " " + " ".join(project["tags"]),
                source="github",
                published_at=project["published_at"],
                stars=project["stars"],
                forks=project["forks"],
            )
            project["score"] = score
            results.append(project)
            print(f"[GitHub] ✅ New: {project['title']} — score {score['total']}")

        time.sleep(1.2)  # Stay within rate limits

    print(f"[GitHub] Done — {len(results)} new projects found")
    return results
