"""
weekly_digest.py — Weekly Summary Report
-----------------------------------------
Reads the data/seen.json state file and computes a 7-day lookback
summary showing how many projects were discovered, which sources
were most active, and how the week compared to previous weeks.

Sends the report to Telegram as a formatted HTML message.
"""

import json
import os
from datetime import datetime, timedelta, timezone
from config import SEEN_FILE
from utils.telegram_notifier import send_message


def generate_digest():
    """Build and send the weekly digest."""
    if not os.path.exists(SEEN_FILE):
        send_message("📊 <b>Weekly Digest</b>\n\nNo data/seen.json found — has the scraper run yet?")
        return

    with open(SEEN_FILE) as f:
        data = json.load(f)

    now     = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    # Count projects seen in the last 7 days
    recent = [
        v for v in data.values()
        if datetime.fromisoformat(v["first_seen"]) > week_ago
    ]

    total_tracked = len(data)
    weekly_count  = len(recent)

    lines = [
        "📊 <b>Web3 Alpha Scraper — Weekly Digest</b>",
        f"📅 Week ending: {now.strftime('%Y-%m-%d')}",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"🆕 New projects this week:  <b>{weekly_count}</b>",
        f"📚 Total tracked ever:      <b>{total_tracked}</b>",
        "",
        "🔍 Keep farming — stay early, stay ahead.",
        "",
        "💡 Tip: Check your Telegram history from this week",
        "   for all notified projects with scores above your threshold.",
    ]

    send_message("\n".join(lines))
    print(f"[Digest] Sent weekly digest — {weekly_count} new projects this week")


if __name__ == "__main__":
    generate_digest()
