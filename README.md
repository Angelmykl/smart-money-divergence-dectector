# 🧠 Smart Money Divergence Detector

> A live web app that finds tokens where **Smart Money is accumulating while retail is fearful** — across 9 blockchains — with automatic Telegram alerts, new token detection, watchlist, and scan history.

🔗 **Live App:** [smart-money-divergence-dectector.streamlit.app](https://smart-money-divergence-dectector.streamlit.app)

Built with the [Nansen API](https://app.nansen.ai) for the **#NansenCLI** competition.

---

## What It Does

The app calls the Nansen REST API to scan multiple blockchains for tokens where Smart Money wallets are **buying while price is falling** — the classic institutional accumulation signal. It scores every token on a Divergence Index, ranks them on a live dashboard, and sends Telegram alerts automatically on a schedule you set.

1. Calls **Nansen token screener API** per chain to find Smart Money active tokens
2. Calls **Nansen Smart Money flows API** to get net USD flows
3. Scores each token on a **Divergence Index (0–100)**
4. Displays a **live ranked dashboard** with token age, chain badges and scores
5. Clicking any token opens it directly on **DexScreener** for instant research
6. **New token detection** — flags tokens not seen in previous scans
7. **Auto-scan scheduler** — runs automatically at your chosen interval
8. **Telegram alerts** fire after every scan with top 5 signals
9. **Watchlist** — star tokens you want to track
10. **Scan history** — shows your last 5 scan results
11. **API call counter** — tracks your Nansen credit usage

---

## Divergence Score Breakdown

| Points | Signal | What It Means |
|--------|--------|--------------|
| 40 pts | SM Netflow | Smart Money buying (positive = accumulating) |
| 30 pts | Price drop | Retail fear while SM buys = divergence signal |
| 20 pts | SM trader count | More distinct SM wallets = stronger signal |
| 10 pts | Holder distribution | Low whale concentration = safer entry |

---

## Supported Chains (9 total)

| Chain | Label | Chain | Label |
|-------|-------|-------|-------|
| Ethereum | ETH | BNB Chain | BNB |
| Solana | SOL | Arbitrum | ARB |
| Base | BASE | Polygon | POL |
| Optimism | OP | Avalanche | AVAX |
| Linea | LNA | | |

---

## How to Use the App

### Step 1 — Get Nansen Credits & API Key
1. Go to **[app.nansen.ai](https://app.nansen.ai)** and sign up
2. Top up your account with credits (pay as you go)
3. Go to **Settings → API Keys** → create a key and copy it

> Each scan makes **1 API call per selected chain** for the token screener + 1 for Smart Money flows. Scanning all 9 chains = 10 API calls per scan.

### Step 2 — Set Up Telegram Bot (Free, 5 minutes)
1. Open Telegram → search **@BotFather**
2. Send `/newbot` → follow prompts → copy the **bot token**
3. Send any message to your new bot
4. Visit this URL in your browser (replace TOKEN with your token):
   ```
   https://api.telegram.org/botTOKEN/getUpdates
   ```
5. Find `"id"` inside `"chat"` — that is your **Chat ID**

### Step 3 — Open the App & Start Scanning
1. Go to **[smart-money-divergence-dectector.streamlit.app](https://smart-money-divergence-dectector.streamlit.app)**
2. In the sidebar paste your **Nansen API Key**, **Telegram Bot Token** and **Chat ID**
3. Select your chains (ETH + SOL + BASE on by default)
4. Set your minimum score filter
5. Choose your scan interval (15 min → 24 hours)
6. Hit **🔍 Run Scan Now** for a one-time scan, or **▶ Start** for continuous auto-scanning

---

## Feature Guide

### 🆕 New Token Detection
Toggle **"New tokens only"** in the sidebar. When ON:
- The app tracks every token address it has ever seen
- Only alerts you when **fresh Smart Money activity** appears on a token not seen before
- Telegram alerts show **(X NEW)** in the title
- New tokens get a glowing **NEW** badge and highlighted card border on the dashboard
- On your first scan, all tokens appear as NEW. From the second scan onwards, only genuinely new tokens trigger alerts

### ⏱️ Auto-Scan Scheduler
- Select your interval: **Every 15 min / 30 min / 1hr / 2hr / 4hr / 12hr / 24hr**
- Hit **▶ Start** — scans run automatically in the background
- Telegram alerts fire after every scan
- Hit **⏹ Stop** to pause
- Sidebar shows scan count and total API calls used

> Note: The scheduler runs inside your browser session. Closing the tab will stop it. Keep the tab open for continuous monitoring.

### ★ Watchlist
- Click the **☆** star button next to any token to add it to your watchlist
- Watchlist appears in the sidebar
- Click **✕** to remove a token from the watchlist

### 🕐 Scan History
- The last 5 scan results are shown at the bottom of the dashboard
- Each entry shows timestamp, total tokens scanned, signals found, new token count and chains used

### 📊 API Calls Counter
- The 5th metric box shows total API calls used in your current session
- Helps you track your Nansen credit consumption

---

## Nansen API Endpoints Used

| Endpoint | Purpose |
|---------|---------|
| `POST /api/v1/token-screener` | Smart Money active tokens (called once per chain) |
| `POST /api/v1/smart-money/flows` | Net USD flows from SM wallets |

---

## The Economics

| Item | Cost |
|------|------|
| This app | **Free** |
| Streamlit Cloud hosting | **Free** |
| Telegram bot | **Free** |
| Nansen API credits | Pay as you go at app.nansen.ai |

---

## Privacy & Security

- Your API keys are **session-only** — never stored on any server
- Keys go directly from your browser to Nansen and Telegram APIs only
- Full source code is open on GitHub

---

## Run Locally

```bash
# Clone the repo
git clone https://github.com/Angelmyk1/smart-money-divergence-dectector
cd smart-money-divergence-dectector

# Install dependencies
pip install -r requirements.txt

# Run
streamlit run app.py
```

**Requirements:** Python 3.9+ · `streamlit>=1.32.0` · `requests>=2.31.0`

No CLI installation needed — uses Nansen REST API directly.

---

## Sample Telegram Alert

```
Smart Money Divergence Alert (3 NEW)
2026-03-17 15:36 UTC

-> 1. OTTIE 🆕 [base]
   Score: 13.5 | Flow: $6.8K | -0.3%

-> 2. WAR 🆕 [solana]
   Score: 13.2 | Flow: $6.4K | -0.3%

-> 3. EXO 🆕 [base]
   Score: 13.2 | Flow: $2.9K | +0.3%

Not financial advice. Built with Nansen API
```

---

## Disclaimer

Not financial advice. For educational and research purposes only. Always do your own research before making any investment decisions.

---

*Built for the [#NansenCLI](https://twitter.com/search?q=%23NansenCLI) competition | [@nansen_ai](https://twitter.com/nansen_ai)*