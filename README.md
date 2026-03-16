# 🧠 Smart Money Divergence Detector

> Find tokens where **Smart Money is buying while retail is fearful** — across Ethereum, Solana, and Base — with Telegram alerts.

Built with the [Nansen CLI](https://agents.nansen.ai) for the #NansenCLI competition.

---

## What It Does

1. Pulls **token screener data** across ETH, SOL, and Base via Nansen CLI
2. Fetches **Smart Money netflows** (Fund + Smart Trader + 30D Smart Trader labels)
3. Scores each token on a **Divergence Index (0–100)**:
   - Smart Money netflow (positive = accumulating) → up to 40 pts
   - Price momentum (negative price + SM buying = opportunity) → up to 30 pts
   - Smart Money trader count → up to 20 pts
   - Holder concentration (lower concentration = safer) → up to 10 pts
4. Prints a **ranked table** to terminal
5. Saves a **Markdown report** locally
6. Fires a **Telegram alert** with the top signals

---

## Setup (5 Steps)

### Step 1 — Install Python 3.9+
```bash
python3 --version   # Should be 3.9 or higher
```
If not installed: https://www.python.org/downloads/

---

### Step 2 — Install Nansen CLI
```bash
# Visit https://agents.nansen.ai and follow the install instructions
# Verify install:
nansen --version
```

---

### Step 3 — Get Your Nansen API Key
1. Go to https://app.nansen.ai
2. Sign in → Settings → API Keys
3. Create a new key and copy it

---

### Step 4 — Set Up Telegram Bot
1. Open Telegram → search for **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy the **bot token** (looks like `7123456789:AAF...`)
4. Send any message to your new bot
5. Visit this URL in your browser (replace `TOKEN`):
   ```
   https://api.telegram.org/botTOKEN/getUpdates
   ```
6. Find `"id"` inside `"chat"` — that's your **Chat ID**

---

### Step 5 — Configure & Run
```bash
# Install Python dependencies
pip install -r requirements.txt

# Open config.py and fill in your 3 values:
#   NANSEN_API_KEY
#   TELEGRAM_BOT_TOKEN
#   TELEGRAM_CHAT_ID

# Run it!
python detector.py
```

---

## Sample Output

```
════════════════════════════════════════════════════════════
  🔍 SMART MONEY DIVERGENCE DETECTOR
  Chains: ethereum, solana, base
  2025-03-16 09:42 UTC
════════════════════════════════════════════════════════════

▶ Scanning ETHEREUM...
  📡 Token screener [ethereum]...
  📡 Smart money netflow [ethereum]...
  ✓ Found 38 screener tokens, 22 netflow entries

▶ Scanning SOLANA...
...

════════════════════════════════════════════════════════════
  📊 TOP DIVERGENCE SIGNALS
════════════════════════════════════════════════════════════
  #   Symbol     Chain    Score   SM Flow      Δ Price    SM Traders
  ──────────────────────────────────────────────────────────────────
  1   TOKEN_A    eth      78.5    $2.1M        🔴-8.3%    14
  2   TOKEN_B    sol      65.0    $890K        🔴-5.1%    9
  3   TOKEN_C    base     54.5    $420K        🔴-3.7%    6
  ...
════════════════════════════════════════════════════════════
```

---

## Run on a Schedule (Optional)

**Mac/Linux — run every hour:**
```bash
crontab -e
# Add this line:
0 * * * * cd /path/to/smart-money-divergence && python detector.py >> log.txt 2>&1
```

**Windows — Task Scheduler:**
Create a basic task to run `python detector.py` hourly.

---

## Nansen CLI Commands Used

| Command | Purpose |
|---------|---------|
| `nansen token screener` | Smart Money active tokens per chain |
| `nansen smart-money netflow` | Net USD flows from SM wallets |
| `nansen token holders` | Holder concentration check |
| `nansen smart-money pnl-leaderboard` | Retail PnL momentum |
| `nansen token flows` | Detailed flow intelligence |

Each full run makes **10+ API calls** across 3 chains.

---

## Disclaimer
Not financial advice. For educational and research purposes only.

---

*Built for the [#NansenCLI](https://twitter.com/search?q=%23NansenCLI) competition | [@nansen_ai](https://twitter.com/nansen_ai)*
