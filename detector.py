#!/usr/bin/env python3
"""
Smart Money Divergence Detector
================================
Uses the Nansen CLI to find tokens where Smart Money is accumulating
while retail sentiment (price momentum) is negative.

Chains: Ethereum, Solana, Base
Alerts: Telegram

CLI Commands Used:
  nansen research token screener --chain <chain> --timeframe 24h
  nansen research smart-money netflow --chain <chain>
"""

import subprocess
import json
import sys
import math
import requests
from datetime import datetime, timezone
from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    TOP_N_RESULTS,
    MIN_SMART_MONEY_TRADERS,
    CHAINS,
)

# ─────────────────────────────────────────────
# 1. NANSEN CLI WRAPPER
# ─────────────────────────────────────────────

def nansen(command: list[str]) -> dict | list:
    """Run a Nansen CLI command and return parsed JSON."""
    full_cmd = ["nansen"] + command + ["--format", "json"]
    try:
        result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            err = result.stderr.strip() or result.stdout.strip()
            print(f"  [warn] CLI error: {err[:120]}")
            return {}
        output = result.stdout.strip()
        if not output:
            return {}
        return json.loads(output)
    except subprocess.TimeoutExpired:
        print(f"  [warn] CLI timed out: {' '.join(command)}")
        return {}
    except json.JSONDecodeError as e:
        # Try to return raw stdout for debugging
        print(f"  [warn] JSON parse error: {e}")
        return {}


# ─────────────────────────────────────────────
# 2. DATA FETCHING
# ─────────────────────────────────────────────

def fetch_token_screener(chain: str) -> list[dict]:
    """Token screener per chain - Smart Money active tokens."""
    print(f"  📡 Token screener [{chain}]...")
    data = nansen([
        "research", "token", "screener",
        "--chain", chain,
        "--timeframe", "24h",
    ])
    # Handle both list and dict responses
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # Try common keys
        for key in ["tokens", "data", "results", "items"]:
            if key in data:
                return data[key]
    return []


def fetch_smart_money_netflow(chain: str) -> list[dict]:
    """Smart money netflow per chain."""
    print(f"  📡 Smart money netflow [{chain}]...")
    data = nansen([
        "research", "smart-money", "netflow",
        "--chain", chain,
    ])
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ["tokens", "data", "results", "items", "flows"]:
            if key in data:
                return data[key]
    return []


# ─────────────────────────────────────────────
# 3. DIVERGENCE SCORING ENGINE
# ─────────────────────────────────────────────

def safe_get(d: dict, *keys, default=0):
    """Try multiple key names, return first match."""
    for k in keys:
        val = d.get(k)
        if val is not None:
            return val
    return default


def compute_divergence_score(token: dict, netflow_map: dict) -> float:
    """
    Divergence Index (0-100):
      40pts  Smart Money net flow (positive = accumulating)
      30pts  Price momentum (negative price = retail fear = opportunity)
      20pts  Smart Money trader count
      10pts  Holder concentration (lower = safer)
    """
    score = 0.0

    address = safe_get(token, "address", "token_address", "contract", default="")

    # --- Smart Money Netflow (40 pts) ---
    nf = netflow_map.get(address, {})
    net_flow_usd = safe_get(nf, "net_flow_usd", "netflow_usd", "net_flow_24h_usd",
                            default=safe_get(token, "smart_money_net_flow_usd",
                                            "netflow_usd", "net_flow_usd", default=0))
    net_flow_usd = net_flow_usd or 0
    if net_flow_usd > 0:
        flow_score = min(40, max(0, (math.log10(max(net_flow_usd, 1)) - 3) * 13.3))
        score += flow_score

    # --- Price Momentum (30 pts) ---
    price_change = safe_get(token, "price_change_24h_pct", "price_change_pct",
                            "price_change_percentage_24h", "priceChange24h", default=0)
    price_change = price_change or 0
    if price_change < 0:
        momentum_score = min(30, abs(price_change) * 1.5)
        score += momentum_score
    elif price_change < 5:
        score += 5

    # --- Smart Money Trader Count (20 pts) ---
    sm_traders = safe_get(token, "smart_money_trader_count", "nof_smart_money_traders",
                          "smartMoneyTraders", "sm_traders", default=0)
    sm_traders = sm_traders or 0
    if sm_traders >= MIN_SMART_MONEY_TRADERS:
        trader_score = min(20, sm_traders * 2)
        score += trader_score

    # --- Holder Concentration (10 pts) ---
    top10_pct = safe_get(token, "top_10_holder_pct", "top10HolderPct",
                         "top_10_holders_percent", default=50)
    top10_pct = top10_pct or 50
    if top10_pct < 30:
        score += 10
    elif top10_pct < 50:
        score += 5

    return round(score, 1)


# ─────────────────────────────────────────────
# 4. MAIN PIPELINE
# ─────────────────────────────────────────────

def run_detector():
    print("\n" + "=" * 60)
    print("  SMART MONEY DIVERGENCE DETECTOR")
    print(f"  Chains: {', '.join(CHAINS)}")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60 + "\n")

    all_tokens = []
    netflow_map = {}

    for chain in CHAINS:
        print(f"Scanning {chain.upper()}...")

        screener_tokens = fetch_token_screener(chain)
        netflow_tokens  = fetch_smart_money_netflow(chain)

        # Build netflow lookup by token address
        for nf in netflow_tokens:
            addr = safe_get(nf, "token_address", "address", "contract", default="")
            if addr:
                netflow_map[addr] = nf

        for t in screener_tokens:
            t["_chain"] = chain
            all_tokens.append(t)

        print(f"  Found {len(screener_tokens)} screener tokens, "
              f"{len(netflow_tokens)} netflow entries\n")

    if not all_tokens:
        print("No tokens returned.")
        print("-> Check credits at app.nansen.ai and make sure CLI is authenticated.")
        sys.exit(1)

    # Score every token
    print("Computing Divergence Index scores...\n")
    scored = []
    for token in all_tokens:
        score = compute_divergence_score(token, netflow_map)
        token["divergence_score"] = score
        scored.append(token)

    # Sort and take top N
    scored.sort(key=lambda x: x["divergence_score"], reverse=True)
    top_tokens = scored[:TOP_N_RESULTS]

    return top_tokens


# ─────────────────────────────────────────────
# 5. OUTPUT FORMATTING
# ─────────────────────────────────────────────

def fmt(n):
    if n is None:
        return "N/A"
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "N/A"
    if abs(n) >= 1_000_000:
        return f"${n/1_000_000:.1f}M"
    if abs(n) >= 1_000:
        return f"${n/1_000:.1f}K"
    return f"${n:.2f}"


def print_report(tokens: list[dict]):
    print("\n" + "=" * 65)
    print("  TOP DIVERGENCE SIGNALS")
    print("=" * 65)
    print(f"  {'#':<3} {'Symbol':<10} {'Chain':<8} {'Score':<7} "
          f"{'SM Flow':<12} {'Price 24h':<12} {'SM Traders'}")
    print("  " + "-" * 61)

    for i, t in enumerate(tokens, 1):
        symbol    = str(safe_get(t, "symbol", "name", default="???"))[:9]
        chain     = t.get("_chain", "")[:7]
        score     = t.get("divergence_score", 0)
        flow      = fmt(safe_get(t, "smart_money_net_flow_usd", "netflow_usd",
                                 "net_flow_usd", default=0))
        price_chg = safe_get(t, "price_change_24h_pct", "price_change_pct",
                              "priceChange24h", default=0) or 0
        traders   = safe_get(t, "smart_money_trader_count", "nof_smart_money_traders",
                              "sm_traders", default=0) or 0
        arrow     = "v" if price_chg < 0 else "^"
        print(f"  {i:<3} {symbol:<10} {chain:<8} {score:<7} "
              f"{flow:<12} {arrow}{price_chg:+.1f}%{'':<5} {traders}")

    print("=" * 65 + "\n")


def build_markdown_report(tokens: list[dict]) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Smart Money Divergence Report",
        f"*Generated: {ts}*\n",
        "## Top Signals\n",
        "| # | Token | Chain | Score | SM Netflow | Price 24h | SM Traders |",
        "|---|-------|-------|-------|------------|-----------|------------|",
    ]
    for i, t in enumerate(tokens, 1):
        symbol    = str(safe_get(t, "symbol", "name", default="???"))
        chain     = t.get("_chain", "")
        score     = t.get("divergence_score", 0)
        flow      = fmt(safe_get(t, "smart_money_net_flow_usd", "netflow_usd", default=0))
        price_chg = safe_get(t, "price_change_24h_pct", "price_change_pct", default=0) or 0
        traders   = safe_get(t, "smart_money_trader_count", "nof_smart_money_traders",
                              "sm_traders", default=0) or 0
        lines.append(f"| {i} | **{symbol}** | {chain} | {score} | "
                     f"{flow} | {price_chg:+.1f}% | {traders} |")

    lines += [
        "\n## How to Read This",
        "- **Score**: 0-100. Higher = stronger divergence signal.",
        "- **SM Netflow**: Net USD Smart Money flow in 24h (positive = buying).",
        "- **Price 24h**: Negative + high SM flow = opportunity signal.",
        "- **SM Traders**: Distinct Smart Money wallets active in this token.",
        "\n> Not financial advice. For research use only.",
    ]
    return "\n".join(lines)


def save_report(tokens: list[dict]):
    md = build_markdown_report(tokens)
    filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    with open(filename, "w") as f:
        f.write(md)
    print(f"Report saved: {filename}")
    return filename, md


# ─────────────────────────────────────────────
# 6. TELEGRAM ALERTS
# ─────────────────────────────────────────────

def send_telegram(message: str):
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("Telegram not configured - skipping alert.")
        return
    if not TELEGRAM_CHAT_ID or TELEGRAM_CHAT_ID == "YOUR_TELEGRAM_CHAT_ID_HERE":
        print("Telegram Chat ID not set - skipping alert.")
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
            print("Telegram alert sent!")
        else:
            print(f"Telegram error {r.status_code}: {r.text[:100]}")
    except Exception as e:
        print(f"Telegram failed: {e}")


def build_telegram_message(tokens: list[dict]) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "*Smart Money Divergence Alert*",
        f"_{ts}_\n",
        f"Top {len(tokens)} signals across {', '.join(CHAINS)}:\n",
    ]
    for i, t in enumerate(tokens, 1):
        symbol    = str(safe_get(t, "symbol", "name", default="???"))
        chain     = t.get("_chain", "")
        score     = t.get("divergence_score", 0)
        flow      = fmt(safe_get(t, "smart_money_net_flow_usd", "netflow_usd", default=0))
        price_chg = safe_get(t, "price_change_24h_pct", "price_change_pct", default=0) or 0
        emoji     = "!!" if score >= 50 else "->"
        lines.append(
            f"{emoji} *{i}. {symbol}* [{chain}]\n"
            f"   Score: `{score}` | Flow: `{flow}` | `{price_chg:+.1f}%`"
        )
    lines.append("\n_Not financial advice. Built with Nansen CLI_")
    return "\n".join(lines)


# ─────────────────────────────────────────────
# 7. ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    top_tokens = run_detector()
    print_report(top_tokens)
    save_report(top_tokens)
    tg_msg = build_telegram_message(top_tokens)
    send_telegram(tg_msg)
    print("Done! Screenshot the output table and post on X with #NansenCLI @nansen_ai\n")