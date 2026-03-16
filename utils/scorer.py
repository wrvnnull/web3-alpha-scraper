"""
utils/scorer.py — Project Potential Scorer
--------------------------------------------
NEWS GATE (aturan paling penting):
  Artikel dari news RSS tidak boleh lolos threshold hanya karena
  kredibilitas sumber + recency. Harus ada setidaknya 1 HIGH_VALUE_KEYWORD.
  Tanpa itu, skor di-cap di 25 (di bawah default threshold 30).

  Ini penting karena kata-kata seperti "blockchain", "defi", "ethereum"
  muncul di SETIAP artikel crypto — tapi yang kita cari adalah signal
  eksplisit farming/reward seperti "airdrop", "testnet", "bounty".
"""

from datetime import datetime, timezone
from config import HIGH_VALUE_KEYWORDS, WEB3_KEYWORDS, AI_AGENT_KEYWORDS

SOURCE_CREDIBILITY = {
    "defillama":         20,
    "coingecko":         18,
    "github":            15,
    "theblock":          16,
    "blockworks":        15,
    "decrypt":           14,
    "cointelegraph":     12,
    "airdrops_io":       10,
    "airdrop_alert":      8,
    "defillama_airdrop": 10,
    "cryptoslate":        8,
    "cryptobriefing":     9,
    "coindesk":          11,
    "twitter":            6,
    "unknown":            5,
}

# Sumber yang kena News Gate Rule
# Airdrop scraper TIDAK masuk sini — mereka memang spesialisasi farming
NEWS_SOURCES = {
    "cointelegraph", "decrypt", "theblock", "blockworks",
    "cryptobriefing", "cryptoslate", "coindesk", "crypto_news",
}

CATEGORY_WEIGHTS = {
    "high_value": 4,
    "ai_agent":   3,
    "web3":       1,
}


def score_project(
    title: str,
    description: str,
    source: str,
    published_at: datetime | None = None,
    stars: int = 0,
    forks: int = 0,
) -> dict:
    text = f"{title} {description}".lower()

    # ── 1. Keyword Relevance (max 40 pts) ────────────────────────────
    matched_kw     = []
    kw_score       = 0
    has_high_value = False

    for kw in HIGH_VALUE_KEYWORDS:
        if kw in text:
            kw_score += CATEGORY_WEIGHTS["high_value"]
            matched_kw.append(f"🎯 {kw}")
            has_high_value = True

    for kw in AI_AGENT_KEYWORDS:
        if kw in text and f"🤖 {kw}" not in matched_kw:
            kw_score += CATEGORY_WEIGHTS["ai_agent"]
            matched_kw.append(f"🤖 {kw}")

    for kw in WEB3_KEYWORDS:
        if kw in text and f"⛓ {kw}" not in matched_kw:
            kw_score += CATEGORY_WEIGHTS["web3"]
            matched_kw.append(f"⛓ {kw}")

    kw_score = min(kw_score, 40)

    # ── 2. Recency (max 20 pts) ───────────────────────────────────────
    recency_score = 0
    if published_at:
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - published_at).total_seconds() / 3600
        if age_hours <= 6:
            recency_score = 20
        elif age_hours <= 24:
            recency_score = 15
        elif age_hours <= 72:
            recency_score = 10
        elif age_hours <= 168:
            recency_score = 5

    # ── 3. Source Credibility (max 20 pts) ───────────────────────────
    src_key    = source.lower()
    cred_score = SOURCE_CREDIBILITY.get(src_key, SOURCE_CREDIBILITY["unknown"])

    # ── 4. Engagement Signals (max 20 pts) ───────────────────────────
    engagement_score = 0
    if stars > 0 or forks > 0:
        if stars >= 500 or forks >= 100:
            engagement_score = 20
        elif stars >= 100 or forks >= 20:
            engagement_score = 15
        elif stars >= 20:
            engagement_score = 10
        elif stars >= 5:
            engagement_score = 5
    else:
        engagement_score = 5

    total = kw_score + recency_score + cred_score + engagement_score

    # ── NEWS GATE ─────────────────────────────────────────────────────
    # Artikel berita tanpa HIGH_VALUE_KEYWORD → bukan farming opportunity
    # Cap di 25 (satu angka di bawah default threshold 30)
    if src_key in NEWS_SOURCES and not has_high_value:
        total = min(total, 25)

    return {
        "total":          min(total, 100),
        "breakdown": {
            "keywords":    kw_score,
            "recency":     recency_score,
            "credibility": cred_score,
            "engagement":  engagement_score,
        },
        "matched_kw":     matched_kw[:8],
        "has_high_value": has_high_value,
    }


def score_label(score: int) -> str:
    if score >= 75:
        return "🔥🔥🔥 ULTRA ALPHA"
    elif score >= 60:
        return "🔥🔥 HIGH POTENTIAL"
    elif score >= 45:
        return "🔥 INTERESTING"
    elif score >= 30:
        return "👀 WORTH WATCHING"
    else:
        return "📌 LOW SIGNAL"
