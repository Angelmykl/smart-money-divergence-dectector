# 🧠 Smart Money Divergence Detector

> Find tokens where **Smart Money is buying while retail is fearful** — across 9 chains — with a live web dashboard and automatic Telegram alerts.

Built with the [Nansen CLI](https://agents.nansen.ai) for the #NansenCLI competition.

---

## What It Does

The app scans multiple blockchains using the Nansen CLI, finds tokens where Smart Money wallets are **accumulating while price is falling**, scores them on a Divergence Index, and sends you Telegram alerts automatically — all without writing a single line of code as a user.

1. Pulls **token screener data** across up to 9 chains via Nansen CLI
2. Fetches **Smart Money netflows** (Fund + Smart Trader + 30D Smart Trader labels)
3. Scores each token on a **Divergence Index (0–100)**:
   - Smart Money netflow (positive = accumulating) → up to 40 pts
   - Price momentum (negative price + SM buying = opportunity) → up to 30 pts
   - Smart Money trader count → up to 20 pts
   - Holder concentration (lower = safer) → up to 10 pts
4. Displays a **live ranked dashboard** in the browser
5. Fires **automatic Telegram alerts** to your phone at your chosen interval

---

## Supported Chains

| Label | Chain | Label | Chain |
|-------|-------|-------|-------|
| ETH | Ethereum | BNB | BNB Chain |
| SOL | Solana | ARB | Arbitrum |
| BASE | Base | POL | Polygon |
| OP | Optimism | AVAX | Avalanche |
| LNA | Linea | | |

---

## How It Works — User Flow

There are only **3 things a user needs to do**. The app handles everything else.

### Step 1 — Get Nansen Credits & API Key

Nansen powers all the on-chain data. You need an account and API credits to make calls.

1. Go to **[app.nansen.ai](https://app.nansen.ai)** and sign up
2. Top up your account with credits (pay as you go — no subscription required)
3. Go to **Settings → API Keys** → create a new key and copy it
4. That key is all you need — paste it into the app

> 💡 The more chains and intervals you scan, the more credits you use. Start with ETH + SOL on a 1-hour interval to be efficient.

---

### Step 2 — Set Up Your Telegram Bot (Free, 5 minutes)

Telegram alerts are free. You just need a bot to send the messages.

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` — follow the prompts to name your bot
3. Copy the **bot token** it gives you (looks like `7123456789:AAFxyz...`)
4. Search for your new bot in Telegram and press **Start** (or send any message)
5. Open this URL in your browser — replace `TOKEN` with your actual token:
   ```
   https://api.telegram.org/botTOKEN/getUpdates
   ```
6. Find the number next to `"id"` inside `"chat"` — that is your **Chat ID**

You now have your **Bot Token** and **Chat ID**. Done.

---

### Step 3 — Open the App & Start Scanning

1. Go to the app URL (hosted on Streamlit Cloud — no install needed)
2. In the **sidebar**, fill in:
   - **Nansen API Key** — from Step 1
   - **Telegram Bot Token** — from Step 2
   - **Telegram Chat ID** — from Step 2
3. Choose your **chains** (ETH, SOL, BASE are on by default — toggle more as needed)
4. Set your **minimum score filter** (20 is a good starting point)
5. Pick your **scan interval** (every 1 hour is recommended)
6. Click **▶ Start Auto** — the app begins scanning automatically

That's it. From this point the app runs on its own:
- Scans your selected chains at your chosen interval
- Scores every token on the Divergence Index
- Updates the dashboard with the latest results
- Sends a Telegram message to your phone with the top 5 signals after every scan

---

## Credential Options

The app gives you two ways to handle your keys:

| Mode | What It Does | Best For |
|------|-------------|----------|
| **Session only** | Keys disappear when you close the tab | Maximum privacy |
| **Save in browser** | Keys stay in your browser's localStorage | Convenience — no re-entering each visit |

> 🔒 Your keys are **never stored on any server**. They go directly from your browser to the Nansen and Telegram APIs only.

---

## The Economics

| Item | Cost |
|------|------|
| This app | **Free** |
| Streamlit Cloud hosting | **Free** |
| Telegram bot | **Free** |
| Nansen API credits | Pay as you go at app.nansen.ai |

The only thing you ever pay for is Nansen credits.

---

## Running Locally (Developer Setup)

If you want to run this yourself instead of using the hosted version:

### Prerequisites
- Python 3.9+
- Node.js (for Nansen CLI)

### Install

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/smart-money-divergence-detector
cd smart-money-divergence-detector

# Install Python dependencies
pip install -r requirements.txt

# Install Nansen CLI
npm install -g nansen-cli

# Authenticate
nansen login --api-key YOUR_NANSEN_API_KEY
```

### Run the Web App
```bash
streamlit run app.py
```

### Run the Terminal Script (no UI)
```bash
# Fill in your keys in config.py first
python detector.py
```

---

## Nansen CLI Commands Used

| Command | Purpose |
|---------|---------|
| `nansen research token screener --chain X --timeframe 24h` | Smart Money active tokens |
| `nansen research smart-money netflow --chain X` | Net USD flows from SM wallets |

Each full scan across all 9 chains makes **18+ API calls**.

---

## Sample Terminal Output

```
============================================================
  SMART MONEY DIVERGENCE DETECTOR
  Chains: ethereum, solana, base, bnb, arbitrum
  2025-03-16 09:42 UTC
============================================================

Scanning ETHEREUM...
  Token screener [ethereum]...
  Smart money netflow [ethereum]...
  Found 38 screener tokens, 22 netflow entries

Scanning SOLANA...
  Found 45 screener tokens, 31 netflow entries

============================================================
  TOP DIVERGENCE SIGNALS
============================================================
  #   Symbol     Chain      Score   SM Flow      Price 24h    SM Traders
  -------------------------------------------------------------------
  1   TOKEN_A    ethereum   78.5    $2.1M        v-8.3%       14
  2   TOKEN_B    solana     65.0    $890K        v-5.1%        9
  3   TOKEN_C    base       54.5    $420K        v-3.7%        6
============================================================
```

---

## Sample Telegram Alert

```
🧠 Smart Money Divergence Alert
2025-03-16 09:42 UTC

!! 1. TOKEN_A [ethereum]
   Score: 78.5 | Flow: $2.1M | -8.3%

-> 2. TOKEN_B [solana]
   Score: 65.0 | Flow: $890K | -5.1%

-> 3. TOKEN_C [base]
   Score: 54.5 | Flow: $420K | -3.7%

Not financial advice. Built with Nansen CLI
```

---

## Disclaimer

Not financial advice. For educational and research purposes only. Always do your own research before making any investment decisions.

---

*Built for the [#NansenCLI](https://twitter.com/search?q=%23NansenCLI) competition | [@nansen_ai](https://twitter.com/nansen_ai)*
