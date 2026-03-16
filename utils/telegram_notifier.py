"""
utils/telegram_notifier.py — Telegram Notification Engine
-----------------------------------------------------------
Sends formatted alert messages to your Telegram chat via a bot.
Each message includes project details, score breakdown, and a direct link
so you can immediately investigate farming opportunities.

HOW TO SET UP:
1. Talk to @BotFather on Telegram → /newbot → copy the token
2. Add bot to a group or use DM → get your chat_id via @userinfobot
3. Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID as GitHub Secrets
"""

import time
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from utils.scorer import score_label


TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

# Telegram has a 4096-char limit per message — we chunk if needed
MAX_MSG_LEN = 4000


def _escape(text: str) -> str:
    """Escape special chars for Telegram MarkdownV2 format."""
    special = r"_*[]()~`>#+-=|{}.!"
    for ch in special:
        text = text.replace(ch, f"\\{ch}")
    return text


def send_message(text: str, parse_mode: str = "HTML") -> bool:
    """
    Fire a raw message to Telegram. Returns True on success.
    We default to HTML parse mode because it's more forgiving than
    MarkdownV2 and doesn't break on special characters.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram] ⚠️  Token or Chat ID not configured — skipping send")
        return False

    url = TELEGRAM_API.format(token=TELEGRAM_BOT_TOKEN)

    # Chunk long messages
    chunks = [text[i:i+MAX_MSG_LEN] for i in range(0, len(text), MAX_MSG_LEN)]
    for chunk in chunks:
        try:
            resp = requests.post(url, json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": chunk,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            }, timeout=15)
            if not resp.ok:
                print(f"[Telegram] Error: {resp.status_code} — {resp.text}")
                return False
        except requests.RequestException as e:
            print(f"[Telegram] Request failed: {e}")
            return False
        time.sleep(0.5)  # Avoid Telegram rate limit (30 msgs/sec)

    return True


def notify_project(project: dict, score: dict):
    """
    Build a nicely formatted Telegram alert for a single project.
    
    The message is structured like a quick briefing card:
    - What is it (title + source)
    - How hot is it (score + tier)
    - Why is it interesting (matched keywords)
    - Where to go (link)
    """
    tier = score_label(score["total"])
    kw_str = ", ".join(score["matched_kw"]) if score["matched_kw"] else "—"

    lines = [
        f"<b>{tier}</b>  |  Score: <b>{score['total']}/100</b>",
        f"━━━━━━━━━━━━━━━━━━━━━━",
        f"📌 <b>{project.get('title', 'Unknown')}</b>",
        f"🔗 Source: <code>{project.get('source', '?')}</code>",
        f"",
        f"📝 {project.get('description', 'No description')[:300]}",
        f"",
        f"🏷 Keywords: <i>{kw_str}</i>",
        f"",
        f"📊 Breakdown:",
        f"   • Keywords:    {score['breakdown']['keywords']}/40",
        f"   • Recency:     {score['breakdown']['recency']}/20",
        f"   • Credibility: {score['breakdown']['credibility']}/20",
        f"   • Engagement:  {score['breakdown']['engagement']}/20",
        f"",
        f"🔗 <a href=\"{project.get('url', '#')}\">→ Open Project</a>",
    ]

    if project.get("extra_url"):
        lines.append(f"🔗 <a href=\"{project['extra_url']}\">→ Extra Link</a>")

    if project.get("tags"):
        lines.append(f"🏷️ Tags: {', '.join(project['tags'][:5])}")

    message = "\n".join(lines)
    return send_message(message)


def send_summary(stats: dict):
    """
    Send a daily/run summary to Telegram with stats on what was found.
    This helps you understand the signal-to-noise ratio of each run.
    """
    lines = [
        "📊 <b>Web3 Alpha Scraper — Run Complete</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"✅ Total discovered:  {stats.get('total', 0)}",
        f"🔥 Notified (new):    {stats.get('notified', 0)}",
        f"♻️  Skipped (seen):    {stats.get('skipped', 0)}",
        f"🚫 Below threshold:   {stats.get('below_threshold', 0)}",
        f"⚠️  Errors:            {stats.get('errors', 0)}",
        f"",
        f"📡 Sources checked:",
    ]
    for src, cnt in stats.get("by_source", {}).items():
        lines.append(f"   • {src}: {cnt} items")

    send_message("\n".join(lines))


def send_startup_message():
    """Send a heartbeat message when the scraper starts — useful for debugging."""
    from datetime import datetime
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    send_message(f"🤖 <b>Web3 Alpha Scraper started</b>\n⏱ {now}")
