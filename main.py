"""
main.py — Web3 Alpha Scraper Orchestrator
------------------------------------------
This is the entry point that wires everything together. Think of it
as the conductor of an orchestra: it calls each scraper in order,
collects all the results, sorts them by score (highest first), and
fires off Telegram notifications for projects above our threshold.

Run order matters here:
  1. Airdrop sites first — most direct farming opportunities
  2. DeFiLlama second — high-quality protocol data
  3. CoinGecko third — trending signals
  4. News feeds fourth — text-rich for keyword scoring
  5. GitHub last — slower but gives us raw early-stage repos
  6. Twitter — can be slow if Nitter instances are down

Usage:
  python main.py                    # Run all scrapers
  python main.py --source github    # Run only GitHub scraper
  python main.py --dry-run          # Scrape but don't send Telegram

Environment variables (set as GitHub Secrets in your repo):
  TELEGRAM_BOT_TOKEN   — Your bot's token from @BotFather
  TELEGRAM_CHAT_ID     — Your chat or group ID
  GITHUB_TOKEN         — GitHub PAT for authenticated API calls
  TWITTER_BEARER_TOKEN — (Optional) Twitter API v2 bearer token
"""

import argparse
import sys
import traceback
from datetime import datetime
from config import MIN_SCORE_TO_NOTIFY

from scrapers import (
    airdrop_scraper,
    defillama_scraper,
    coingecko_scraper,
    news_scraper,
    github_scraper,
    twitter_scraper,
    web3_jobs_scraper,
)
from utils.telegram_notifier import notify_project, send_summary, send_startup_message

# ── Map CLI name → scraper module ──────────────────────────────────────
ALL_SCRAPERS = {
    "airdrop":   airdrop_scraper,
    "defillama": defillama_scraper,
    "coingecko": coingecko_scraper,
    "news":      news_scraper,
    "github":    github_scraper,
    "twitter":   twitter_scraper,
    "jobs":      web3_jobs_scraper,
}


def run(sources: list[str], dry_run: bool = False) -> dict:
    """
    Main execution loop. Runs selected scrapers, aggregates results,
    sorts by score, and sends Telegram alerts for qualifying projects.
    
    Returns a stats dictionary for the summary notification at the end.
    """
    stats = {
        "total": 0,
        "notified": 0,
        "skipped": 0,
        "below_threshold": 0,
        "errors": 0,
        "by_source": {},
    }

    all_results: list[dict] = []

    # ── 1. Run each scraper ──────────────────────────────────────────
    for name in sources:
        scraper = ALL_SCRAPERS[name]
        print(f"\n{'='*50}")
        print(f"  Running scraper: {name.upper()}")
        print(f"{'='*50}")
        try:
            results = scraper.scrape()
            all_results.extend(results)
            stats["by_source"][name] = len(results)
            stats["total"] += len(results)
        except Exception as e:
            print(f"[MAIN] ❌ Error in {name} scraper: {e}")
            traceback.print_exc()
            stats["errors"] += 1
            stats["by_source"][name] = 0

    # ── 2. Sort by score descending — best opportunities first ───────
    all_results.sort(key=lambda p: p.get("score", {}).get("total", 0), reverse=True)

    print(f"\n{'='*50}")
    print(f"  TOTAL NEW ITEMS FOUND: {len(all_results)}")
    print(f"  SCORE THRESHOLD: {MIN_SCORE_TO_NOTIFY}/100")
    print(f"{'='*50}")

    if not dry_run:
        send_startup_message()

    # ── 3. Notify for each qualifying project ─────────────────────────
    for project in all_results:
        score = project.get("score", {})
        total = score.get("total", 0)

        print(f"\n  [{total:3d}/100] {project.get('title', '?')[:60]}")
        print(f"           Source: {project.get('source', '?')}")
        print(f"           URL: {project.get('url', '?')[:80]}")

        if total < MIN_SCORE_TO_NOTIFY:
            print(f"           → BELOW THRESHOLD ({MIN_SCORE_TO_NOTIFY}) — skipping")
            stats["below_threshold"] += 1
            continue

        if dry_run:
            print(f"           → DRY RUN — would notify")
            stats["notified"] += 1
        else:
            success = notify_project(project, score)
            if success:
                print(f"           → ✅ Telegram notification sent")
                stats["notified"] += 1
            else:
                print(f"           → ⚠️  Telegram send failed")
                stats["errors"] += 1

    # ── 4. Send run summary ─────────────────────────────────────────
    print(f"\n{'='*50}")
    print(f"  RUN SUMMARY")
    print(f"  Total:           {stats['total']}")
    print(f"  Notified:        {stats['notified']}")
    print(f"  Below threshold: {stats['below_threshold']}")
    print(f"  Errors:          {stats['errors']}")
    print(f"{'='*50}\n")

    if not dry_run:
        send_summary(stats)

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Web3 Alpha Scraper — Find early farming opportunities"
    )
    parser.add_argument(
        "--source",
        choices=list(ALL_SCRAPERS.keys()),
        help="Run only a specific scraper (default: run all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape and score but do NOT send Telegram notifications",
    )
    args = parser.parse_args()

    sources = [args.source] if args.source else list(ALL_SCRAPERS.keys())
    print(f"\n🚀 Web3 Alpha Scraper starting at {datetime.utcnow().isoformat()} UTC")
    print(f"   Sources: {', '.join(sources)}")
    print(f"   Dry run: {args.dry_run}\n")

    stats = run(sources, dry_run=args.dry_run)
    sys.exit(0 if stats["errors"] == 0 else 1)


if __name__ == "__main__":
    main()
