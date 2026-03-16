"""
Smart Money Divergence Detector — Streamlit Web App
=====================================================
Users enter their own Nansen API key, Telegram Bot Token,
and Telegram Chat ID. Results are shown in a live dashboard.
"""

import streamlit as st
import subprocess
import json
import math
import requests
import time
from datetime import datetime, timezone

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Smart Money Divergence Detector",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Inter:wght@300;400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    h1, h2, h3 {
        font-family: 'Space Mono', monospace !important;
    }
    .main-title {
        font-family: 'Space Mono', monospace;
        font-size: 2rem;
        font-weight: 700;
        color: #00ff88;
        text-shadow: 0 0 30px rgba(0,255,136,0.3);
        margin-bottom: 0;
    }
    .subtitle {
        color: #888;
        font-size: 0.9rem;
        margin-top: 4px;
    }
    .signal-card {
        background: #0d1117;
        border: 1px solid #21262d;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        transition: border-color 0.2s;
    }
    .signal-card:hover {
        border-color: #00ff88;
    }
    .score-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-family: 'Space Mono', monospace;
        font-size: 0.85rem;
        font-weight: 700;
    }
    .score-high   { background: rgba(0,255,136,0.15); color: #00ff88; border: 1px solid #00ff88; }
    .score-medium { background: rgba(255,170,0,0.15); color: #ffaa00; border: 1px solid #ffaa00; }
    .score-low    { background: rgba(100,100,100,0.15); color: #888;   border: 1px solid #444; }
    .chain-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .chain-ethereum { background: #1a1f6e; color: #818cf8; }
    .chain-solana   { background: #1a3a2a; color: #00ff88; }
    .chain-base     { background: #0d2244; color: #60a5fa; }
    .metric-box {
        background: #0d1117;
        border: 1px solid #21262d;
        border-radius: 10px;
        padding: 12px 16px;
        text-align: center;
    }
    .metric-value {
        font-family: 'Space Mono', monospace;
        font-size: 1.6rem;
        font-weight: 700;
        color: #00ff88;
    }
    .metric-label {
        font-size: 0.75rem;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .stButton > button {
        background: #00ff88 !important;
        color: #0d1117 !important;
        font-family: 'Space Mono', monospace !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.6rem 2rem !important;
        font-size: 0.9rem !important;
        transition: all 0.2s !important;
    }
    .stButton > button:hover {
        background: #00cc6e !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 20px rgba(0,255,136,0.3) !important;
    }
    .stTextInput > div > div > input,
    .stSelectbox > div > div {
        background: #0d1117 !important;
        border: 1px solid #21262d !important;
        border-radius: 8px !important;
        color: #e6edf3 !important;
        font-family: 'Space Mono', monospace !important;
        font-size: 0.85rem !important;
    }
    .info-box {
        background: rgba(0,255,136,0.05);
        border: 1px solid rgba(0,255,136,0.2);
        border-radius: 10px;
        padding: 14px 18px;
        font-size: 0.85rem;
        color: #aaa;
        margin-bottom: 16px;
    }
    .stMarkdown hr { border-color: #21262d; }
    div[data-testid="stSidebarNav"] { display: none; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

CHAINS = ["ethereum", "solana", "base"]

def fmt_usd(n):
    try:
        n = float(n or 0)
    except:
        return "N/A"
    if abs(n) >= 1_000_000:
        return f"${n/1_000_000:.1f}M"
    if abs(n) >= 1_000:
        return f"${n/1_000:.1f}K"
    return f"${n:.2f}"

def safe_get(d, *keys, default=0):
    for k in keys:
        v = d.get(k)
        if v is not None:
            return v
    return default

def nansen_call(command: list, api_key: str) -> list | dict:
    """Run a Nansen CLI command authenticated with the given key."""
    full_cmd = ["nansen", "login", "--api-key", api_key]
    subprocess.run(full_cmd, capture_output=True, text=True, timeout=15)

    full_cmd = ["nansen"] + command + ["--format", "json"]
    try:
        result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            return {}
        output = result.stdout.strip()
        if not output:
            return {}
        return json.loads(output)
    except Exception:
        return {}

def fetch_screener(chain: str, api_key: str) -> list:
    data = nansen_call(["research", "token", "screener", "--chain", chain, "--timeframe", "24h"], api_key)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ["tokens", "data", "results", "items"]:
            if k in data:
                return data[k]
    return []

def fetch_netflow(chain: str, api_key: str) -> list:
    data = nansen_call(["research", "smart-money", "netflow", "--chain", chain], api_key)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ["tokens", "data", "results", "items", "flows"]:
            if k in data:
                return data[k]
    return []

def compute_score(token: dict, netflow_map: dict) -> float:
    score = 0.0
    address = safe_get(token, "address", "token_address", "contract", default="")

    nf = netflow_map.get(address, {})
    net_flow = safe_get(nf, "net_flow_usd", "netflow_usd", "net_flow_24h_usd",
                        default=safe_get(token, "smart_money_net_flow_usd", "netflow_usd", default=0)) or 0
    if net_flow > 0:
        score += min(40, max(0, (math.log10(max(net_flow, 1)) - 3) * 13.3))

    price_chg = safe_get(token, "price_change_24h_pct", "price_change_pct",
                         "priceChange24h", default=0) or 0
    if price_chg < 0:
        score += min(30, abs(price_chg) * 1.5)
    elif price_chg < 5:
        score += 5

    sm_traders = safe_get(token, "smart_money_trader_count", "nof_smart_money_traders",
                          "sm_traders", default=0) or 0
    score += min(20, sm_traders * 2)

    top10 = safe_get(token, "top_10_holder_pct", "top10HolderPct", default=50) or 50
    if top10 < 30:
        score += 10
    elif top10 < 50:
        score += 5

    return round(score, 1)

def send_telegram(bot_token: str, chat_id: str, message: str) -> bool:
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        r = requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}, timeout=10)
        return r.status_code == 200
    except:
        return False

def score_class(score):
    if score >= 55:
        return "score-high"
    elif score >= 30:
        return "score-medium"
    return "score-low"

def chain_class(chain):
    return f"chain-{chain.lower()}"

# ─────────────────────────────────────────────
# SIDEBAR — CREDENTIALS
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown('<p class="main-title">🧠 SM Detector</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Smart Money Divergence</p>', unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("### ⚙️ Your Credentials")
    st.markdown("""
    <div class="info-box">
    Your keys are used only for this session and are never stored or shared.
    </div>
    """, unsafe_allow_html=True)

    nansen_key = st.text_input(
        "Nansen API Key",
        type="password",
        placeholder="Paste your Nansen API key...",
        help="Get yours at app.nansen.ai → Settings → API"
    )

    st.markdown("---")
    st.markdown("### 📬 Telegram Alerts *(optional)*")

    tg_token = st.text_input(
        "Telegram Bot Token",
        type="password",
        placeholder="1234567890:AAF...",
        help="Get from @BotFather on Telegram"
    )

    tg_chat_id = st.text_input(
        "Telegram Chat ID",
        placeholder="123456789",
        help="Visit api.telegram.org/bot<TOKEN>/getUpdates after messaging your bot"
    )

    st.markdown("---")
    st.markdown("### 🔗 Chains")
    selected_chains = []
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.checkbox("ETH", value=True):
            selected_chains.append("ethereum")
    with col2:
        if st.checkbox("SOL", value=True):
            selected_chains.append("solana")
    with col3:
        if st.checkbox("BASE", value=True):
            selected_chains.append("base")

    st.markdown("---")
    st.markdown("### 🎚️ Min Score Filter")
    min_score = st.slider("Show tokens scoring above:", 0, 80, 20)

    st.markdown("---")
    st.markdown(
        '<p style="font-size:0.7rem;color:#555;text-align:center">'
        'Built with Nansen CLI · #NansenCLI</p>',
        unsafe_allow_html=True
    )

# ─────────────────────────────────────────────
# MAIN CONTENT
# ─────────────────────────────────────────────

st.markdown('<h1 class="main-title">Smart Money Divergence Detector</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="subtitle">Find tokens where Smart Money accumulates while retail is fearful — '
    'across Ethereum, Solana & Base.</p>',
    unsafe_allow_html=True
)
st.markdown("---")

# Run button
col_btn, col_ts = st.columns([2, 3])
with col_btn:
    run_clicked = st.button("🔍 Run Scan Now")
with col_ts:
    if "last_run" in st.session_state:
        st.markdown(
            f'<p style="color:#555;font-size:0.8rem;padding-top:12px">Last run: {st.session_state.last_run}</p>',
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

    all_tokens = []
    netflow_map = {}

    progress = st.progress(0, text="Starting scan...")
    steps = len(selected_chains) * 2
    step = 0

    for chain in selected_chains:
        progress.progress(step / steps, text=f"📡 Fetching token screener [{chain}]...")
        screener = fetch_screener(chain, nansen_key)
        step += 1

        progress.progress(step / steps, text=f"📡 Fetching SM netflow [{chain}]...")
        netflow = fetch_netflow(chain, nansen_key)
        step += 1

        for nf in netflow:
            addr = safe_get(nf, "token_address", "address", "contract", default="")
            if addr:
                netflow_map[addr] = nf

        for t in screener:
            t["_chain"] = chain
            all_tokens.append(t)

    progress.progress(1.0, text="✅ Scan complete!")
    time.sleep(0.5)
    progress.empty()

    # Score and filter
    for t in all_tokens:
        t["_score"] = compute_score(t, netflow_map)

    results = [t for t in all_tokens if t["_score"] >= min_score]
    results.sort(key=lambda x: x["_score"], reverse=True)

    st.session_state.results = results
    st.session_state.last_run = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Send Telegram if configured
    if tg_token and tg_chat_id and results:
        top5 = results[:5]
        lines = [f"*Smart Money Divergence Alert*\n_{st.session_state.last_run}_\n"]
        for i, t in enumerate(top5, 1):
            sym = safe_get(t, "symbol", "name", default="???")
            chain = t.get("_chain", "")
            score = t["_score"]
            flow = fmt_usd(safe_get(t, "smart_money_net_flow_usd", "netflow_usd", default=0))
            pc = safe_get(t, "price_change_24h_pct", "price_change_pct", default=0) or 0
            lines.append(f"{'!!' if score >= 55 else '->'} *{i}. {sym}* [{chain}]\nScore: `{score}` | Flow: `{flow}` | `{pc:+.1f}%`")
        lines.append("\n_Not financial advice. Built with Nansen CLI_")
        ok = send_telegram(tg_token, tg_chat_id, "\n".join(lines))
        if ok:
            st.success("📬 Telegram alert sent!")
        else:
            st.warning("⚠️ Telegram alert failed — check your token and chat ID.")

# ─────────────────────────────────────────────
# DISPLAY RESULTS
# ─────────────────────────────────────────────

if "results" in st.session_state and st.session_state.results:
    results = st.session_state.results

    # Summary metrics
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value">{len(results)}</div>
            <div class="metric-label">Signals found</div>
        </div>""", unsafe_allow_html=True)
    with m2:
        high = len([r for r in results if r["_score"] >= 55])
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value" style="color:#00ff88">{high}</div>
            <div class="metric-label">High conviction</div>
        </div>""", unsafe_allow_html=True)
    with m3:
        top_score = results[0]["_score"] if results else 0
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value">{top_score}</div>
            <div class="metric-label">Top score</div>
        </div>""", unsafe_allow_html=True)
    with m4:
        chains_hit = len(set(r["_chain"] for r in results))
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value">{chains_hit}</div>
            <div class="metric-label">Chains active</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📊 Top Divergence Signals")

    for i, token in enumerate(results[:20], 1):
        sym       = str(safe_get(token, "symbol", "name", default="???"))
        chain     = token.get("_chain", "")
        score     = token["_score"]
        flow      = fmt_usd(safe_get(token, "smart_money_net_flow_usd", "netflow_usd", default=0))
        price_chg = safe_get(token, "price_change_24h_pct", "price_change_pct", default=0) or 0
        traders   = safe_get(token, "smart_money_trader_count", "nof_smart_money_traders", "sm_traders", default=0) or 0
        arrow     = "▼" if price_chg < 0 else "▲"
        color     = "#ff4444" if price_chg < 0 else "#00ff88"
        sc        = score_class(score)
        cc        = chain_class(chain)

        st.markdown(f"""
        <div class="signal-card">
            <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px">
                <div style="display:flex;align-items:center;gap:10px">
                    <span style="font-family:'Space Mono',monospace;color:#555;font-size:0.85rem">#{i:02d}</span>
                    <span style="font-family:'Space Mono',monospace;font-weight:700;font-size:1.1rem;color:#e6edf3">{sym}</span>
                    <span class="chain-badge {cc}">{chain}</span>
                </div>
                <span class="score-badge {sc}">{score} pts</span>
            </div>
            <div style="display:flex;gap:24px;margin-top:10px;flex-wrap:wrap">
                <div>
                    <div style="font-size:0.7rem;color:#555;text-transform:uppercase;letter-spacing:.07em">SM Netflow</div>
                    <div style="font-family:'Space Mono',monospace;font-size:0.95rem;color:#e6edf3">{flow}</div>
                </div>
                <div>
                    <div style="font-size:0.7rem;color:#555;text-transform:uppercase;letter-spacing:.07em">Price 24h</div>
                    <div style="font-family:'Space Mono',monospace;font-size:0.95rem;color:{color}">{arrow} {abs(price_chg):.1f}%</div>
                </div>
                <div>
                    <div style="font-size:0.7rem;color:#555;text-transform:uppercase;letter-spacing:.07em">SM Traders</div>
                    <div style="font-family:'Space Mono',monospace;font-size:0.95rem;color:#e6edf3">{traders}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

elif "results" in st.session_state and not st.session_state.results:
    st.info("No tokens matched the current score filter. Try lowering the minimum score.")

else:
    # Empty state
    st.markdown("""
    <div style="text-align:center;padding:60px 20px;color:#444">
        <div style="font-size:3rem">🧠</div>
        <div style="font-family:'Space Mono',monospace;font-size:1.1rem;color:#555;margin-top:12px">
            Enter your credentials in the sidebar<br>and hit <span style="color:#00ff88">Run Scan Now</span>
        </div>
        <div style="font-size:0.8rem;margin-top:16px;color:#333">
            Scans ETH · SOL · BASE for Smart Money divergence signals
        </div>
    </div>
    """, unsafe_allow_html=True)

    # How it works
    st.markdown("---")
    st.markdown("### How the Divergence Score Works")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("""
        <div class="metric-box">
            <div class="metric-value">40</div>
            <div class="metric-label">pts — SM Netflow</div>
            <div style="font-size:0.75rem;color:#555;margin-top:8px">Positive = Smart Money accumulating</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="metric-box">
            <div class="metric-value">30</div>
            <div class="metric-label">pts — Price drop</div>
            <div style="font-size:0.75rem;color:#555;margin-top:8px">Retail fear while SM buys = signal</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="metric-box">
            <div class="metric-value">20</div>
            <div class="metric-label">pts — SM traders</div>
            <div style="font-size:0.75rem;color:#555;margin-top:8px">More unique SM wallets = stronger</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown("""
        <div class="metric-box">
            <div class="metric-value">10</div>
            <div class="metric-label">pts — Distribution</div>
            <div style="font-size:0.75rem;color:#555;margin-top:8px">Low whale concentration = safer</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="margin-top:16px;padding:12px 16px;background:rgba(255,60,60,0.05);
        border:1px solid rgba(255,60,60,0.15);border-radius:8px;
        font-size:0.78rem;color:#666">
    ⚠️ Not financial advice. For research and educational purposes only.
    </div>
    """, unsafe_allow_html=True)
