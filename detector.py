#!/usr/bin/env python3
"""
Smart Money Divergence Detector
================================
Uses the Nansen CLI to find tokens where Smart Money is accumulating
while retail sentiment (price momentum) is negative — a classic alpha signal.

Chains: Ethereum, Solana, Base
Alerts: Telegram
"""

import subprocess
import json
import sys
import math
import requests
from datetime import datetime, timezone
from config import (
    NANSEN_API_KEY,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    TOP_N_RESULTS,
    MIN_MARKET_CAP_USD,
    MIN_SMART_MONEY_TRADERS,
    CHAINS,
)

# ─────────────────────────────────────────────
# 1. NANSEN CLI WRAPPER
# ─────────────────────────────────────────────

def nansen(command: list[str]) -> dict | list:
    """Run a Nansen CLI command and return parsed JSON."""
    full_cmd = ["nansen"] + command + ["--api-key", NANSEN_API_KEY, "--output", "json"]
    try:
        result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"  [warn] CLI error: {result.stderr.strip()}")
            return {}
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        print(f"  [warn] CLI call failed: {e}")
        return {}


# ─────────────────────────────────────────────
# 2. DATA FETCHING (each = 1 API call)
# ─────────────────────────────────────────────

def fetch_token_screener(chain: str) -> list[dict]:
    """API call 1-3: Token screener per chain — Smart Money only."""
    print(f"  📡 Token screener [{chain}]...")
    data = nansen([
        "token", "screener",
        "--chains", chain,
        "--timeframe", "24h",
        "--only-smart-money",
        "--min-market-cap", str(MIN_MARKET_CAP_USD),
        "--per-page", "50",
    ])
    return data.get("tokens", data) if isinstance(data, dict) else (data or [])


def fetch_smart_money_netflow(chain: str) -> list[dict]:
    """API call 4-6: Smart money netflow per chain."""
    print(f"  📡 Smart money netflow [{chain}]...")
    data = nansen([
        "smart-money", "netflow",
        "--chains", chain,
        "--timeframe", "24h",
        "--include-labels", "Fund,Smart Trader,30D Smart Trader",
        "--min-trader-count", str(MIN_SMART_MONEY_TRADERS),
        "--per-page", "50",
    ])
    return data.get("tokens", data) if isinstance(data, dict) else (data or [])


def fetch_token_holders(token_address: str, chain: str) -> dict:
    """API call 7+: Token holder distribution for a specific token."""
    print(f"  📡 Holders [{chain}:{token_address[:8]}...]")
    data = nansen([
        "token", "holders",
        "--address", token_address,
        "--chain", chain,
    ])
    return data if isinstance(data, dict) else {}


def fetch_pnl_leaderboard(chain: str) -> list[dict]:
    """API call: PnL leaderboard to gauge retail momentum."""
    print(f"  📡 PnL leaderboard [{chain}]...")
    data = nansen([
        "smart-money", "pnl-leaderboard",
        "--chains", chain,
        "--timeframe", "24h",
        "--per-page", "20",
    ])
    return data.get("wallets", data) if isinstance(data, dict) else (data or [])


def fetch_token_flows(token_address: str, chain: str) -> dict:
    """API call: Detailed flow intelligence for a token."""
    print(f"  📡 Token flows [{chain}:{token_address[:8]}...]")
    data = nansen([
        "token", "flows",
        "--address", token_address,
        "--chain", chain,
        "--timeframe", "24h",
    ])
    return data if isinstance(data, dict) else {}


# ─────────────────────────────────────────────
# 3. DIVERGENCE SCORING ENGINE
# ─────────────────────────────────────────────

def compute_divergence_score(token: dict, netflow_map: dict) -> float:
    """
    Divergence Index (0–100):
      40pts — Smart Money net flow (positive = accumulating)
      30pts — Price momentum (negative = retail fear = opportunity)
      20pts — Smart Money trader count (more = stronger signal)
      10pts — Holder concentration penalty (high whale = risky)
    """
    score = 0.0
    symbol = token.get("symbol", "???")
    address = token.get("address", "")

    # --- Smart Money Netflow (40 pts) ---
    nf = netflow_map.get(address, {})
    net_flow_usd = nf.get("net_flow_24h_usd", token.get("smart_money_net_flow_usd", 0)) or 0
    if net_flow_usd > 0:
        # Log scale: $10k → 10pts, $100k → 20pts, $1M → 30pts, $10M → 40pts
        flow_score = min(40, max(0, (math.log10(max(net_flow_usd, 1)) - 4) * 10))
        score += flow_score

    # --- Price Momentum (30 pts) — negative price = retail fear ---
    price_change = token.get("price_change_24h_pct", token.get("price_change_pct", 0)) or 0
    if price_change < 0:
        # Deeper dip while SM buys = stronger divergence
        momentum_score = min(30, abs(price_change) * 1.5)
        score += momentum_score
    elif price_change < 5:
        score += 5  # Flat price with SM buying = mild signal

    # --- Smart Money Trader Count (20 pts) ---
    sm_traders = token.get("smart_money_trader_count", token.get("nof_smart_money_traders", 0)) or 0
    trader_score = min(20, sm_traders * 2)
    score += trader_score

    # --- Holder Concentration Penalty (10 pts) ---
    top10_pct = token.get("top_10_holder_pct", 50) or 50
    if top10_pct < 30:
        score += 10
    elif top10_pct < 50:
        score += 5
    # else 0 — concentrated = risky, no bonus

    return round(score, 1)


# ─────────────────────────────────────────────
# 4. MAIN PIPELINE
# ─────────────────────────────────────────────

def run_detector():
    print("\n" + "═" * 60)
    print("  🔍 SMART MONEY DIVERGENCE DETECTOR")
    print(f"  Chains: {', '.join(CHAINS)}")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("═" * 60 + "\n")

    all_tokens = []
    netflow_map = {}

    for chain in CHAINS:
        print(f"▶ Scanning {chain.upper()}...")

        screener_tokens = fetch_token_screener(chain)
        netflow_tokens = fetch_smart_money_netflow(chain)

        # Build netflow lookup by token address
        for nf in netflow_tokens:
            addr = nf.get("token_address", nf.get("address", ""))
            if addr:
                netflow_map[addr] = nf

        # Tag each token with its chain
        for t in screener_tokens:
            t["_chain"] = chain
            all_tokens.append(t)

        print(f"  ✓ Found {len(screener_tokens)} screener tokens, {len(netflow_tokens)} netflow entries\n")

    if not all_tokens:
        print("⚠️  No tokens returned. Check your API key and CLI installation.")
        sys.exit(1)

    # Score every token
    print("⚙️  Computing Divergence Index scores...\n")
    scored = []
    for token in all_tokens:
        score = compute_divergence_score(token, netflow_map)
        if score > 0:
            token["divergence_score"] = score
            scored.append(token)

    # Sort and take top N
    scored.sort(key=lambda x: x["divergence_score"], reverse=True)
    top_tokens = scored[:TOP_N_RESULTS]

    # Enrich top tokens with flow details (extra API calls for depth)
    print(f"🔬 Enriching top {len(top_tokens)} tokens with flow data...\n")
    for token in top_tokens:
        addr = token.get("address", "")
        chain = token.get("_chain", "ethereum")
        if addr:
            flows = fetch_token_flows(addr, chain)
            token["_flows"] = flows

    return top_tokens


# ─────────────────────────────────────────────
# 5. OUTPUT FORMATTING
# ─────────────────────────────────────────────

def format_number(n):
    if n is None:
        return "N/A"
    if abs(n) >= 1_000_000:
        return f"${n/1_000_000:.1f}M"
    if abs(n) >= 1_000:
        return f"${n/1_000:.1f}K"
    return f"${n:.2f}"


def print_report(tokens: list[dict]):
    print("\n" + "═" * 60)
    print("  📊 TOP DIVERGENCE SIGNALS")
    print("═" * 60)
    print(f"  {'#':<3} {'Symbol':<10} {'Chain':<8} {'Score':<7} {'SM Flow':<12} {'Δ Price':<10} {'SM Traders'}")
    print("  " + "─" * 58)

    for i, t in enumerate(tokens, 1):
        symbol    = t.get("symbol", "???")[:9]
        chain     = t.get("_chain", "")[:7]
        score     = t.get("divergence_score", 0)
        flow      = format_number(t.get("smart_money_net_flow_usd", t.get("net_flow_24h_usd", 0)))
        price_chg = t.get("price_change_24h_pct", t.get("price_change_pct", 0)) or 0
        traders   = t.get("smart_money_trader_count", t.get("nof_smart_money_traders", 0)) or 0
        arrow     = "🔴" if price_chg < 0 else "🟢"
        print(f"  {i:<3} {symbol:<10} {chain:<8} {score:<7} {flow:<12} {arrow}{price_chg:+.1f}%{'':<3} {traders}")

    print("═" * 60 + "\n")


def build_report_markdown(tokens: list[dict]) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# 🧠 Smart Money Divergence Report",
        f"*Generated: {ts}*",
        f"*Chains: {', '.join(CHAINS)} | Min Market Cap: {format_number(MIN_MARKET_CAP_USD)}*\n",
        "## Top Divergence Signals\n",
        "| # | Token | Chain | Score | SM Netflow | Price Δ | SM Traders |",
        "|---|-------|-------|-------|------------|---------|------------|",
    ]
    for i, t in enumerate(tokens, 1):
        symbol    = t.get("symbol", "???")
        chain     = t.get("_chain", "")
        score     = t.get("divergence_score", 0)
        flow      = format_number(t.get("smart_money_net_flow_usd", t.get("net_flow_24h_usd", 0)))
        price_chg = t.get("price_change_24h_pct", t.get("price_change_pct", 0)) or 0
        traders   = t.get("smart_money_trader_count", t.get("nof_smart_money_traders", 0)) or 0
        lines.append(f"| {i} | **{symbol}** | {chain} | {score} | {flow} | {price_chg:+.1f}% | {traders} |")

    lines += [
        "\n## How to Read This",
        "- **Divergence Score**: 0–100. Higher = stronger signal that SM is accumulating while retail fears.",
        "- **SM Netflow**: Net USD flow from Smart Money wallets in last 24h (positive = buying).",
        "- **Price Δ**: 24h price change. Negative + high SM flow = divergence opportunity.",
        "- **SM Traders**: Number of distinct Smart Money wallets active in this token.",
        "\n> ⚠️ Not financial advice. For educational/research use only.",
    ]
    return "\n".join(lines)


def save_report(tokens: list[dict]):
    md = build_report_markdown(tokens)
    filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    with open(filename, "w") as f:
        f.write(md)
    print(f"📄 Report saved: {filename}")
    return filename, md


# ─────────────────────────────────────────────
# 6. TELEGRAM ALERTS
# ─────────────────────────────────────────────

def send_telegram(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️  Telegram not configured — skipping alert.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            print("✅ Telegram alert sent!")
        else:
            print(f"⚠️  Telegram error {r.status_code}: {r.text}")
    except Exception as e:
        print(f"⚠️  Telegram failed: {e}")


def build_telegram_message(tokens: list[dict]) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"🧠 *Smart Money Divergence Alert*",
        f"_{ts}_\n",
        f"Top {len(tokens)} signals across {', '.join(CHAINS)}:\n",
    ]
    for i, t in enumerate(tokens, 1):
        symbol    = t.get("symbol", "???")
        chain     = t.get("_chain", "")
        score     = t.get("divergence_score", 0)
        flow      = format_number(t.get("smart_money_net_flow_usd", t.get("net_flow_24h_usd", 0)))
        price_chg = t.get("price_change_24h_pct", t.get("price_change_pct", 0)) or 0
        emoji     = "🚨" if score >= 50 else "⚡"
        lines.append(
            f"{emoji} *{i}. {symbol}* [{chain}]\n"
            f"   Score: `{score}` | SM Flow: `{flow}` | Δ`{price_chg:+.1f}%`"
        )
    lines.append("\n_Not financial advice. Built with Nansen CLI 🔍_")
    return "\n".join(lines)


# ─────────────────────────────────────────────
# 7. ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    top_tokens = run_detector()
    print_report(top_tokens)
    filename, md = save_report(top_tokens)

    tg_msg = build_telegram_message(top_tokens)
    send_telegram(tg_msg)

    print("\n✅ Done. Share the report screenshot on X with #NansenCLI @nansen_ai\n")
