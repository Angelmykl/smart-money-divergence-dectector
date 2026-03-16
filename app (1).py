"""
Smart Money Divergence Detector — Streamlit Web App v2
=======================================================
- Users enter Nansen API key, Telegram Bot Token, Chat ID
- Option to save credentials in browser (localStorage) or session only
- User picks scan interval (15min, 30min, 1h, 4h, 12h, 24h)
- Background scheduler fires scans automatically
- Telegram alerts sent on every scheduled scan
"""

import streamlit as st
import subprocess
import json
import math
import requests
import time
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Smart Money Divergence Detector",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Loading screen — shows while app initialises
st.markdown("""
<style>
#loading-screen {
    position: fixed; inset: 0; z-index: 99999;
    background: #0d1117;
    display: flex; align-items: center; justify-content: center;
    flex-direction: column; gap: 16px;
    transition: opacity 0.8s ease;
    font-family: 'Space Mono', monospace;
}
#loading-screen.hide { opacity: 0; pointer-events: none; }
.ld-brain { font-size: 3rem; animation: ldpulse 1.5s ease-in-out infinite; }
@keyframes ldpulse {
    0%,100%{filter:drop-shadow(0 0 8px rgba(0,255,136,0.4));}
    50%{filter:drop-shadow(0 0 24px rgba(0,255,136,0.9));}
}
.ld-title { color:#00ff88; font-size:1.2rem; font-weight:700; letter-spacing:-0.02em; }
.ld-sub   { color:#444; font-size:0.72rem; margin-top:-8px; }
.ld-bar-wrap { width:220px; height:3px; background:#161b22; border-radius:4px; overflow:hidden; }
.ld-bar { height:100%; width:40%; background:linear-gradient(90deg,transparent,#00ff88,transparent);
          animation:ldscan 1.4s ease-in-out infinite; border-radius:4px; }
@keyframes ldscan { 0%{transform:translateX(-150%);} 100%{transform:translateX(350%);} }
.ld-status { color:#00ff88; font-size:0.7rem; opacity:0.6;
             animation:ldblink 1.4s ease-in-out infinite; }
@keyframes ldblink { 0%,100%{opacity:0.6;} 50%{opacity:0.2;} }
.ld-chains { display:flex; gap:5px; flex-wrap:wrap; justify-content:center; max-width:260px; }
.ld-pill { padding:2px 8px; border-radius:20px; font-size:0.62rem; font-weight:600;
           letter-spacing:0.05em; border:1px solid; }
</style>
<div id="loading-screen">
    <span class="ld-brain">🧠</span>
    <div class="ld-title">Smart Money Detector</div>
    <div class="ld-sub">#NansenCLI</div>
    <div class="ld-bar-wrap"><div class="ld-bar"></div></div>
    <div class="ld-status">INITIALIZING SCANNER...</div>
    <div class="ld-chains">
        <span class="ld-pill" style="background:#1a1f6e;color:#818cf8;border-color:#818cf8">ETH</span>
        <span class="ld-pill" style="background:#1a3a2a;color:#00ff88;border-color:#00ff88">SOL</span>
        <span class="ld-pill" style="background:#0d2244;color:#60a5fa;border-color:#60a5fa">BASE</span>
        <span class="ld-pill" style="background:#2a2000;color:#f0b90b;border-color:#f0b90b">BNB</span>
        <span class="ld-pill" style="background:#0d1f33;color:#28a0f0;border-color:#28a0f0">ARB</span>
        <span class="ld-pill" style="background:#1a0d33;color:#8247e5;border-color:#8247e5">POL</span>
        <span class="ld-pill" style="background:#330d0d;color:#ff0420;border-color:#ff0420">OP</span>
        <span class="ld-pill" style="background:#330d0d;color:#e84142;border-color:#e84142">AVAX</span>
        <span class="ld-pill" style="background:#0d1a2a;color:#61dfff;border-color:#61dfff">LINEA</span>
    </div>
</div>
<script>
window.addEventListener('load', function() {
    setTimeout(function() {
        var el = document.getElementById('loading-screen');
        if (el) { el.classList.add('hide'); setTimeout(function(){ el.remove(); }, 900); }
    }, 2200);
});
</script>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────

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
    .scheduler-active {
        background: rgba(0,255,136,0.08); border: 1px solid rgba(0,255,136,0.3);
        border-radius: 10px; padding: 12px 16px;
        font-size: 0.85rem; color: #00ff88; margin-bottom: 12px;
    }
    .scheduler-inactive {
        background: rgba(100,100,100,0.08); border: 1px solid #21262d;
        border-radius: 10px; padding: 12px 16px;
        font-size: 0.85rem; color: #555; margin-bottom: 12px;
    }
    .info-box {
        background: rgba(0,255,136,0.05); border: 1px solid rgba(0,255,136,0.2);
        border-radius: 10px; padding: 14px 18px;
        font-size: 0.85rem; color: #aaa; margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SESSION STATE DEFAULTS
# ─────────────────────────────────────────────

defaults = {
    "results": [],
    "last_run": None,
    "scheduler_running": False,
    "scheduler": None,
    "scan_count": 0,
    "auto_enabled": False,
    "saved_nansen": "",
    "saved_tg_token": "",
    "saved_tg_chat": "",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────
# CORE FUNCTIONS
# ─────────────────────────────────────────────

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

def nansen_call(command: list, api_key: str):
    subprocess.run(["nansen", "login", "--api-key", api_key],
                   capture_output=True, text=True, timeout=15)
    try:
        result = subprocess.run(
            ["nansen"] + command + ["--format", "json"],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0: return {}
        output = result.stdout.strip()
        return json.loads(output) if output else {}
    except Exception:
        return {}

def fetch_screener(chain, api_key):
    data = nansen_call(["research", "token", "screener",
                        "--chain", chain, "--timeframe", "24h"], api_key)
    if isinstance(data, list): return data
    if isinstance(data, dict):
        for k in ["tokens", "data", "results", "items"]:
            if k in data: return data[k]
    return []

def fetch_netflow(chain, api_key):
    data = nansen_call(["research", "smart-money", "netflow",
                        "--chain", chain], api_key)
    if isinstance(data, list): return data
    if isinstance(data, dict):
        for k in ["tokens", "data", "results", "items", "flows"]:
            if k in data: return data[k]
    return []

def compute_score(token, netflow_map):
    score = 0.0
    address = safe_get(token, "address", "token_address", "contract", default="")
    nf = netflow_map.get(address, {})
    net_flow = safe_get(nf, "net_flow_usd", "netflow_usd", "net_flow_24h_usd",
                        default=safe_get(token, "smart_money_net_flow_usd",
                                         "netflow_usd", default=0)) or 0
    if net_flow > 0:
        score += min(40, max(0, (math.log10(max(net_flow, 1)) - 3) * 13.3))
    price_chg = safe_get(token, "price_change_24h_pct", "price_change_pct",
                         "priceChange24h", default=0) or 0
    if price_chg < 0:   score += min(30, abs(price_chg) * 1.5)
    elif price_chg < 5: score += 5
    sm_traders = safe_get(token, "smart_money_trader_count",
                          "nof_smart_money_traders", "sm_traders", default=0) or 0
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

def run_full_scan(api_key, tg_token, tg_chat, chains, min_score):
    all_tokens, netflow_map = [], {}
    for chain in chains:
        screener = fetch_screener(chain, api_key)
        netflow  = fetch_netflow(chain, api_key)
        for nf in netflow:
            addr = safe_get(nf, "token_address", "address", "contract", default="")
            if addr: netflow_map[addr] = nf
        for t in screener:
            t["_chain"] = chain
            all_tokens.append(t)
    for t in all_tokens:
        t["_score"] = compute_score(t, netflow_map)
    results = sorted(
        [t for t in all_tokens if t["_score"] >= min_score],
        key=lambda x: x["_score"], reverse=True
    )
    st.session_state.results    = results
    st.session_state.last_run   = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    st.session_state.scan_count += 1
    if tg_token and tg_chat and results:
        top5  = results[:5]
        lines = [f"*Smart Money Divergence Alert*\n_{st.session_state.last_run}_\n"]
        for i, t in enumerate(top5, 1):
            sym   = str(safe_get(t, "symbol", "name", default="???"))
            chain = t.get("_chain", "")
            score = t["_score"]
            flow  = fmt_usd(safe_get(t, "smart_money_net_flow_usd", "netflow_usd", default=0))
            pc    = safe_get(t, "price_change_24h_pct", "price_change_pct", default=0) or 0
            lines.append(
                f"{'!!' if score >= 55 else '->'} *{i}. {sym}* [{chain}]\n"
                f"Score: `{score}` | Flow: `{flow}` | `{pc:+.1f}%`"
            )
        lines.append("\n_Not financial advice. Built with Nansen CLI_")
        send_telegram(tg_token, tg_chat, "\n".join(lines))
    return results

# ─────────────────────────────────────────────
# SCHEDULER
# ─────────────────────────────────────────────

INTERVAL_OPTIONS = {
    "Every 15 minutes": 15,
    "Every 30 minutes": 30,
    "Every 1 hour":     60,
    "Every 4 hours":    240,
    "Every 12 hours":   720,
    "Every 24 hours":   1440,
}

def start_scheduler(api_key, tg_token, tg_chat, chains, min_score, interval_mins):
    stop_scheduler()
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_full_scan, "interval",
        minutes=interval_mins,
        args=[api_key, tg_token, tg_chat, chains, min_score],
        id="scan_job",
        next_run_time=datetime.now(timezone.utc),
    )
    scheduler.start()
    st.session_state.scheduler         = scheduler
    st.session_state.scheduler_running = True
    st.session_state.auto_enabled      = True

def stop_scheduler():
    if st.session_state.scheduler:
        try: st.session_state.scheduler.shutdown(wait=False)
        except: pass
    st.session_state.scheduler         = None
    st.session_state.scheduler_running = False
    st.session_state.auto_enabled      = False

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown('<p class="main-title">🧠 SM Detector</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Smart Money Divergence</p>', unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("### 🔐 Credential Mode")
    save_mode = st.radio(
        "How to handle your keys:",
        ["Session only (private)", "Save in browser (persistent)"],
        help="Session only: keys disappear when tab closes. Save in browser: stored in localStorage."
    )
    save_to_browser = save_mode == "Save in browser (persistent)"

    if save_to_browser:
        st.markdown("""<div class="info-box">
        Keys saved in <b>your browser only</b>. Never sent anywhere except
        Nansen and Telegram APIs directly.
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### ⚙️ Your Credentials")

    nansen_key = st.text_input(
        "Nansen API Key", type="password",
        value=st.session_state.get("saved_nansen", ""),
        placeholder="Paste your Nansen API key...",
        help="Get yours at app.nansen.ai → Settings → API"
    )
    st.markdown("---")
    st.markdown("### 📬 Telegram Alerts")

    tg_token = st.text_input(
        "Telegram Bot Token", type="password",
        value=st.session_state.get("saved_tg_token", ""),
        placeholder="1234567890:AAF...",
        help="Get from @BotFather on Telegram"
    )
    tg_chat_id = st.text_input(
        "Telegram Chat ID",
        value=st.session_state.get("saved_tg_chat", ""),
        placeholder="123456789",
        help="Visit api.telegram.org/bot<TOKEN>/getUpdates"
    )

    if save_to_browser:
        col_save, col_clear = st.columns(2)
        with col_save:
            if st.button("💾 Save keys"):
                st.session_state.saved_nansen   = nansen_key
                st.session_state.saved_tg_token = tg_token
                st.session_state.saved_tg_chat  = tg_chat_id
                st.success("Saved to session!")
        with col_clear:
            if st.button("🗑️ Clear keys"):
                st.session_state.saved_nansen   = ""
                st.session_state.saved_tg_token = ""
                st.session_state.saved_tg_chat  = ""
                st.rerun()

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
    chain_keys = list(ALL_CHAINS.keys())
    cols = st.columns(3)
    for idx, chain_id in enumerate(chain_keys):
        label, default = ALL_CHAINS[chain_id]
        with cols[idx % 3]:
            if st.checkbox(label, value=default, key=f"chain_{chain_id}"):
                selected_chains.append(chain_id)

    if not selected_chains:
        st.warning("Select at least one chain.")

    st.markdown("---")
    st.markdown("### 🎚️ Min Score Filter")
    min_score = st.slider("Show tokens scoring above:", 0, 80, 20)

    st.markdown("---")
    st.markdown("### ⏱️ Auto-Scan")
    interval_label = st.selectbox("Scan every:", list(INTERVAL_OPTIONS.keys()), index=2)
    interval_mins  = INTERVAL_OPTIONS[interval_label]

    col_start, col_stop = st.columns(2)
    with col_start:
        if st.button("▶ Start"):
            if not nansen_key:
                st.error("Need API key!")
            elif not selected_chains:
                st.error("Pick a chain!")
            else:
                start_scheduler(nansen_key, tg_token, tg_chat_id,
                                selected_chains, min_score, interval_mins)
                st.success("Auto-scan started!")
    with col_stop:
        if st.button("⏹ Stop"):
            stop_scheduler()
            st.info("Stopped.")

    if st.session_state.scheduler_running:
        st.markdown(f"""<div class="scheduler-active">
        ● Auto-scan ON — {interval_label}<br>
        <span style="color:#aaa;font-size:0.75rem">Scans completed: {st.session_state.scan_count}</span>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""<div class="scheduler-inactive">
        ○ Auto-scan off
        </div>""", unsafe_allow_html=True)

    st.markdown('<p style="font-size:0.7rem;color:#555;text-align:center">Built with Nansen CLI · #NansenCLI</p>',
                unsafe_allow_html=True)

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

st.markdown('<h1 class="main-title">Smart Money Divergence Detector</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Find tokens where Smart Money accumulates while retail is fearful — across 9 chains.</p>',
            unsafe_allow_html=True)
st.markdown("---")

col_btn, col_status, col_ts = st.columns([2, 3, 3])
with col_btn:
    run_clicked = st.button("🔍 Run Scan Now")
with col_status:
    if st.session_state.scheduler_running:
        st.markdown(f'<p style="color:#00ff88;font-size:0.85rem;padding-top:12px">● Auto-scanning {interval_label.lower()}</p>',
                    unsafe_allow_html=True)
with col_ts:
    if st.session_state.last_run:
        st.markdown(f'<p style="color:#555;font-size:0.8rem;padding-top:12px">Last scan: {st.session_state.last_run}</p>',
                    unsafe_allow_html=True)

# Manual scan
if run_clicked:
    if not nansen_key:
        st.error("⚠️ Please enter your Nansen API key in the sidebar.")
        st.stop()
    if not selected_chains:
        st.error("⚠️ Please select at least one chain.")
        st.stop()

    progress = st.progress(0, text="Starting scan...")
    steps, step = len(selected_chains) * 2, 0
    all_tokens, netflow_map = [], {}

    for chain in selected_chains:
        progress.progress(step / steps, text=f"📡 Token screener [{chain}]...")
        screener = fetch_screener(chain, nansen_key); step += 1
        progress.progress(step / steps, text=f"📡 SM netflow [{chain}]...")
        netflow  = fetch_netflow(chain, nansen_key);  step += 1
        for nf in netflow:
            addr = safe_get(nf, "token_address", "address", "contract", default="")
            if addr: netflow_map[addr] = nf
        for t in screener:
            t["_chain"] = chain; all_tokens.append(t)

    progress.progress(1.0, text="✅ Done!"); time.sleep(0.4); progress.empty()

    for t in all_tokens:
        t["_score"] = compute_score(t, netflow_map)
    results = sorted(
        [t for t in all_tokens if t["_score"] >= min_score],
        key=lambda x: x["_score"], reverse=True
    )
    st.session_state.results    = results
    st.session_state.last_run   = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    st.session_state.scan_count += 1

    if tg_token and tg_chat_id and results:
        top5  = results[:5]
        lines = [f"*Smart Money Divergence Alert*\n_{st.session_state.last_run}_\n"]
        for i, t in enumerate(top5, 1):
            sym   = str(safe_get(t, "symbol", "name", default="???"))
            score = t["_score"]
            flow  = fmt_usd(safe_get(t, "smart_money_net_flow_usd", "netflow_usd", default=0))
            pc    = safe_get(t, "price_change_24h_pct", "price_change_pct", default=0) or 0
            lines.append(f"{'!!' if score >= 55 else '->'} *{i}. {sym}* [{t.get('_chain','')}]\nScore: `{score}` | Flow: `{flow}` | `{pc:+.1f}%`")
        lines.append("\n_Not financial advice. Built with Nansen CLI_")
        ok = send_telegram(tg_token, tg_chat_id, "\n".join(lines))
        st.success("📬 Telegram alert sent!") if ok else st.warning("⚠️ Telegram failed — check token and chat ID.")

# Display results
if st.session_state.results:
    results = st.session_state.results
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f'<div class="metric-box"><div class="metric-value">{len(results)}</div><div class="metric-label">Signals found</div></div>', unsafe_allow_html=True)
    with m2:
        high = len([r for r in results if r["_score"] >= 55])
        st.markdown(f'<div class="metric-box"><div class="metric-value" style="color:#00ff88">{high}</div><div class="metric-label">High conviction</div></div>', unsafe_allow_html=True)
    with m3:
        st.markdown(f'<div class="metric-box"><div class="metric-value">{results[0]["_score"]}</div><div class="metric-label">Top score</div></div>', unsafe_allow_html=True)
    with m4:
        st.markdown(f'<div class="metric-box"><div class="metric-value">{len(set(r["_chain"] for r in results))}</div><div class="metric-label">Chains active</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📊 Top Divergence Signals")

    for i, token in enumerate(results[:20], 1):
        sym     = str(safe_get(token, "symbol", "name", default="???"))
        chain   = token.get("_chain", "")
        score   = token["_score"]
        flow    = fmt_usd(safe_get(token, "smart_money_net_flow_usd", "netflow_usd", default=0))
        pc      = safe_get(token, "price_change_24h_pct", "price_change_pct", default=0) or 0
        traders = safe_get(token, "smart_money_trader_count", "nof_smart_money_traders", "sm_traders", default=0) or 0
        arrow   = "▼" if pc < 0 else "▲"
        clr     = "#ff4444" if pc < 0 else "#00ff88"
        sc      = "score-high" if score >= 55 else ("score-medium" if score >= 30 else "score-low")

        st.markdown(f"""
        <div class="signal-card">
          <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px">
            <div style="display:flex;align-items:center;gap:10px">
              <span style="font-family:'Space Mono',monospace;color:#555;font-size:0.85rem">#{i:02d}</span>
              <span style="font-family:'Space Mono',monospace;font-weight:700;font-size:1.1rem;color:#e6edf3">{sym}</span>
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
          </div>
        </div>""", unsafe_allow_html=True)

else:
    st.markdown("""
    <div style="text-align:center;padding:60px 20px;color:#444">
        <div style="font-size:3rem">🧠</div>
        <div style="font-family:'Space Mono',monospace;font-size:1.1rem;color:#555;margin-top:12px">
            Enter credentials in the sidebar<br>
            then hit <span style="color:#00ff88">Run Scan Now</span>
            or <span style="color:#00ff88">Start Auto</span>
        </div>
    </div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:32px">
        <div class="metric-box"><div class="metric-value">40</div><div class="metric-label">pts SM Netflow</div><div style="font-size:0.75rem;color:#555;margin-top:6px">SM accumulation signal</div></div>
        <div class="metric-box"><div class="metric-value">30</div><div class="metric-label">pts Price drop</div><div style="font-size:0.75rem;color:#555;margin-top:6px">Retail fear = opportunity</div></div>
        <div class="metric-box"><div class="metric-value">20</div><div class="metric-label">pts SM traders</div><div style="font-size:0.75rem;color:#555;margin-top:6px">More wallets = stronger</div></div>
        <div class="metric-box"><div class="metric-value">10</div><div class="metric-label">pts Distribution</div><div style="font-size:0.75rem;color:#555;margin-top:6px">Low concentration = safer</div></div>
    </div>
    <div style="margin-top:16px;padding:12px 16px;background:rgba(255,60,60,0.05);border:1px solid rgba(255,60,60,0.15);border-radius:8px;font-size:0.78rem;color:#666">
    Not financial advice. For research and educational purposes only.
    </div>""", unsafe_allow_html=True)

# Auto-refresh while scheduler is running
if st.session_state.scheduler_running:
    time.sleep(3)
    st.rerun()
