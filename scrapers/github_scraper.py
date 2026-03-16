"""
scrapers/github_scraper.py — GitHub New Repos Scraper
-------------------------------------------------------
Filter bawaan:
  - Max 3 repos per username per run → mencegah satu akun spam flooding notif
  - Skip akun yang namanya terlihat auto-generated (angka random panjang)
  - fork:false → hanya original repos
  - Dedup antar query dalam satu run
"""

import re
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

BASE_URL      = "https://api.github.com/search/repositories"
LOOKBACK_DAYS = 30

# Max repos yang dinotifikasi per akun GitHub per run
# Ini mencegah satu "bot factory" account flooding 10+ notif sekaligus
MAX_REPOS_PER_USER = 3


def _looks_like_spam_account(username: str) -> bool:
    """
    Heuristic sederhana untuk mendeteksi akun yang kemungkinan
    adalah spam/copy-paste bot factory:
      - Username dengan 6+ digit angka di tengah/akhir (auto-generated pattern)
        Contoh: marilyn4120shaz3, fernandez81188studio, gesine1541ro7
      - Username dengan pola nama+angka+namaacak
    
    Akun legitimate biasanya: organisasi (crestalnetwork, goat-sdk),
    nama developer (nirholas, tryethernal), atau handle sederhana.
    """
    # Pola: ada 4+ digit berurutan di username → kemungkinan auto-generated
    if re.search(r'\d{4,}', username):
        return True
    return False


def _build_date_filter() -> str:
    cutoff = (datetime.utcnow() - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    return f"pushed:>{cutoff}"


def _fetch_repos(query: str, per_page: int = 20) -> list[dict]:
    date_filter = _build_date_filter()
    full_query  = f"{query} {date_filter} fork:false"

    try:
        resp = requests.get(
            BASE_URL,
            headers=HEADERS,
            params={"q": full_query, "sort": "stars", "order": "desc", "per_page": per_page},
            timeout=20,
        )
        if resp.status_code == 422:
            resp = requests.get(
                BASE_URL,
                headers=HEADERS,
                params={"q": query + " fork:false", "sort": "stars", "order": "desc", "per_page": per_page},
                timeout=20,
            )
        resp.raise_for_status()
        data  = resp.json()
        items = data.get("items", [])
        print(f"[GitHub] ↳ {len(items)}/{data.get('total_count',0)} repos: {query!r}")
        return items
    except requests.RequestException as e:
        print(f"[GitHub] Error {query!r}: {e}")
        return []


def _parse_repo(repo: dict) -> dict:
    pushed_at = repo.get("pushed_at")
    if pushed_at:
        pushed_at = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
    return {
        "id":           f"github_{repo['id']}",
        "title":        repo.get("full_name", ""),
        "description":  repo.get("description") or "",
        "url":          repo.get("html_url", ""),
        "source":       "github",
        "published_at": pushed_at,
        "stars":        repo.get("stargazers_count", 0),
        "forks":        repo.get("forks_count", 0),
        "tags":         repo.get("topics", []),
        "language":     repo.get("language", ""),
        "extra_url":    repo.get("homepage") or "",
    }


def scrape() -> list[dict]:
    processed_in_run  = set()   # dedup antar query
    repos_per_user    = {}      # counter per username
    results           = []

    for query in GITHUB_SEARCH_QUERIES:
        print(f"[GitHub] 🔍 {query!r}")
        raw_repos = _fetch_repos(query)

        for repo in raw_repos:
            repo_id  = f"github_{repo['id']}"
            username = repo.get("owner", {}).get("login", "")

            # ── Filter 1: dedup antar query ───────────────────────────
            if repo_id in processed_in_run:
                continue
            processed_in_run.add(repo_id)

            # ── Filter 2: skip akun spam ──────────────────────────────
            if _looks_like_spam_account(username):
                print(f"[GitHub] ⏭  Skip spam account: {username}")
                continue

            # ── Filter 3: max 3 repos per user per run ────────────────
            count = repos_per_user.get(username, 0)
            if count >= MAX_REPOS_PER_USER:
                print(f"[GitHub] ⏭  {username} sudah {count} repos, skip")
                continue
            repos_per_user[username] = count + 1

            # ── Filter 4: belum pernah dilihat (across runs) ──────────
            if not is_new(repo_id):
                continue

            project = _parse_repo(repo)
            full_text = " ".join([project["title"], project["description"], " ".join(project["tags"])])

            score = score_project(
                title=project["title"],
                description=full_text,
                source="github",
                published_at=project["published_at"],
                stars=project["stars"],
                forks=project["forks"],
            )
            project["score"] = score
            results.append(project)
            print(f"[GitHub] ✅ {project['title']} (⭐{project['stars']}) — score {score['total']}")

        time.sleep(2)

    print(f"[GitHub] Done — {len(results)} new projects found")
    return results
