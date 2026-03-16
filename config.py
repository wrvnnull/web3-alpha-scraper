"""
config.py — Central configuration for Web3 Alpha Scraper
All sensitive values (tokens, keys) are read from environment variables,
which will be set as GitHub Secrets in your repo.
"""

import os

# ─────────────────────────────────────────────
# TELEGRAM CONFIG (set as GitHub Secret)
# ─────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")

# ─────────────────────────────────────────────
# GITHUB API (set as GitHub Secret — use your PAT)
# ─────────────────────────────────────────────
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# ─────────────────────────────────────────────
# OPTIONAL: Twitter/X Bearer Token (expensive, optional)
# ─────────────────────────────────────────────
TWITTER_BEARER_TOKEN = os.environ.get("TWITTER_BEARER_TOKEN", "")

# ─────────────────────────────────────────────
# SCORING THRESHOLDS
# Only projects with score >= MIN_SCORE will be notified
# ─────────────────────────────────────────────
MIN_SCORE_TO_NOTIFY = 30   # out of 100

# ─────────────────────────────────────────────
# KEYWORDS — used to filter & score projects
# Higher-weight = more likely to be early alpha with rewards
# ─────────────────────────────────────────────
HIGH_VALUE_KEYWORDS = [
    "airdrop", "testnet", "incentivized", "points", "rewards",
    "early access", "alpha", "beta", "whitelist", "waitlist",
    "season", "campaign", "genesis", "og", "pioneer",
    "node runner", "validator", "grant", "bounty",
]

WEB3_KEYWORDS = [
    "blockchain", "defi", "dex", "nft", "dao", "layer2", "layer 2",
    "zk", "zkvm", "zkp", "rollup", "bridge", "restaking", "staking",
    "liquid staking", "intent", "account abstraction", "aa wallet",
    "modular", "data availability", "sequencer", "prover",
    "ai agent", "on-chain ai", "depin", "rwa", "real world asset",
    "gamefi", "socialfi", "perpetual", "perp dex", "lending",
    "yield", "vault", "strategy", "cross-chain", "omnichain",
    "solana", "ethereum", "cosmos", "sui", "aptos", "monad",
    "berachain", "megaeth", "base", "arbitrum", "optimism",
]

AI_AGENT_KEYWORDS = [
    "ai agent", "autonomous agent", "agent framework", "multi-agent",
    "llm on-chain", "on-chain ai", "ai protocol", "inference network",
    "verifiable ai", "zkml", "opml", "ai oracle", "agent economy",
]

# ─────────────────────────────────────────────
# GITHUB SEARCH QUERIES
# These target brand-new repos likely to be early-stage Web3 projects
# ─────────────────────────────────────────────
GITHUB_SEARCH_QUERIES = [
    "web3 airdrop testnet 2025",
    "blockchain ai agent protocol",
    "defi alpha points rewards",
    "zkvm rollup incentivized testnet",
    "depin node runner rewards",
    "on-chain ai agent framework",
    "restaking protocol points season",
    "layer2 monad berachain megaeth",
]

# ─────────────────────────────────────────────
# NEWS RSS FEEDS — reliable crypto news sources
# ─────────────────────────────────────────────
NEWS_RSS_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://decrypt.co/feed",
    "https://www.theblock.co/rss.xml",
    "https://blockworks.co/feed",
    "https://cryptobriefing.com/feed/",
    "https://cryptoslate.com/feed/",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
]

# ─────────────────────────────────────────────
# AIRDROP AGGREGATOR SITES
# ─────────────────────────────────────────────
AIRDROP_SITES = {
    "airdrops_io":      "https://airdrops.io/",
    "earnifi":          "https://earnifi.com/",
    "airdrop_alert":    "https://airdropalert.com/",
    "defi_airdrops":    "https://defillama.com/airdrops",
}

# ─────────────────────────────────────────────
# DEDUP STATE FILE — tracks seen project IDs
# In GitHub Actions, this is committed back to the repo
# ─────────────────────────────────────────────
SEEN_FILE = "data/seen.json"
SEEN_TTL_DAYS = 30  # forget entries older than 30 days to keep file small
