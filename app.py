import streamlit as st
import requests
import math
import time
import threading
from datetime import datetime, timezone, timedelta

st.set_page_config(page_title="Smart Money Divergence Detector", page_icon="🧠", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Inter:wght@300;400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.main-title { font-family: 'Space Mono', monospace; font-size: 2rem; font-weight: 700; color: #00ff88; text-shadow: 0 0 30px rgba(0,255,136,0.3); margin-bottom: 0; }
.subtitle { color: #888; font-size: 0.9rem; margin-top: 4px; }
.signal-card { background: #0d1117; border: 1px solid #21262d; border-radius: 12px; padding: 16px; margin-bottom: 12px; transition: border-color 0.2s; }
.signal-card:hover { border-color: #00ff88; }
.signal-card.new-token { border-color: rgba(0,255,136,0.5); background: rgba(0,255,136,0.03); }
.new-badge { display: inline-block; padding: 1px 7px; border-radius: 10px; font-size: 0.65rem; font-weight: 700; background: rgba(0,255,136,0.2); color: #00ff88; border: 1px solid #00ff88; margin-left: 6px; vertical-align: middle; letter-spacing: 0.05em; }
.score-badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-family: 'Space Mono', monospace; font-size: 0.85rem; font-weight: 700; }
.score-high { background: rgba(0,255,136,0.15); color: #00ff88; border: 1px solid #00ff88; }
.score-medium { background: rgba(255,170,0,0.15); color: #ffaa00; border: 1px solid #ffaa00; }
.score-low { background: rgba(100,100,100,0.15); color: #888; border: 1px solid #444; }
.chain-badge { display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
.chain-ethereum { background: #1a1f6e; color: #818cf8; }
.chain-solana { background: #1a3a2a; color: #00ff88; }
.chain-base { background: #0d2244; color: #60a5fa; }
.chain-bnb { background: #2a2000; color: #f0b90b; }
.chain-arbitrum { background: #0d1f33; color: #28a0f0; }
.chain-polygon { background: #1a0d33; color: #8247e5; }
.chain-optimism { background: #330d0d; color: #ff0420; }
.chain-avalanche { background: #330d0d; color: #e84142; }
.chain-linea { background: #0d1a2a; color: #61dfff; }
.metric-box { background: #0d1117; border: 1px solid #21262d; border-radius: 10px; padding: 12px 16px; text-align: center; }
.metric-value { font-family: 'Space Mono', monospace; font-size: 1.6rem; font-weight: 700; color: #00ff88; }
.metric-label { font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 0.08em; }
.stButton > button { background: #00ff88 !important; color: #0d1117 !important; font-family: 'Space Mono', monospace !important; font-weight: 700 !important; border: none !important; border-radius: 8px !important; padding: 0.6rem 2rem !important; }
.info-box { background: rgba(0,255,136,0.05); border: 1px solid rgba(0,255,136,0.2); border-radius: 10px; padding: 14px 18px; font-size: 0.85rem; color: #aaa; margin-bottom: 16px; }
.scheduler-on { background: rgba(0,255,136,0.08); border: 1px solid rgba(0,255,136,0.3); border-radius: 10px; padding: 10px 14px; font-size: 0.82rem; color: #00ff88; margin-top: 8px; }
.scheduler-off { background: rgba(100,100,100,0.08); border: 1px solid #21262d; border-radius: 10px; padding: 10px 14px; font-size: 0.82rem; color: #555; margin-top: 8px; }
.history-card { background: #0d1117; border: 1px solid #21262d; border-radius: 8px; padding: 10px 14px; margin-bottom: 6px; font-size: 0.78rem; color: #888; }
.watchlist-pill { display: inline-block; background: rgba(96,165,250,0.1); border: 1px solid #60a5fa; color: #60a5fa; border-radius: 20px; padding: 3px 10px; font-size: 0.72rem; font-family: 'Space Mono', monospace; margin: 2px; cursor: pointer; }
.age-badge { display: inline-block; padding: 1px 7px; border-radius: 10px; font-size: 0.65rem; font-weight: 600; background: rgba(255,170,0,0.1); color: #ffaa00; border: 1px solid rgba(255,170,0,0.3); margin-left: 4px; vertical-align: middle; }
</style>
""", unsafe_allow_html=True)

NANSEN_BASE = "https://api.nansen.ai/api/v1"
INTERVAL_OPTIONS = {"Every 15 min": 15, "Every 30 min": 30, "Every 1 hour": 60, "Every 2 hours": 120, "Every 4 hours": 240, "Every 12 hours": 720}

# Session state defaults
for k, v in {
    "results": [], "all_tokens": [], "last_run": None,
    "scan_count": 0, "seen_tokens": set(), "scan_history": [],
    "watchlist": set(), "api_calls_total": 0,
    "scheduler_running": False, "scheduler_thread": None,
    "scheduler_stop": False,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

def fmt_usd(n):
    try:
        n = float(n or 0)
    except:
        return "N/A"
    if abs(n) >= 1_000_000: return f"${n/1_000_000:.1f}M"
    if abs(n) >= 1_000: return f"${n/1_000:.1f}K"
    return f"${n:.2f}"

def safe_get(d, *keys, default=0):
    for k in keys:
        v = d.get(k)
        if v is not None: return v
    return default

def nansen_post(endpoint, api_key, payload):
    try:
        r = requests.post(
            f"{NANSEN_BASE}/{endpoint}",
            headers={"apiKey": api_key, "Content-Type": "application/json"},
            json=payload, timeout=30
        )
        st.session_state.api_calls_total += 1
        if r.status_code == 200: return r.json()
        elif r.status_code == 403: return {"error": "Invalid API key or insufficient credits"}
        elif r.status_code == 429: return {"error": "Rate limit — wait a moment"}
        else: return {"error": f"API error {r.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def fetch_token_screener(chain, api_key):
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    payload = {
        "chains": [chain],
        "date": {"from": yesterday.strftime("%Y-%m-%dT%H:%M:%SZ"), "to": now.strftime("%Y-%m-%dT%H:%M:%SZ")},
        "pagination": {"page": 1, "per_page": 50},
        "filters": {"only_smart_money": True, "token_age_days": {"max": 365, "min": 1}},
        "order_by": [{"field": "chain", "direction": "ASC"}]
    }
    data = nansen_post("token-screener", api_key, payload)
    if isinstance(data, dict) and "error" in data: return [{"_error": data["error"]}]
    if isinstance(data, list): return data
    for key in ["tokens", "data", "results", "items"]:
        if key in data and isinstance(data[key], list): return data[key]
    return []

def fetch_smart_money_flows(chains, api_key):
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    payload = {
        "chains": chains,
        "date": {"from": yesterday.strftime("%Y-%m-%dT%H:%M:%SZ"), "to": now.strftime("%Y-%m-%dT%H:%M:%SZ")},
        "pagination": {"page": 1, "per_page": 50},
        "order_by": [{"field": "chain", "direction": "ASC"}]
    }
    data = nansen_post("smart-money/flows", api_key, payload)
    if isinstance(data, dict) and "error" in data: return []
    if isinstance(data, list): return data
    for key in ["tokens", "data", "results", "flows", "items"]:
        if key in data and isinstance(data[key], list): return data[key]
    return []

def compute_score(token, netflow_map):
    score = 0.0
    address = safe_get(token, "token_address", "address", "contract", default="")
    nf = netflow_map.get(address, {})
    net_flow = safe_get(nf, "net_flow_usd", "netflow_usd", default=safe_get(token, "netflow", "smart_money_net_flow_usd", default=0)) or 0
    if net_flow > 0: score += min(40, max(0, (math.log10(max(net_flow, 1)) - 3) * 13.3))
    price_chg = safe_get(token, "price_change", "price_change_24h_pct", "price_change_pct", default=0) or 0
    if price_chg < 0: score += min(30, abs(price_chg) * 1.5)
    elif price_chg < 5: score += 5
    sm_traders = safe_get(token, "nof_traders", "smart_money_trader_count", "sm_traders", default=0) or 0
    score += min(20, sm_traders * 2)
    top10 = safe_get(token, "top_10_holder_pct", "top10HolderPct", default=50) or 50
    if top10 < 30: score += 10
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

def run_scan(api_key, tg_token, tg_chat, chains, min_score, new_only=False):
    screener_tokens = []
    for chain in chains:
        tokens = fetch_token_screener(chain, api_key)
        if tokens and isinstance(tokens[0], dict) and "_error" in tokens[0]:
            return False, tokens[0]["_error"]
        for t in tokens:
            t["_chain"] = chain
        screener_tokens.extend(tokens)

    flow_tokens = fetch_smart_money_flows(chains, api_key)
    netflow_map = {}
    for nf in flow_tokens:
        addr = safe_get(nf, "token_address", "address", "contract", default="")
        if addr: netflow_map[addr] = nf

    all_tokens = []
    for t in screener_tokens:
        if "_chain" not in t:
            t["_chain"] = t.get("chain", chains[0])
        t["_score"] = compute_score(t, netflow_map)
        addr = safe_get(t, "token_address", "address", "contract", default="")
        t["_is_new"] = addr not in st.session_state.seen_tokens
        all_tokens.append(t)

    # Update seen tokens
    for t in all_tokens:
        addr = safe_get(t, "token_address", "address", "contract", default="")
        if addr: st.session_state.seen_tokens.add(addr)

    results = sorted(
        [t for t in all_tokens if t["_score"] >= min_score and (not new_only or t["_is_new"])],
        key=lambda x: x["_score"], reverse=True
    )

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    new_count = len([t for t in results if t["_is_new"]])

    # Save to history
    st.session_state.scan_history.insert(0, {
        "ts": ts, "total": len(all_tokens),
        "signals": len(results), "new": new_count,
        "chains": chains
    })
    st.session_state.scan_history = st.session_state.scan_history[:5]

    st.session_state.results = results
    st.session_state.all_tokens = all_tokens
    st.session_state.last_run = ts
    st.session_state.scan_count += 1

    # Telegram
    if tg_token and tg_chat and results:
        top5 = results[:5]
        new_label = f" ({new_count} NEW)" if new_count else ""
        lines = [f"*Smart Money Divergence Alert{new_label}*\n_{ts}_\n"]
        for i, t in enumerate(top5, 1):
            sym = str(safe_get(t, "token_symbol", "symbol", "name", default="???"))
            score = t["_score"]
            flow = fmt_usd(safe_get(t, "netflow", "smart_money_net_flow_usd", default=0))
            pc = safe_get(t, "price_change", "price_change_24h_pct", default=0) or 0
            chain = t.get("_chain", "")
            new_tag = " 🆕" if t.get("_is_new") else ""
            lines.append(f"{'!!' if score >= 55 else '->'} *{i}. {sym}*{new_tag} [{chain}]\nScore: `{score}` | Flow: `{flow}` | `{pc:+.1f}%`")
        lines.append("\n_Not financial advice. Built with Nansen API_")
        send_telegram(tg_token, tg_chat, "\n".join(lines))

    return True, None

def scheduler_loop(api_key, tg_token, tg_chat, chains, min_score, new_only, interval_mins):
    while not st.session_state.scheduler_stop:
        run_scan(api_key, tg_token, tg_chat, chains, min_score, new_only)
        for _ in range(interval_mins * 60):
            if st.session_state.scheduler_stop:
                break
            time.sleep(1)

# ─── SIDEBAR ───────────────────────────────────────────

with st.sidebar:
    st.markdown('<p class="main-title">🧠 SM Detector</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Smart Money Divergence</p>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### ⚙️ Credentials")
    st.markdown('<div class="info-box">Keys used this session only — never stored.</div>', unsafe_allow_html=True)
    nansen_key = st.text_input("Nansen API Key", type="password", placeholder="Paste your Nansen API key...")
    st.markdown("---")
    st.markdown("### 📬 Telegram Alerts *(optional)*")
    tg_token = st.text_input("Bot Token", type="password", placeholder="1234567890:AAF...")
    tg_chat_id = st.text_input("Chat ID", placeholder="123456789")
    st.markdown("---")
    st.markdown("### 🔗 Chains")
    ALL_CHAINS = {"ethereum": ("ETH", True), "solana": ("SOL", True), "base": ("BASE", True), "bnb": ("BNB", False), "arbitrum": ("ARB", False), "polygon": ("POL", False), "optimism": ("OP", False), "avalanche": ("AVAX", False), "linea": ("LNA", False)}
    selected_chains = []
    cols = st.columns(3)
    for idx, (chain_id, (label, default)) in enumerate(ALL_CHAINS.items()):
        with cols[idx % 3]:
            if st.checkbox(label, value=default, key=f"chain_{chain_id}"):
                selected_chains.append(chain_id)
    st.markdown("---")
    st.markdown("### 🎚️ Filters")
    min_score = st.slider("Min score:", 0, 80, 0)
    new_only = st.toggle("🆕 New tokens only", value=False, help="Only alert on tokens not seen in previous scans")
    st.markdown("---")
    st.markdown("### ⏱️ Auto-Scan")
    interval_label = st.selectbox("Scan every:", list(INTERVAL_OPTIONS.keys()), index=2)
    interval_mins = INTERVAL_OPTIONS[interval_label]
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶ Start"):
            if not nansen_key:
                st.error("Need API key!")
            elif not selected_chains:
                st.error("Pick a chain!")
            else:
                st.session_state.scheduler_stop = False
                t = threading.Thread(
                    target=scheduler_loop,
                    args=(nansen_key, tg_token, tg_chat_id, selected_chains, min_score, new_only, interval_mins),
                    daemon=True
                )
                t.start()
                st.session_state.scheduler_running = True
                st.session_state.scheduler_thread = t
                st.success("Started!")
    with col2:
        if st.button("⏹ Stop"):
            st.session_state.scheduler_stop = True
            st.session_state.scheduler_running = False
            st.info("Stopped.")
    if st.session_state.scheduler_running:
        st.markdown(f'<div class="scheduler-on">● Auto-scan ON — {interval_label}<br><span style="color:#aaa;font-size:0.72rem">Scans: {st.session_state.scan_count} | API calls: {st.session_state.api_calls_total}</span></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="scheduler-off">○ Auto-scan off<br><span style="font-size:0.72rem">Total scans: {st.session_state.scan_count} | API calls: {st.session_state.api_calls_total}</span></div>', unsafe_allow_html=True)
    st.markdown("---")

    # Watchlist
    if st.session_state.watchlist:
        st.markdown("### 👁️ Watchlist")
        for sym in list(st.session_state.watchlist):
            col_w1, col_w2 = st.columns([3, 1])
            with col_w1:
                st.markdown(f'<span class="watchlist-pill">{sym}</span>', unsafe_allow_html=True)
            with col_w2:
                if st.button("✕", key=f"rm_{sym}"):
                    st.session_state.watchlist.discard(sym)
                    st.rerun()
        st.markdown("---")

    st.markdown('<p style="font-size:0.7rem;color:#555;text-align:center">Built with Nansen API · #NansenCLI</p>', unsafe_allow_html=True)

# ─── MAIN ──────────────────────────────────────────────

st.markdown('<h1 class="main-title">Smart Money Divergence Detector</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Find tokens where Smart Money accumulates while retail is fearful — across 9 chains.</p>', unsafe_allow_html=True)
st.markdown("---")

col_btn, col_new, col_ts = st.columns([2, 2, 3])
with col_btn:
    run_clicked = st.button("🔍 Run Scan Now")
with col_new:
    if st.session_state.results:
        new_count = len([t for t in st.session_state.results if t.get("_is_new")])
        if new_count:
            st.markdown(f'<p style="color:#00ff88;font-size:0.85rem;padding-top:12px">🆕 {new_count} new tokens</p>', unsafe_allow_html=True)
with col_ts:
    if st.session_state.last_run:
        st.markdown(f'<p style="color:#555;font-size:0.8rem;padding-top:12px">Last scan: {st.session_state.last_run}</p>', unsafe_allow_html=True)

if run_clicked:
    if not nansen_key:
        st.error("⚠️ Please enter your Nansen API key in the sidebar.")
        st.stop()
    if not selected_chains:
        st.error("⚠️ Please select at least one chain.")
        st.stop()
    progress = st.progress(0, text="Starting scan...")
    total = len(selected_chains)
    screener_tokens = []
    for ci, chain in enumerate(selected_chains):
        progress.progress(0.1 + (ci / total) * 0.5, text=f"📡 Scanning {chain}...")
        tokens = fetch_token_screener(chain, nansen_key)
        if tokens and isinstance(tokens[0], dict) and "_error" in tokens[0]:
            st.error(f"❌ {tokens[0]['_error']}")
            st.stop()
        for t in tokens:
            t["_chain"] = chain
        screener_tokens.extend(tokens)
    progress.progress(0.7, text="📡 Fetching SM netflows...")
    flow_tokens = fetch_smart_money_flows(selected_chains, nansen_key)
    progress.progress(0.9, text="⚙️ Scoring tokens...")
    netflow_map = {}
    for nf in flow_tokens:
        addr = safe_get(nf, "token_address", "address", "contract", default="")
        if addr: netflow_map[addr] = nf
    all_tokens = []
    for t in screener_tokens:
        if "_chain" not in t:
            t["_chain"] = t.get("chain", selected_chains[0])
        t["_score"] = compute_score(t, netflow_map)
        addr = safe_get(t, "token_address", "address", "contract", default="")
        t["_is_new"] = addr not in st.session_state.seen_tokens
        all_tokens.append(t)
    for t in all_tokens:
        addr = safe_get(t, "token_address", "address", "contract", default="")
        if addr: st.session_state.seen_tokens.add(addr)
    results = sorted(
        [t for t in all_tokens if t["_score"] >= min_score and (not new_only or t["_is_new"])],
        key=lambda x: x["_score"], reverse=True
    )
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    new_count = len([t for t in results if t["_is_new"]])
    st.session_state.scan_history.insert(0, {"ts": ts, "total": len(all_tokens), "signals": len(results), "new": new_count, "chains": selected_chains})
    st.session_state.scan_history = st.session_state.scan_history[:5]
    st.session_state.results = results
    st.session_state.all_tokens = all_tokens
    st.session_state.last_run = ts
    st.session_state.scan_count += 1
    progress.progress(1.0, text="✅ Done!")
    time.sleep(0.4)
    progress.empty()
    if tg_token and tg_chat_id and results:
        top5 = results[:5]
        new_label = f" ({new_count} NEW)" if new_count else ""
        lines = [f"*Smart Money Divergence Alert{new_label}*\n_{ts}_\n"]
        for i, t in enumerate(top5, 1):
            sym = str(safe_get(t, "token_symbol", "symbol", "name", default="???"))
            score = t["_score"]
            flow = fmt_usd(safe_get(t, "netflow", "smart_money_net_flow_usd", default=0))
            pc = safe_get(t, "price_change", "price_change_24h_pct", default=0) or 0
            chain = t.get("_chain", "")
            new_tag = " 🆕" if t.get("_is_new") else ""
            lines.append(f"{'!!' if score >= 55 else '->'} *{i}. {sym}*{new_tag} [{chain}]\nScore: `{score}` | Flow: `{flow}` | `{pc:+.1f}%`")
        lines.append("\n_Not financial advice. Built with Nansen API_")
        ok = send_telegram(tg_token, tg_chat_id, "\n".join(lines))
        if ok: st.success("📬 Telegram alert sent!")
        else: st.warning("⚠️ Telegram alert failed.")

# ─── RESULTS ───────────────────────────────────────────

if st.session_state.results:
    results = st.session_state.results
    all_tokens = st.session_state.get("all_tokens", results)
    new_count = len([t for t in results if t.get("_is_new")])

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.markdown(f'<div class="metric-box"><div class="metric-value">{len(results)}</div><div class="metric-label">Signals</div></div>', unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="metric-box"><div class="metric-value" style="color:#00ff88">{new_count}</div><div class="metric-label">New tokens</div></div>', unsafe_allow_html=True)
    with m3:
        high = len([r for r in results if r["_score"] >= 55])
        st.markdown(f'<div class="metric-box"><div class="metric-value">{high}</div><div class="metric-label">High conviction</div></div>', unsafe_allow_html=True)
    with m4:
        st.markdown(f'<div class="metric-box"><div class="metric-value">{results[0]["_score"]}</div><div class="metric-label">Top score</div></div>', unsafe_allow_html=True)
    with m5:
        st.markdown(f'<div class="metric-box"><div class="metric-value">{st.session_state.api_calls_total}</div><div class="metric-label">API calls used</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"### 📊 Divergence Signals *({len(all_tokens)} tokens scanned)*")

    for i, token in enumerate(results[:20], 1):
        addr = safe_get(token, "token_address", "address", "contract", default="")
        sym = str(safe_get(token, "token_symbol", "symbol", "name", default="???"))
        chain = token.get("_chain", token.get("chain", ""))
        score = token["_score"]
        flow = fmt_usd(safe_get(token, "netflow", "smart_money_net_flow_usd", "net_flow_usd", default=0))
        pc = safe_get(token, "price_change", "price_change_24h_pct", "price_change_pct", default=0) or 0
        traders = safe_get(token, "nof_traders", "smart_money_trader_count", "sm_traders", default=0) or 0
        token_age = safe_get(token, "token_age_days", "age_days", default=None)
        is_new = token.get("_is_new", False)
        in_watchlist = sym in st.session_state.watchlist
        arrow = "▼" if pc < 0 else "▲"
        clr = "#ff4444" if pc < 0 else "#00ff88"
        sc = "score-high" if score >= 55 else ("score-medium" if score >= 30 else "score-low")
        dex_url = f"https://dexscreener.com/{chain.lower()}/{addr}"
        new_badge = '<span class="new-badge">NEW</span>' if is_new else ""
        age_badge = f'<span class="age-badge">{int(token_age)}d old</span>' if token_age is not None else ""
        card_class = "signal-card new-token" if is_new else "signal-card"

        col_card, col_watch = st.columns([10, 1])
        with col_card:
            st.markdown(f"""<div class="{card_class}">
              <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px">
                <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
                  <span style="font-family:'Space Mono',monospace;color:#555;font-size:0.85rem">#{i:02d}</span>
                  <a href="{dex_url}" target="_blank" style="font-family:'Space Mono',monospace;font-weight:700;font-size:1.1rem;color:#00ff88;text-decoration:none;border-bottom:1px solid rgba(0,255,136,0.3)">{sym} ↗</a>
                  {new_badge}{age_badge}
                  <span class="chain-badge chain-{chain.lower()}">{chain}</span>
                </div>
                <span class="score-badge {sc}">{score} pts</span>
              </div>
              <div style="display:flex;gap:24px;margin-top:10px;flex-wrap:wrap">
                <div><div style="font-size:0.7rem;color:#555;text-transform:uppercase;letter-spacing:.07em">SM Netflow</div><div style="font-family:'Space Mono',monospace;font-size:0.95rem;color:#e6edf3">{flow}</div></div>
                <div><div style="font-size:0.7rem;color:#555;text-transform:uppercase;letter-spacing:.07em">Price 24h</div><div style="font-family:'Space Mono',monospace;font-size:0.95rem;color:{clr}">{arrow} {abs(pc):.1f}%</div></div>
                <div><div style="font-size:0.7rem;color:#555;text-transform:uppercase;letter-spacing:.07em">SM Traders</div><div style="font-family:'Space Mono',monospace;font-size:0.95rem;color:#e6edf3">{traders}</div></div>
              </div>
            </div>""", unsafe_allow_html=True)
        with col_watch:
            watch_label = "★" if in_watchlist else "☆"
            if st.button(watch_label, key=f"watch_{i}_{sym}", help="Add to watchlist"):
                if in_watchlist:
                    st.session_state.watchlist.discard(sym)
                else:
                    st.session_state.watchlist.add(sym)
                st.rerun()

    # Scan History
    if st.session_state.scan_history:
        st.markdown("---")
        st.markdown("### 🕐 Scan History *(last 5)*")
        for h in st.session_state.scan_history:
            chains_str = ", ".join(h["chains"])
            st.markdown(f'<div class="history-card">🕐 {h["ts"]} — <b style="color:#e6edf3">{h["signals"]} signals</b> ({h["new"]} new) from {h["total"]} tokens across {chains_str}</div>', unsafe_allow_html=True)

else:
    st.markdown("""<div style="text-align:center;padding:60px 20px">
    <div style="font-size:3rem">🧠</div>
    <div style="font-family:'Space Mono',monospace;font-size:1.1rem;color:#555;margin-top:12px">
    Enter your credentials in the sidebar<br>
    hit <span style="color:#00ff88">Run Scan Now</span> or <span style="color:#00ff88">▶ Start</span> for auto-scan
    </div></div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:16px">
    <div class="metric-box"><div class="metric-value">40</div><div class="metric-label">pts SM Netflow</div></div>
    <div class="metric-box"><div class="metric-value">30</div><div class="metric-label">pts Price drop</div></div>
    <div class="metric-box"><div class="metric-value">20</div><div class="metric-label">pts SM traders</div></div>
    <div class="metric-box"><div class="metric-value">10</div><div class="metric-label">pts Distribution</div></div></div>
    <div style="margin-top:16px;padding:12px 16px;background:rgba(255,60,60,0.05);border:1px solid rgba(255,60,60,0.15);border-radius:8px;font-size:0.78rem;color:#666">
    Not financial advice. For research and educational purposes only.</div>""", unsafe_allow_html=True)

# Auto-refresh when scheduler running
if st.session_state.scheduler_running:
    time.sleep(3)
    st.rerun()
