"""
Smart Money Divergence Detector — Streamlit Web App
=====================================================
Calls Nansen REST API directly (no CLI needed).
Supports 9 chains: ETH, SOL, BASE, BNB, ARB, POL, OP, AVAX, LINEA
"""

import streamlit as st
import requests
import json
import math
import time
from datetime import datetime, timezone, timedelta

st.set_page_config(
    page_title="Smart Money Divergence Detector",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Inter:wght@300;400;500;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    h1, h2, h3 { font-family: 'Space Mono', monospace !important; }
    .main-title {
        font-family: 'Space Mono', monospace;
        font-size: 2rem; font-weight: 700;
        color: #00ff88;
        text-shadow: 0 0 30px rgba(0,255,136,0.3);
        margin-bottom: 0;
    }
    .subtitle { color: #888; font-size: 0.9rem; margin-top: 4px; }
    .signal-card {
        background: #0d1117; border: 1px solid #21262d;
        border-radius: 12px; padding: 16px; margin-bottom: 12px;
    }
    .signal-card:hover { border-color: #00ff88; }
    .score-badge {
        display: inline-block; padding: 4px 12px; border-radius: 20px;
        font-family: 'Space Mono', monospace; font-size: 0.85rem; font-weight: 700;
    }
    .score-high   { background: rgba(0,255,136,0.15); color: #00ff88; border: 1px solid #00ff88; }
    .score-medium { background: rgba(255,170,0,0.15);  color: #ffaa00; border: 1px solid #ffaa00; }
    .score-low    { background: rgba(100,100,100,0.15); color: #888;   border: 1px solid #444; }
    .chain-badge {
        display: inline-block; padding: 2px 8px; border-radius: 6px;
        font-size: 0.75rem; font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.05em;
    }
    .chain-ethereum  { background: #1a1f6e; color: #818cf8; }
    .chain-solana    { background: #1a3a2a; color: #00ff88; }
    .chain-base      { background: #0d2244; color: #60a5fa; }
    .chain-bnb       { background: #2a2000; color: #f0b90b; }
    .chain-arbitrum  { background: #0d1f33; color: #28a0f0; }
    .chain-polygon   { background: #1a0d33; color: #8247e5; }
    .chain-optimism  { background: #330d0d; color: #ff0420; }
    .chain-avalanche { background: #330d0d; color: #e84142; }
    .chain-linea     { background: #0d1a2a; color: #61dfff; }
    .metric-box {
        background: #0d1117; border: 1px solid #21262d;
        border-radius: 10px; padding: 12px 16px; text-align: center;
    }
    .metric-value { font-family: 'Space Mono', monospace; font-size: 1.6rem; font-weight: 700; color: #00ff88; }
    .metric-label { font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 0.08em; }
    .stButton > button {
        background: #00ff88 !important; color: #0d1117 !important;
        font-family: 'Space Mono', monospace !important; font-weight: 700 !important;
        border: none !important; border-radius: 8px !important;
        padding: 0.6rem 2rem !important; font-size: 0.9rem !important;
    }
    .stButton > button:hover {
        background: #00cc6e !important;
        box-shadow: 0 4px 20px rgba(0,255,136,0.3) !important;
    }
    .info-box {
        background: rgba(0,255,136,0.05); border: 1px solid rgba(0,255,136,0.2);
        border-radius: 10px; padding: 14px 18px;
        font-size: 0.85rem; color: #aaa; margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

NANSEN_BASE = "https://api.nansen.ai/api/v1"

def fmt_usd(n):
    try:
        n = float(n or 0)
    except:
        return "N/A"
    if abs(n) >= 1_000_000: return f"${n/1_000_000:.1f}M"
    if abs(n) >= 1_000:     return f"${n/1_000:.1f}K"
    return f"${n:.2f}"

def safe_get(d, *keys, default=0):
    for k in keys:
        v = d.get(k)
        if v is not None: return v
    return default

def nansen_post(endpoint: str, api_key: str, payload: dict) -> dict:
    """Make a POST request to Nansen REST API."""
    try:
        r = requests.post(
            f"{NANSEN_BASE}/{endpoint}",
            headers={
                "apiKey": api_key,
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=30
        )
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 403:
            return {"error": "Invalid API key or insufficient credits"}
        elif r.status_code == 429:
            return {"error": "Rate limit reached — wait a moment and try again"}
        else:
            return {"error": f"API error {r.status_code}: {r.text[:100]}"}
    except Exception as e:
        return {"error": str(e)}

def fetch_token_screener(chains: list, api_key: str) -> list:
    """Fetch Smart Money token screener across chains."""
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    payload = {
        "chains": chains,
        "date": {
            "from": yesterday.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "to": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "pagination": {"page": 1, "per_page": 50},
        "filters": {
            "only_smart_money": True,
            "token_age_days": {"max": 365, "min": 1}
        },
        "order_by": [{"field": "chain", "direction": "ASC"}]
    }
    data = nansen_post("token-screener", api_key, payload)
    if "error" in data:
        return [{"_error": data["error"]}]
    # Handle various response shapes
    if isinstance(data, list):
        return data
    for key in ["tokens", "data", "results", "items"]:
        if key in data and isinstance(data[key], list):
            return data[key]
    return []

def fetch_smart_money_flows(chains: list, api_key: str) -> list:
    """Fetch Smart Money netflows across chains."""
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    payload = {
        "chains": chains,
        "date": {
            "from": yesterday.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "to": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "pagination": {"page": 1, "per_page": 50},
        "order_by": [{"field": "net_flow_usd", "direction": "DESC"}]
    }
    data = nansen_post("smart-money/flows", api_key, payload)
    if "error" in data:
        return []
    if isinstance(data, list):
        return data
    for key in ["tokens", "data", "results", "flows", "items"]:
        if key in data and isinstance(data[key], list):
            return data[key]
    return []

def compute_score(token: dict, netflow_map: dict) -> float:
    score = 0.0
    address = safe_get(token, "address", "token_address", "contract", default="")
    nf = netflow_map.get(address, {})
    net_flow = safe_get(nf, "net_flow_usd", "netflow_usd",
                        default=safe_get(token, "smart_money_net_flow_usd",
                                         "netflow_usd", "net_flow_usd", default=0)) or 0
    if net_flow > 0:
        score += min(40, max(0, (math.log10(max(net_flow, 1)) - 3) * 13.3))
    price_chg = safe_get(token, "price_change", "price_change_24h_pct", "price_change_pct", default=0) or 0
    if price_chg < 0:   score += min(30, abs(price_chg) * 1.5)
    elif price_chg < 5: score += 5
    sm_traders = safe_get(token, "nof_traders", "smart_money_trader_count", "sm_traders", default=0) or 0
    score += min(20, sm_traders * 2)
    top10 = safe_get(token, "top_10_holder_pct", "top10HolderPct", default=50) or 50
    if top10 < 30:   score += 10
    elif top10 < 50: score += 5
    return round(score, 1)

def send_telegram(bot_token, chat_id, message):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
            timeout=10
        )
        return r.status_code == 200
    except:
        return False

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown('<p class="main-title">🧠 SM Detector</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Smart Money Divergence</p>', unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("### ⚙️ Your Credentials")
    st.markdown("""<div class="info-box">
    Your keys are used only for this session and are never stored or shared.
    </div>""", unsafe_allow_html=True)

    nansen_key = st.text_input(
        "Nansen API Key", type="password",
        placeholder="Paste your Nansen API key...",
        help="Get yours at app.nansen.ai → Settings → API"
    )

    st.markdown("---")
    st.markdown("### 📬 Telegram Alerts *(optional)*")
    tg_token = st.text_input(
        "Telegram Bot Token", type="password",
        placeholder="1234567890:AAF...",
        help="Get from @BotFather on Telegram"
    )
    tg_chat_id = st.text_input(
        "Telegram Chat ID", placeholder="123456789",
        help="Visit api.telegram.org/bot<TOKEN>/getUpdates"
    )

    st.markdown("---")
    st.markdown("### 🔗 Chains")

    ALL_CHAINS = {
        "ethereum":  ("ETH",  True),
        "solana":    ("SOL",  True),
        "base":      ("BASE", True),
        "bnb":       ("BNB",  False),
        "arbitrum":  ("ARB",  False),
        "polygon":   ("POL",  False),
        "optimism":  ("OP",   False),
        "avalanche": ("AVAX", False),
        "linea":     ("LNA",  False),
    }

    selected_chains = []
    cols = st.columns(3)
    for idx, (chain_id, (label, default)) in enumerate(ALL_CHAINS.items()):
        with cols[idx % 3]:
            if st.checkbox(label, value=default, key=f"chain_{chain_id}"):
                selected_chains.append(chain_id)

    st.markdown("---")
    st.markdown("### 🎚️ Min Score Filter")
    min_score = st.slider("Show tokens scoring above:", 0, 80, 0)

    st.markdown("---")
    st.markdown(
        '<p style="font-size:0.7rem;color:#555;text-align:center">'
        'Built with Nansen API · #NansenCLI</p>',
        unsafe_allow_html=True
    )

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

st.markdown('<h1 class="main-title">Smart Money Divergence Detector</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="subtitle">Find tokens where Smart Money accumulates while retail is fearful '
    '— across 9 chains.</p>', unsafe_allow_html=True
)
st.markdown("---")

col_btn, col_ts = st.columns([2, 4])
with col_btn:
    run_clicked = st.button("🔍 Run Scan Now")
with col_ts:
    if "last_run" in st.session_state and st.session_state.last_run:
        st.markdown(
            f'<p style="color:#555;font-size:0.8rem;padding-top:12px">'
            f'Last scan: {st.session_state.last_run}</p>',
            unsafe_allow_html=True
        )

# ─────────────────────────────────────────────
# RUN SCAN
# ─────────────────────────────────────────────

if run_clicked:
    if not nansen_key:
        st.error("⚠️ Please enter your Nansen API key in the sidebar.")
        st.stop()
    if not selected_chains:
        st.error("⚠️ Please select at least one chain.")
        st.stop()

    progress = st.progress(0, text="Calling Nansen API...")

    # Scan each chain separately to ensure all chains return results
    all_tokens = []
    netflow_map = {}
    steps = len(selected_chains)

    for idx, chain in enumerate(selected_chains):
        pct = 0.1 + (0.8 * idx / steps)
        progress.progress(pct, text=f"📡 Scanning {chain.upper()}...")

        chain_tokens = fetch_token_screener([chain], nansen_key)
        if chain_tokens and "_error" in chain_tokens[0]:
            st.warning(f"⚠️ {chain}: {chain_tokens[0]['_error']}")
            continue

        flow_tokens = fetch_smart_money_flows([chain], nansen_key)
        for nf in flow_tokens:
            addr = safe_get(nf, "token_address", "address", "contract", default="")
            if addr:
                netflow_map[addr] = nf

        for t in chain_tokens:
            t["_chain"] = t.get("chain", chain)
            all_tokens.append(t)

    progress.progress(0.95, text="⚙️ Computing divergence scores...")
    for t in all_tokens:
        t["_score"] = compute_score(t, netflow_map)

    results = sorted(
        [t for t in all_tokens if t["_score"] >= min_score],
        key=lambda x: x["_score"], reverse=True
    )

    progress.progress(1.0, text="✅ Scan complete!")
    time.sleep(0.5)
    progress.empty()

    st.session_state.results    = results
    st.session_state.all_tokens = all_tokens
    st.session_state.last_run   = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Telegram alert
    if tg_token and tg_chat_id and results:
        top5  = results[:5]
        lines = [f"*Smart Money Divergence Alert*\n_{st.session_state.last_run}_\n"]
        for i, t in enumerate(top5, 1):
            sym   = str(safe_get(t, "symbol", "name", default="???"))
            score = t["_score"]
            flow  = fmt_usd(safe_get(t, "smart_money_net_flow_usd", "net_flow_usd", "netflow_usd", default=0))
            pc    = safe_get(t, "price_change_24h_pct", "price_change_pct", default=0) or 0
            chain = t.get("_chain", t.get("chain", ""))
            lines.append(
                f"{'!!' if score >= 55 else '->'} *{i}. {sym}* [{chain}]\n"
                f"Score: `{score}` | Flow: `{flow}` | `{pc:+.1f}%`"
            )
        lines.append("\n_Not financial advice. Built with Nansen API_")
        ok = send_telegram(tg_token, tg_chat_id, "\n".join(lines))
        if ok:  st.success("📬 Telegram alert sent!")
        else:   st.warning("⚠️ Telegram alert failed — check your token and chat ID.")

# ─────────────────────────────────────────────
# DISPLAY RESULTS
# ─────────────────────────────────────────────

if "results" in st.session_state and st.session_state.results:
    results    = st.session_state.results
    all_tokens = st.session_state.get("all_tokens", results)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f'<div class="metric-box"><div class="metric-value">{len(results)}</div><div class="metric-label">Signals found</div></div>', unsafe_allow_html=True)
    with m2:
        high = len([r for r in results if r["_score"] >= 55])
        st.markdown(f'<div class="metric-box"><div class="metric-value" style="color:#00ff88">{high}</div><div class="metric-label">High conviction</div></div>', unsafe_allow_html=True)
    with m3:
        top_score = results[0]["_score"] if results else 0
        st.markdown(f'<div class="metric-box"><div class="metric-value">{top_score}</div><div class="metric-label">Top score</div></div>', unsafe_allow_html=True)
    with m4:
        chains_hit = len(set(r.get("_chain", r.get("chain", "")) for r in results))
        st.markdown(f'<div class="metric-box"><div class="metric-value">{chains_hit}</div><div class="metric-label">Chains active</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    # Show raw token count for debugging
    st.markdown(f"### 📊 Top Divergence Signals *({len(all_tokens)} tokens scanned)*")

    if not results:
        st.info("No tokens scored above the minimum threshold. Try lowering the Min Score Filter to 0.")
    else:
        for i, token in enumerate(results[:20], 1):
                addr    = safe_get(token, 'token_address', 'address', 'contract', default='')
            sym     = str(safe_get(token, "token_symbol", "symbol", "name", default="???"))
            chain   = token.get("_chain", token.get("chain", ""))
            score   = token["_score"]
            flow    = fmt_usd(safe_get(token, "netflow", "smart_money_net_flow_usd", "net_flow_usd", default=0))
            pc      = safe_get(token, "price_change_24h_pct", "price_change_pct", "price_change", default=0) or 0
            traders = safe_get(token, "smart_money_trader_count",
                               "nof_smart_money_traders", "sm_traders",
                               "smart_money_count", default=0) or 0
            arrow   = "▼" if pc < 0 else "▲"
            clr     = "#ff4444" if pc < 0 else "#00ff88"
            sc      = "score-high" if score >= 55 else ("score-medium" if score >= 30 else "score-low")

            addr = safe_get(token, "token_address", "address", "contract", default="")
            dex_url = f"https://dexscreener.com/search?q={addr}" if addr else "#"
            addr_short = addr[:6] + "..." + addr[-4:] if len(addr) > 10 else addr

            st.markdown(f"""
            <div class="signal-card">
              <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px">
                <div style="display:flex;align-items:center;gap:10px">
                  <span style="font-family:'Space Mono',monospace;color:#555;font-size:0.85rem">#{i:02d}</span>
                  <a href="{dex_url}" target="_blank" style="font-family:'Space Mono',monospace;font-weight:700;font-size:1.1rem;color:#00ff88;text-decoration:none">{sym} ↗</a>
                  <span class="chain-badge chain-{chain.lower()}">{chain}</span>
                </div>
                <span class="score-badge {sc}">{score} pts</span>
              </div>
              <div style="display:flex;gap:24px;margin-top:10px;flex-wrap:wrap">
                <div><div style="font-size:0.7rem;color:#555;text-transform:uppercase;letter-spacing:.07em">SM Netflow</div>
                     <div style="font-family:'Space Mono',monospace;font-size:0.95rem;color:#e6edf3">{flow}</div></div>
                <div><div style="font-size:0.7rem;color:#555;text-transform:uppercase;letter-spacing:.07em">Price 24h</div>
                     <div style="font-family:'Space Mono',monospace;font-size:0.95rem;color:{clr}">{arrow} {abs(pc):.1f}%</div></div>
                <div><div style="font-size:0.7rem;color:#555;text-transform:uppercase;letter-spacing:.07em">SM Traders</div>
                     <div style="font-family:'Space Mono',monospace;font-size:0.95rem;color:#e6edf3">{traders}</div></div>
                <div><div style="font-size:0.7rem;color:#555;text-transform:uppercase;letter-spacing:.07em">Contract</div>
                     <a href="{dex_url}" target="_blank" style="font-family:'Space Mono',monospace;font-size:0.8rem;color:#555;text-decoration:none">{addr_short}</a></div>
              </div>
            </div>""", unsafe_allow_html=True)

elif "results" in st.session_state and not st.session_state.results:
    st.info("No tokens matched. Try lowering the Min Score Filter to 0 and scan again.")

else:
    st.markdown("""
    <div style="text-align:center;padding:60px 20px">
        <div style="font-size:3rem">🧠</div>
        <div style="font-family:'Space Mono',monospace;font-size:1.1rem;color:#555;margin-top:12px">
            Enter your credentials in the sidebar<br>
            and hit <span style="color:#00ff88">Run Scan Now</span>
        </div>
    </div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:16px">
        <div class="metric-box"><div class="metric-value">40</div><div class="metric-label">pts SM Netflow</div><div style="font-size:0.75rem;color:#555;margin-top:6px">SM accumulation signal</div></div>
        <div class="metric-box"><div class="metric-value">30</div><div class="metric-label">pts Price drop</div><div style="font-size:0.75rem;color:#555;margin-top:6px">Retail fear = opportunity</div></div>
        <div class="metric-box"><div class="metric-value">20</div><div class="metric-label">pts SM traders</div><div style="font-size:0.75rem;color:#555;margin-top:6px">More wallets = stronger</div></div>
        <div class="metric-box"><div class="metric-value">10</div><div class="metric-label">pts Distribution</div><div style="font-size:0.75rem;color:#555;margin-top:6px">Low concentration = safer</div></div>
    </div>
    <div style="margin-top:16px;padding:12px 16px;background:rgba(255,60,60,0.05);
        border:1px solid rgba(255,60,60,0.15);border-radius:8px;font-size:0.78rem;color:#666">
    Not financial advice. For research and educational purposes only.
    </div>""", unsafe_allow_html=True)