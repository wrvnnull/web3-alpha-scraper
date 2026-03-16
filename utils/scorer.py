"""
utils/scorer.py — Project Potential Scorer
--------------------------------------------
Scores each discovered project 0–100 based on signals that historically
correlate with high farming/reward potential. Think of it like a credit
score, but for Web3 alpha opportunities.

Score breakdown:
  - Keyword relevance  : up to 40 pts
  - Recency            : up to 20 pts
  - Source credibility : up to 20 pts
  - Engagement signals : up to 20 pts
"""

from datetime import datetime, timezone
from config import HIGH_VALUE_KEYWORDS, WEB3_KEYWORDS, AI_AGENT_KEYWORDS

# Source trust tiers — more trustworthy = higher base score
SOURCE_CREDIBILITY = {
    "defillama":    20,
    "coingecko":    18,
    "github":       15,
    "theblock":     16,
    "blockworks":   15,
    "decrypt":      14,
    "cointelegraph": 12,
    "airdrops_io":  10,
    "airdrop_alert": 8,
    "cryptoslate":   8,
    "twitter":       6,   # noisy, but sometimes first-mover
    "unknown":       5,
}

# Score multipliers per keyword category
# High-value = explicit reward/farming signals → worth more
CATEGORY_WEIGHTS = {
    "high_value": 4,   # "airdrop", "testnet incentivized", etc.
    "ai_agent":   3,   # AI agent protocols are ultra-hot in 2025
    "web3":       1,   # general Web3 — everyone is doing this
}


def score_project(
    title: str,
    description: str,
    source: str,
    published_at: datetime | None = None,
    stars: int = 0,
    forks: int = 0,
) -> dict:
    """
    Given a project's metadata, return a scoring dict:
    {
        "total": int,       # 0–100
        "breakdown": dict,  # per-category scores for transparency
        "matched_kw": list, # which keywords triggered
    }
    """
    text = f"{title} {description}".lower()

    # ── 1. Keyword Relevance (max 40 pts) ────────────────────────────
    matched_kw   = []
    kw_score     = 0

    for kw in HIGH_VALUE_KEYWORDS:
        if kw in text:
            kw_score += CATEGORY_WEIGHTS["high_value"]
            matched_kw.append(f"🎯 {kw}")

    for kw in AI_AGENT_KEYWORDS:
        if kw in text and kw not in matched_kw:
            kw_score += CATEGORY_WEIGHTS["ai_agent"]
            matched_kw.append(f"🤖 {kw}")

    for kw in WEB3_KEYWORDS:
        if kw in text and kw not in matched_kw:
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
        elif age_hours <= 168:  # 1 week
            recency_score = 5

    # ── 3. Source Credibility (max 20 pts) ───────────────────────────
    src_key = source.lower()
    cred_score = SOURCE_CREDIBILITY.get(src_key, SOURCE_CREDIBILITY["unknown"])

    # ── 4. Engagement Signals (max 20 pts) ───────────────────────────
    # Stars/forks for GitHub repos; for news we default to 5
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
        engagement_score = 5  # news/airdrop items — neutral

    total = kw_score + recency_score + cred_score + engagement_score

    return {
        "total": min(total, 100),
        "breakdown": {
            "keywords":    kw_score,
            "recency":     recency_score,
            "credibility": cred_score,
            "engagement":  engagement_score,
        },
        "matched_kw": matched_kw[:8],  # top 8 to keep Telegram msg readable
    }


def score_label(score: int) -> str:
    """Convert numeric score into a human-readable tier label."""
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
