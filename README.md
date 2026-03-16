# 🔍 Web3 Alpha Scraper

> Automated multi-source scraper untuk farming reward, airdrop, testnet incentivized, points campaign, dan early-stage Web3/AI Agent projects — lengkap dengan scoring, deduplication, GitHub Actions, dan Telegram notifikasi.

---

## 📡 Sources yang Di-scrape

| Source | Endpoint | Refresh | Notes |
|--------|----------|---------|-------|
| **Airdrop Aggregators** | airdrops.io, airdropalert.com, DeFiLlama Airdrops | Every 4h | Paling langsung untuk farming |
| **DeFiLlama** | `/protocols` API | Every 4h | Protocol baru dengan TVL data |
| **CoinGecko** | `/search/trending` + coin detail | Every 4h | Trending = community buzz |
| **Crypto News RSS** | CoinTelegraph, Decrypt, The Block, Blockworks, CoinDesk, dll | Every 4h | Text-rich untuk keyword scoring |
| **GitHub** | Search API — repos baru < 7 hari | Every 4h | Devs push code sebelum marketing |
| **Twitter/X** | Nitter RSS (free) atau API v2 (opsional) | Every 4h | Paling real-time, tapi paling noisy |

---

## 🧠 Scoring System (0–100)

Setiap project dapat skor berdasarkan 4 faktor:

```
Keywords relevance  ─── up to 40 pts
  🎯 High-value kw  : "airdrop", "testnet", "incentivized", "points", dll → 4 pts each
  🤖 AI Agent kw    : "ai agent", "on-chain ai", "zkml", dll              → 3 pts each
  ⛓  Web3 kw        : "defi", "rollup", "restaking", "depin", dll         → 1 pt each

Recency             ─── up to 20 pts
  ≤ 6 hours old     → 20 pts
  ≤ 24 hours old    → 15 pts
  ≤ 72 hours old    → 10 pts
  ≤ 1 week old      → 5 pts

Source Credibility  ─── up to 20 pts
  DeFiLlama         → 20 pts
  CoinGecko         → 18 pts
  The Block         → 16 pts
  GitHub            → 15 pts
  CoinTelegraph     → 12 pts
  Twitter           → 6 pts

Engagement          ─── up to 20 pts
  GitHub: stars/forks based
  News/Airdrop: default 5 pts
```

**Tiers:**
- 🔥🔥🔥 **ULTRA ALPHA** → score ≥ 75
- 🔥🔥 **HIGH POTENTIAL** → score ≥ 60
- 🔥 **INTERESTING** → score ≥ 45
- 👀 **WORTH WATCHING** → score ≥ 30
- 📌 **LOW SIGNAL** → score < 30

Default threshold notifikasi: **30/100** (bisa diubah di `config.py`)

---

## 🚀 Setup: Langkah demi Langkah

### 1. Fork / Clone Repo ini

```bash
git clone https://github.com/USERNAME/web3-alpha-scraper.git
cd web3-alpha-scraper
```

### 2. Buat Telegram Bot

1. Buka Telegram → cari **@BotFather**
2. Kirim `/newbot` → ikuti instruksi → copy **Bot Token**
3. Tambahkan bot ke grup atau DM bot-nya
4. Dapatkan **Chat ID**:
   - DM: chat dengan @userinfobot → copy angka `Id`
   - Group: tambahkan bot ke grup, kirim pesan, lalu buka:  
     `https://api.telegram.org/bot<TOKEN>/getUpdates`  
     Cari field `"chat":{"id":...}` — angka negatif = group chat ID

### 3. Set GitHub Secrets

Buka repo GitHub → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret Name | Value | Wajib? |
|-------------|-------|--------|
| `TELEGRAM_BOT_TOKEN` | Token dari @BotFather | ✅ Ya |
| `TELEGRAM_CHAT_ID` | Chat/Group ID kamu | ✅ Ya |
| `GH_PAT` | GitHub Personal Access Token (repo scope) | ✅ Ya (untuk GitHub scraper) |
| `TWITTER_BEARER_TOKEN` | Twitter API v2 Bearer Token | ❌ Opsional |

**Cara buat GH_PAT:**
GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token → centang `repo` → copy token

### 4. Aktifkan GitHub Actions

Actions sudah ada di `.github/workflows/`. Setelah push repo:
1. Buka tab **Actions** di GitHub repo
2. Actions akan jalan otomatis sesuai schedule (`*/4 * * * *` = setiap 4 jam)
3. Untuk test manual: Actions → **Web3 Alpha Scraper** → **Run workflow**

### 5. (Opsional) Jalankan Lokal

```bash
pip install -r requirements.txt

# Set env variables dulu
export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHAT_ID="your_chat_id"
export GITHUB_TOKEN="your_gh_pat"

# Run semua sources
python main.py

# Run source tertentu saja
python main.py --source github
python main.py --source airdrop
python main.py --source defillama

# Dry run (tanpa kirim Telegram)
python main.py --dry-run
```

---

## 📁 Struktur Project

```
web3-alpha-scraper/
├── main.py                     # Orchestrator utama
├── config.py                   # Semua config & keywords
├── weekly_digest.py            # Weekly summary report
├── requirements.txt
│
├── scrapers/
│   ├── airdrop_scraper.py      # airdrops.io, airdropalert, DeFiLlama airdrops
│   ├── defillama_scraper.py    # DeFiLlama protocols API
│   ├── coingecko_scraper.py    # CoinGecko trending + new listings
│   ├── news_scraper.py         # 7 RSS feeds crypto news
│   ├── github_scraper.py       # GitHub new repos search
│   └── twitter_scraper.py      # Nitter RSS / Twitter API v2
│
├── utils/
│   ├── dedup.py                # Deduplication engine (seen.json)
│   ├── scorer.py               # Scoring algorithm (0–100)
│   └── telegram_notifier.py    # Telegram bot sender
│
├── data/
│   └── seen.json               # State file (di-commit otomatis oleh Actions)
│
└── .github/
    └── workflows/
        ├── scraper.yml          # Main workflow (every 4h)
        └── weekly_digest.yml    # Weekly digest (every Monday)
```

---

## 📲 Contoh Notifikasi Telegram

```
🔥🔥🔥 ULTRA ALPHA  |  Score: 82/100
━━━━━━━━━━━━━━━━━━━━━━
📌 MegaETH Incentivized Testnet Launch
🔗 Source: theblock

📝 MegaETH announces incentivized testnet with points campaign
for early node operators and liquidity providers. Season 1 
rewards distributed based on activity metrics...

🏷 Keywords: 🎯 testnet, 🎯 incentivized, 🎯 points, 🎯 node runner

📊 Breakdown:
   • Keywords:    32/40
   • Recency:     20/20
   • Credibility: 16/20
   • Engagement:  14/20

🔗 → Open Project
```

---

## ⚙️ Kustomisasi

### Tambah Keywords
Edit `config.py`:
```python
HIGH_VALUE_KEYWORDS = [
    "airdrop", "testnet", "incentivized",
    # Tambah keyword baru di sini ↓
    "season 2", "snapshot", "retroactive",
]
```

### Ubah Threshold Score
```python
MIN_SCORE_TO_NOTIFY = 30  # Naikan untuk lebih selektif
```

### Ubah Jadwal Run
Edit `.github/workflows/scraper.yml`:
```yaml
- cron: "0 */4 * * *"   # Setiap 4 jam (default)
- cron: "0 */2 * * *"   # Setiap 2 jam (lebih sering)
- cron: "0 * * * *"     # Setiap jam (maksimal)
```

### Tambah Akun Twitter yang Dipantau
Edit `scrapers/twitter_scraper.py`:
```python
ALPHA_ACCOUNTS = [
    "CryptoKoryo",
    # Tambah handle akun alpha di sini ↓
    "YourFavoriteAlphaAccount",
]
```

---

## 🔄 Deduplication: Cara Kerja

`data/seen.json` adalah "memori" bot:
- Setiap project pertama kali ditemukan → ID-nya disimpan di `seen.json`
- Runs berikutnya → cek dulu apakah ID sudah ada → skip jika sudah
- Setelah setiap run, GitHub Actions commit `seen.json` balik ke repo
- Entry yang sudah > 30 hari otomatis dihapus (agar file tetap kecil)

---

## 🐛 Troubleshooting

| Problem | Solusi |
|---------|--------|
| Tidak ada notif Telegram | Cek `TELEGRAM_BOT_TOKEN` dan `TELEGRAM_CHAT_ID` di Secrets |
| GitHub scraper error 403 | `GH_PAT` belum di-set atau expired — buat token baru |
| Nitter tidak bisa di-akses | Instance Nitter down — coba ganti list di `twitter_scraper.py` |
| Terlalu banyak notif | Naikan `MIN_SCORE_TO_NOTIFY` di `config.py` (coba 45–60) |
| Terlalu sedikit notif | Turunkan threshold atau tambah keywords |
| Actions tidak berjalan | Cek tab Actions → pastikan Actions diaktifkan di repo |

---

## ⚠️ Disclaimer

Tool ini hanya untuk riset dan pengumpulan informasi publik. 
Selalu DYOR (Do Your Own Research) sebelum berpartisipasi dalam 
airdrop, testnet, atau farming program apapun. Tidak ada yang namanya
"guaranteed reward" di Web3.

---

## 📜 License

MIT — gunakan, modifikasi, dan bagikan dengan bebas.
