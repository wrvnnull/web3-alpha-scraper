#!/usr/bin/env bash
# setup.sh — One-shot local setup script
# Run: chmod +x setup.sh && ./setup.sh

set -e

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║     Web3 Alpha Scraper — Local Setup     ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── Python version check ────────────────────────────────────────────
PYTHON=$(command -v python3 || command -v python)
if [ -z "$PYTHON" ]; then
  echo "❌ Python not found. Install Python 3.10+ first."
  exit 1
fi
echo "✅ Python: $($PYTHON --version)"

# ── Create virtualenv ───────────────────────────────────────────────
if [ ! -d ".venv" ]; then
  echo "📦 Creating virtual environment..."
  $PYTHON -m venv .venv
fi

# Activate
source .venv/bin/activate
echo "✅ Virtual environment activated"

# ── Install dependencies ────────────────────────────────────────────
echo "📦 Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "✅ Dependencies installed"

# ── Create data directory ───────────────────────────────────────────
mkdir -p data
if [ ! -f data/seen.json ]; then
  echo "{}" > data/seen.json
  echo "✅ Created data/seen.json"
fi

# ── Create .env file template ───────────────────────────────────────
if [ ! -f .env ]; then
  cat > .env << 'EOF'
# Copy this file and fill in your values
# Then run: source .env

export TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN_HERE"
export TELEGRAM_CHAT_ID="YOUR_CHAT_ID_HERE"
export GITHUB_TOKEN="YOUR_GITHUB_PAT_HERE"

# Optional — only needed for Twitter official API
# export TWITTER_BEARER_TOKEN="YOUR_TWITTER_BEARER_TOKEN"
EOF
  echo "✅ Created .env template — fill in your credentials"
else
  echo "ℹ️  .env already exists"
fi

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║           Setup Complete! 🎉             ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "  1. Fill in your credentials in .env"
echo "  2. Run: source .env"
echo "  3. Test run: python main.py --dry-run"
echo "  4. Live run: python main.py"
echo ""
echo "Run a specific source only:"
echo "  python main.py --source airdrop"
echo "  python main.py --source github"
echo "  python main.py --source defillama"
echo ""
