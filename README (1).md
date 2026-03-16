# 🧠 Smart Money Divergence Detector

> A live web app that finds tokens where **Smart Money is accumulating while retail is fearful** — across 9 blockchains — with automatic Telegram alerts.

🔗 **Live App:** [smart-money-divergence-dectector.streamlit.app](https://smart-money-divergence-dectector.streamlit.app)

Built with the [Nansen API](https://app.nansen.ai) for the **#NansenCLI** competition.

---

## What It Does

The app calls the Nansen API to scan multiple blockchains for tokens where Smart Money wallets are **buying while price is falling** — the classic institutional accumulation signal. It scores every token on a Divergence Index, ranks them, and sends Telegram alerts automatically.

1. Calls the **Nansen token screener API** per chain to find Smart Money active tokens
2. Calls the **Nansen Smart Money flows API** to get net USD flows
3. Scores each token on a **Divergence Index (0–100)**
4. Displays a **live ranked dashboard** in the browser
5. Clicking any token opens it directly on **DexScreener** for instant analysis
6. Fires **Telegram alerts** with top 5 signals after every scan

---

## Divergence Score Breakdown

| Points | Signal | What It Means |
|--------|--------|--------------|
| 40 pts | SM Netflow | Smart Money buying (positive = accumulating) |
| 30 pts | Price drop | Retail fear while SM buys = divergence |
| 20 pts | SM trader count | More distinct SM wallets = stronger signal |
| 10 pts | Holder distribution | Low whale concentration = safer entry |

---

## Supported Chains (9 total)

| | | | |
|--|--|--|--|
| ETH — Ethereum | SOL — Solana | BASE — Base | BNB — BNB Chain |
| ARB — Arbitrum | POL — Polygon | OP — Optimism | AVAX — Avalanche |
| LNA — Linea | | | |

---

## How to Use the App (3 Steps)

### Step 1 — Get Nansen Credits & API Key
1. Go to **[app.nansen.ai](https://app.nansen.ai)** and sign up
2. Top up your account with credits (pay as you go)
3. Go to **Settings → API Keys** → create a key and copy it

### Step 2 — Set Up Telegram Bot (Free, 5 minutes)
1. Open Telegram → search **@BotFather**
2. Send `/newbot` → follow prompts → copy the **bot token**
3. Send any message to your new bot
4. Visit this URL (replace TOKEN):
   ```
   https://api.telegram.org/botTOKEN/getUpdates
   ```
5. Find `"id"` inside `"chat"` — that is your **Chat ID**

### Step 3 — Open the App & Scan
1. Go to **[smart-money-divergence-dectector.streamlit.app](https://smart-money-divergence-dectector.streamlit.app)**
2. In the sidebar, paste your:
   - **Nansen API Key**
   - **Telegram Bot Token** (optional)
   - **Telegram Chat ID** (optional)
3. Select your chains (ETH + SOL + BASE on by default)
4. Set your minimum score filter
5. Hit **🔍 Run Scan Now**

Results appear instantly. Click any token name to open it directly on DexScreener. If Telegram is configured, alerts fire automatically after every scan.

---

## The Economics

| Item | Cost |
|------|------|
| This app | **Free** |
| Streamlit Cloud hosting | **Free** |
| Telegram bot | **Free** |
| Nansen API credits | Pay as you go at app.nansen.ai |

The only cost is Nansen API credits — the app itself is completely free.

---

## Privacy & Security

- Your API keys are **session-only** — they are never stored on any server
- Keys go directly from your browser to the Nansen and Telegram APIs only
- The app source code is fully open on GitHub

---

## Nansen API Calls Made Per Scan

| API Call | Purpose |
|---------|---------|
| `POST /api/v1/token-screener` | Smart Money active tokens per chain |
| `POST /api/v1/smart-money/flows` | Net USD flows from SM wallets |

Each scan calls the token screener **once per selected chain** (e.g. 3 chains = 3 screener calls + 1 flows call = **4+ API calls per scan**). Selecting all 9 chains makes **10+ API calls** per scan.

---

## Run Locally (Developer Setup)

```bash
# Clone the repo
git clone https://github.com/Angelmyk1/smart-money-divergence-dectector
cd smart-money-divergence-dectector

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

**Requirements:**
- Python 3.9+
- `streamlit>=1.32.0`
- `requests>=2.31.0`

No CLI installation needed — the app calls the Nansen REST API directly.

---

## Sample Output

```
📊 Top Divergence Signals (50 tokens scanned)

#01  EVE ↗   [BASE]                          13.2 pts
     SM Netflow: $2.9K   Price 24h: ▲ 0.0%   SM Traders: 1

#02  NOCK ↗  [BASE]                          12.8 pts
     SM Netflow: $2.7K   Price 24h: ▲ 0.4%   SM Traders: 1

#03  JAN ↗   [SOL]                           12.2 pts
     SM Netflow: $2.4K   Price 24h: ▲ 1.4%   SM Traders: 1
```

---

## Sample Telegram Alert

```
🧠 Smart Money Divergence Alert
2025-03-17 12:00 UTC

!! 1. EVE [base]
   Score: 13.2 | Flow: $2.9K | +0.0%

-> 2. NOCK [base]
   Score: 12.8 | Flow: $2.7K | +0.4%

Not financial advice. Built with Nansen API
```

---

## Disclaimer

Not financial advice. For educational and research purposes only. Always do your own research before making any investment decisions.

---

*Built for the [#NansenCLI](https://twitter.com/search?q=%23NansenCLI) competition | [@nansen_ai](https://twitter.com/nansen_ai)*
