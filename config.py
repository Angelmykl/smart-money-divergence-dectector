# ─────────────────────────────────────────────
# config.py  —  Smart Money Divergence Detector
# ─────────────────────────────────────────────
# Fill in your keys below, then run: python detector.py
# ─────────────────────────────────────────────

# ── Nansen ───────────────────────────────────
# Get your key at: https://app.nansen.ai → Settings → API
NANSEN_API_KEY = "YOUR_NANSEN_API_KEY_HERE"

# ── Telegram ─────────────────────────────────
# Step 1: Message @BotFather on Telegram → /newbot → copy the token
# Step 2: Message your bot once, then get your chat_id from:
#         https://api.telegram.org/bot<TOKEN>/getUpdates
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID   = "YOUR_TELEGRAM_CHAT_ID_HERE"   # e.g. "123456789"

# ── Chains to Monitor ─────────────────────────
CHAINS = ["ethereum", "solana", "base"]

# ── Filters ───────────────────────────────────
MIN_MARKET_CAP_USD     = 1_000_000   # $1M minimum — filters micro-cap noise
MIN_SMART_MONEY_TRADERS = 3           # At least 3 SM wallets active

# ── Output ────────────────────────────────────
TOP_N_RESULTS = 10   # How many top tokens to show in the report
