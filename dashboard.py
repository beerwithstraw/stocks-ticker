"""
Morning Movers Dashboard — v3
-------------------------------
Light theme · Sector heatmap (single row, continuous gradient) ·
Unified gainers→losers table · Sector grid (3 per row) · F&O tagging

Run:  streamlit run dashboard.py
Deps: pip install streamlit kiteconnect pandas python-dotenv
"""

import os
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from kiteconnect import KiteConnect

_HERE = Path(__file__).parent
load_dotenv(_HERE / ".env")

st.set_page_config(
    page_title="Morning Movers · NSE",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Inter', -apple-system, sans-serif !important;
    background: #f1f5f9 !important;
}
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.2rem !important; padding-bottom: 2rem !important; max-width: 1440px; }

/* ── Dashboard header ── */
.dash-title {
    font-size: 1.5rem; font-weight: 800; color: #0f172a;
    letter-spacing: -0.03em; line-height: 1;
}
.dash-title span { color: #2563eb; }
.dash-subtitle { font-size: 0.72rem; color: #94a3b8; margin-top: 4px; font-weight: 500; }

/* ── Market pulse cards ── */
.pulse-card {
    background: white; border-radius: 14px; padding: 1.1rem 1.4rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 0 0 1px rgba(0,0,0,0.04);
    height: 100%;
}
.pulse-label {
    font-size: 0.65rem; font-weight: 700; color: #94a3b8;
    text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 6px;
}
.pulse-price { font-size: 1.65rem; font-weight: 800; color: #0f172a; line-height: 1; }
.pulse-up   { font-size: 0.8rem; font-weight: 600; color: #16a34a; margin-top: 5px; }
.pulse-down { font-size: 0.8rem; font-weight: 600; color: #dc2626; margin-top: 5px; }
.pulse-flat { font-size: 0.8rem; font-weight: 500; color: #94a3b8; margin-top: 5px; }

/* ── Section labels ── */
.sec-label {
    font-size: 0.63rem; font-weight: 800; color: #94a3b8;
    text-transform: uppercase; letter-spacing: 0.12em;
    margin: 1.4rem 0 0.7rem; padding-bottom: 7px;
    border-bottom: 1.5px solid #e2e8f0;
}

/* ── Sector heatmap — SINGLE scrollable row ── */
.heatmap-scroll {
    display: flex;
    flex-wrap: nowrap;
    overflow-x: auto;
    gap: 9px;
    margin-bottom: 0.5rem;
    padding-bottom: 6px;
    scrollbar-width: thin;
    scrollbar-color: #cbd5e1 transparent;
}
.heatmap-scroll::-webkit-scrollbar { height: 4px; }
.heatmap-scroll::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
.sector-tile {
    border-radius: 11px; padding: 11px 16px;
    flex-shrink: 0; min-width: 100px;
    text-align: center; cursor: default;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}
.sector-tile:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(0,0,0,0.10); }
.s-name { font-size: 0.6rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.09em; opacity: 0.72; }
.s-pct  { font-size: 1.1rem; font-weight: 800; line-height: 1.15; margin-top: 2px; }
.s-ltp  { font-size: 0.62rem; opacity: 0.60; margin-top: 3px; font-weight: 500; }

/* ── Sector tile card headers (3-per-row grid) ── */
.sector-card-hdr {
    border-radius: 10px; padding: 10px 14px; margin-bottom: 6px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}
.sc-name { font-size: 0.62rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.1em; opacity: 0.75; }
.sc-pct  { font-size: 1.15rem; font-weight: 800; margin-top: 2px; line-height: 1.1; }
.sc-ltp  { font-size: 0.62rem; opacity: 0.60; margin-top: 2px; }

/* ── Dataframe tweaks ── */
[data-testid="stDataFrame"] {
    border-radius: 12px !important; overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.07), 0 0 0 1px rgba(0,0,0,0.04);
}

/* ── Refresh button ── */
[data-testid="stButton"] > button {
    background: #2563eb !important; color: white !important;
    border: none !important; border-radius: 8px !important;
    font-weight: 600 !important; font-size: 0.82rem !important;
    padding: 0.45rem 1.1rem !important;
    box-shadow: 0 2px 6px rgba(37,99,235,0.35) !important;
    transition: background 0.15s ease !important;
}
[data-testid="stButton"] > button:hover { background: #1d4ed8 !important; }
</style>
""", unsafe_allow_html=True)


# ─── Credentials ─────────────────────────────────────────────────────────────
# Reads from Streamlit Secrets when deployed on Streamlit Community Cloud,
# falls back to os.environ (populated from .env) for local development.
def _secret(key: str) -> str | None:
    # 1. Check session state first (populated dynamically)
    if key in st.session_state and st.session_state[key]:
        return st.session_state[key]
    # 2. Check os.environ (populated from .env or dynamically)
    val = os.environ.get(key)
    if val:
        return val
    # 3. Check Streamlit Cloud secrets
    try:
        val = st.secrets[key]
        if val:
            return val
    except Exception:
        pass
    return None


API_KEY      = _secret("KITE_API_KEY")
API_SECRET   = _secret("KITE_API_SECRET")
ACCESS_TOKEN = _secret("KITE_ACCESS_TOKEN")

_missing_base = [n for n, v in (("KITE_API_KEY", API_KEY), ("KITE_API_SECRET", API_SECRET)) if not v]
if _missing_base:
    st.error(
        f"Missing base credentials: **{', '.join(_missing_base)}**\n\n"
        "**Local:** copy `env.example` → `.env` and fill in your API Key and Secret.\n\n"
        "**Streamlit Cloud:** go to your app's **Settings → Secrets** and add the keys.",
        icon="🔑",
    )
    st.stop()


# ─── Config ──────────────────────────────────────────────────────────────────
SECTOR_INDEX = {
    "IT":          "NIFTY IT",
    "AUTO":        "NIFTY AUTO",
    "PHARMA":      "NIFTY PHARMA",
    "BANK":        "NIFTY BANK",
    "FMCG":        "NIFTY FMCG",
    "METAL":       "NIFTY METAL",
    "REALTY":      "NIFTY REALTY",
    "ENERGY":      "NIFTY ENERGY",
    "FINSERV":     "NIFTY FIN SERVICE",
    "CONSDURABLE": "NIFTY CONSR DURBL",
    "INFRA":       "NIFTY INFRA",
    "CHEMICALS":   "NIFTY CHEMICALS",
    # CEMENT / TELECOM — no Nifty index; tiles skipped, sector grid still shows.
}

# NSE F&O eligible stocks (from our universe) — update as NSE revises the list
FNO_STOCKS = {
    "TCS","INFY","WIPRO","HCLTECH","TECHM","COFORGE","PERSISTENT","LTIM",
    "MPHASIS","LTTS","TATAELXSI","KPITTECH","CYIENT","BIRLASOFT",
    "TATAMOTORS","M&M","MARUTI","BAJAJ-AUTO","EICHERMOT","HEROMOTOCO",
    "ASHOKLEY","TVSMOTOR","MOTHERSON","BOSCHLTD","BALKRISIND","BHARATFORG","ESCORTS",
    "SUNPHARMA","CIPLA","DRREDDY","DIVISLAB","AUROPHARMA","LUPIN","TORNTPHARM",
    "ALKEM","GLENMARK","BIOCON","LAURUSLABS","GRANULES","IPCALAB",
    "HDFCBANK","ICICIBANK","SBIN","KOTAKBANK","AXISBANK","INDUSINDBK",
    "FEDERALBNK","BANKBARODA","IDFCFIRSTB","BANDHANBNK","AUBANK","CANBK","PNB",
    "HINDUNILVR","ITC","NESTLEIND","BRITANNIA","DABUR","TATACONSUM",
    "GODREJCP","MARICO","COLPAL","VBL",
    "TATASTEEL","JSWSTEEL","HINDALCO","VEDL","JINDALSTEL","SAIL",
    "NMDC","HINDZINC","NATIONALUM","APLAPOLLO",
    "DLF","OBEROIRLTY","GODREJPROP","PRESTIGE","SOBHA","BRIGADE",
    "RELIANCE","ONGC","NTPC","POWERGRID","COALINDIA","BPCL",
    "TATAPOWER","GAIL","PETRONET","IOC","IGL","MGL",
    "BAJFINANCE","BAJAJFINSV","HDFCLIFE","SBILIFE","ICICIGI",
    "CHOLAFIN","LICHSGFIN","MUTHOOTFIN","RECLTD","PFC","IRFC",
    "DIXON","VOLTAS","HAVELLS","CROMPTON","TITAN","BLUESTARCO","AMBER","VGUARD",
    "LT","SIEMENS","ABB","BHEL","CUMMINSIND","THERMAX","KEC","TIINDIA",
    "PIDILITIND","SRF","DEEPAKNITR","NAVINFLUOR","ATUL",
    "ULTRACEMCO","AMBUJACEM","ACC","SHREECEM","JKCEMENT","RAMCOCEM","DALMIACEM",
    "BHARTIARTL","INDUSTOWER",
}

TOP_N_MOVERS = 5   # gainers + losers each in the unified table


# ─── Data loading ─────────────────────────────────────────────────────────────
@st.cache_resource
def get_kite():
    kite = KiteConnect(api_key=API_KEY)
    kite.set_access_token(ACCESS_TOKEN)
    return kite


def load_universe():
    """Read universe.csv fresh every time — it's tiny and must not be stale."""
    return pd.read_csv(_HERE / "universe.csv")


@st.cache_data(ttl=86400)
def load_instrument_tokens(_kite):
    instruments = _kite.instruments("NSE")
    return {i["tradingsymbol"]: i["instrument_token"] for i in instruments}


@st.cache_data(ttl=86400)
def load_daily_stats(_kite, symbols, token_map):
    to_date   = datetime.now()
    from_date = to_date - timedelta(days=380)
    stats = {}
    for sym in symbols:
        token = token_map.get(sym)
        if not token:
            continue
        try:
            candles = _kite.historical_data(token, from_date, to_date, "day")
        except Exception:
            continue
        if not candles:
            continue
        last_252 = candles[-252:]
        last_20  = candles[-20:]
        stats[sym] = {
            "52w_high":    max(c["high"]   for c in last_252),
            "52w_low":     min(c["low"]    for c in last_252),
            "avg_vol_20d": sum(c["volume"] for c in last_20) / len(last_20),
        }
    return stats


def fetch_live_quotes(kite, instrument_keys):
    quotes = {}
    for i in range(0, len(instrument_keys), 500):
        quotes.update(kite.quote(instrument_keys[i : i + 500]))
    return quotes


# ─── Visual helpers ───────────────────────────────────────────────────────────
def _lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def _tile_colors(pct: float, scale: float = 3.0):
    """Smooth continuous gradient: white at 0% → green (positive) / red (negative)."""
    t = min(1.0, abs(pct) / scale)
    if pct >= 0:
        # bg: #f8fafc → #86efac  (white → light green)
        bg  = f"#{_lerp(248,134,t):02x}{_lerp(250,239,t):02x}{_lerp(252,172,t):02x}"
        # text: #475569 → #14532d  (slate → dark green)
        clr = f"#{_lerp(71,20,t):02x}{_lerp(85,83,t):02x}{_lerp(105,45,t):02x}"
    else:
        # bg: #f8fafc → #fca5a5  (white → light red)
        bg  = f"#{_lerp(248,252,t):02x}{_lerp(250,165,t):02x}{_lerp(252,165,t):02x}"
        # text: #475569 → #7f1d1d  (slate → dark red)
        clr = f"#{_lerp(71,127,t):02x}{_lerp(85,29,t):02x}{_lerp(105,29,t):02x}"
    return bg, clr


def sector_tile_html(name: str, pct: float, ltp: float) -> str:
    bg, clr = _tile_colors(pct)
    sign = "+" if pct >= 0 else ""
    return (
        f'<div class="sector-tile" style="background:{bg};color:{clr};">'
        f'  <div class="s-name">{name}</div>'
        f'  <div class="s-pct">{sign}{pct:.2f}%</div>'
        f'  <div class="s-ltp">{ltp:,.0f}</div>'
        f'</div>'
    )


def sector_card_header(name: str, pct: float | None, ltp: float | None) -> str:
    if pct is None:
        bg, clr = "#f8fafc", "#475569"
        pct_str, ltp_str = "—", "—"
    else:
        bg, clr = _tile_colors(pct)
        sign    = "+" if pct >= 0 else ""
        pct_str = f"{sign}{pct:.2f}%"
        ltp_str = f"{ltp:,.0f}"
    return (
        f'<div class="sector-card-hdr" style="background:{bg};color:{clr};">'
        f'  <div class="sc-name">{name}</div>'
        f'  <div class="sc-pct">{pct_str}</div>'
        f'  <div class="sc-ltp">{ltp_str}</div>'
        f'</div>'
    )


def pulse_card(label: str, price_str: str, delta_str: str, direction: str) -> str:
    delta_class = {"up": "pulse-up", "down": "pulse-down", "flat": "pulse-flat"}[direction]
    return (
        f'<div class="pulse-card">'
        f'  <div class="pulse-label">{label}</div>'
        f'  <div class="pulse-price">{price_str}</div>'
        f'  <div class="{delta_class}">{delta_str}</div>'
        f'</div>'
    )


def _move_style(val):
    try:    v = float(val)
    except: return ""
    if   v >=  3.0: return "background-color:#dcfce7;color:#14532d;font-weight:700"
    elif v >=  1.5: return "background-color:#bbf7d0;color:#166534;font-weight:600"
    elif v >=  0.3: return "background-color:#f0fdf4;color:#15803d"
    elif v >= -0.3: return ""
    elif v >= -1.5: return "background-color:#fff1f2;color:#9f1239"
    elif v >= -3.0: return "background-color:#fecdd3;color:#881337;font-weight:600"
    else:           return "background-color:#fee2e2;color:#7f1d1d;font-weight:700"


def styled_df(data: pd.DataFrame, cols: list):
    present = [c for c in cols if c in data.columns]
    s = data[present].style
    if "Move %" in present:
        s = s.map(_move_style, subset=["Move %"])
    fmt = {
        "LTP":          "{:,.2f}",
        "Move %":       "{:+.2f}%",
        "52w Position": "{:.0%}",
    }
    s = s.format({k: v for k, v in fmt.items() if k in present}, na_rep="—")
    return s


# ─── Column configs ───────────────────────────────────────────────────────────
_PROGRESS_COL = st.column_config.ProgressColumn("52w Range", min_value=0, max_value=1, format="")
_MOVE_COL     = st.column_config.NumberColumn("Move %", format="%.2f%%")

# Movers table: Symbol (with tags), LTP, Move %, 52w Range
MOVERS_COLS  = ["Symbol", "LTP", "Move %", "52w Position"]
MOVERS_CFG   = {"Move %": _MOVE_COL, "52w Position": _PROGRESS_COL}

# Sector mini-table: same 4 columns
SECTOR_COLS  = ["Symbol", "LTP", "Move %", "52w Position"]
SECTOR_CFG   = {"Move %": _MOVE_COL, "52w Position": _PROGRESS_COL}


# ─── Page ─────────────────────────────────────────────────────────────────────
universe = load_universe()
kite     = get_kite()

hdr_l, hdr_fno, hdr_tok, hdr_ref = st.columns([5, 1, 1, 1])
with hdr_l:
    st.markdown('<div class="dash-title">Morning <span>Movers</span></div>', unsafe_allow_html=True)
with hdr_fno:
    fno_only = st.toggle("F&O Only", key="fno_toggle", value=False)
with hdr_tok:
    # Auto-open token UI if access token is missing
    show_token_ui = st.toggle("🔑 Token", key="show_token", value=not bool(ACCESS_TOKEN))
with hdr_ref:
    refresh = st.button("⧳  Refresh", key="refresh_btn")

# ── Token renewal panel ───────────────────────────────────────────────────────
if show_token_ui:
    with st.container():
        st.markdown(
            '<div style="background:white;border-radius:12px;padding:1rem 1.2rem;'
            'border:1.5px solid #e2e8f0;margin-bottom:1rem;">',
            unsafe_allow_html=True,
        )
        st.markdown("**🔑 Renew Kite Access Token** &nbsp; *(expires daily at midnight)*")
        st.caption(
            "1. Click the login link below · 2. Log in to Zerodha · "
            "3. Copy the full redirect URL · 4. Paste it here and hit Save"
        )
        _login_url = KiteConnect(api_key=API_KEY).login_url()
        st.markdown(f"**[Open Kite Login →]({_login_url})**")
        _redirect = st.text_input(
            "Paste redirect URL",
            placeholder="http://127.0.0.1:5000/kite/callback?request_token=...",
            label_visibility="collapsed",
            key="token_redirect_url",
        )
        if st.button("Save Token", key="save_token_btn"):
            import re
            _match = re.search(r"[?&]request_token=([^&]+)", _redirect)
            if not _match:
                st.error("Could not find request_token in that URL — please try again.")
            else:
                try:
                    _kite_tmp = KiteConnect(api_key=API_KEY)
                    _session  = _kite_tmp.generate_session(_match.group(1), api_secret=API_SECRET)
                    from dotenv import set_key as _set_key
                    _set_key(str(_HERE / ".env"), "KITE_ACCESS_TOKEN", _session["access_token"])
                    # Reload env & session so the running process picks up the new token
                    os.environ["KITE_ACCESS_TOKEN"] = _session["access_token"]
                    st.session_state["KITE_ACCESS_TOKEN"] = _session["access_token"]
                    # Clear all caches so the new token is used on next data pull
                    st.cache_resource.clear()
                    st.cache_data.clear()
                    st.success("✅ Token saved! Hit Refresh to pull fresh data.")
                    st.session_state.pop("data_loaded", None)
                    st.rerun()  # Instantly reload the page to apply the token
                except Exception as _e:
                    st.error(f"Failed to generate session: {_e}")
        st.markdown("</div>", unsafe_allow_html=True)

if not ACCESS_TOKEN:
    st.warning("⚠️ **Kite Access Token is missing.** Please use the token renewal panel above.", icon="🚨")
    st.stop()

if "data_loaded" not in st.session_state:
    refresh = True

if refresh:
    with st.spinner("Pulling live data from Kite…"):
        try:
            token_map   = load_instrument_tokens(kite)
            daily_stats = load_daily_stats(kite, universe["symbol"].tolist(), token_map)

            stock_keys  = [f"NSE:{s}"   for s in universe["symbol"]]
            index_keys  = [f"NSE:{idx}" for idx in SECTOR_INDEX.values()]
            market_keys = [
                "NSE:NIFTY 50", "NSE:NIFTY BANK", "NSE:INDIA VIX",
                "NSE:GOLDBEES",   # Gold ETF proxy (Nippon India Gold BeES)
                "NSE:SILVERBEES", # Silver ETF proxy (Nippon India Silver ETF)
            ]

            quotes = fetch_live_quotes(kite, stock_keys + index_keys + market_keys)
            st.session_state.update({
                "quotes": quotes, "daily_stats": daily_stats,
                "last_refreshed": datetime.now(), "data_loaded": True,
            })
            st.toast(f"Loaded {len(universe)} stocks · {len(SECTOR_INDEX)} indexed sectors", icon="✅")
        except Exception as e:
            st.error(f"**Kite API Error:** {e}")
            st.warning("Your token might be expired. Please use the **🔑 Token** panel above to generate a new one.", icon="🚨")
            st.session_state.pop("data_loaded", None)
            st.stop()

if not st.session_state.get("data_loaded"):
    st.stop()

quotes      = st.session_state["quotes"]
daily_stats = st.session_state["daily_stats"]
last_ref    = st.session_state["last_refreshed"]

with hdr_l:
    st.markdown(
        f'<div class="dash-subtitle">Last refreshed: {last_ref.strftime("%I:%M:%S %p")} · '
        f'NSE · {len(universe)} stocks · {len(SECTOR_INDEX)} sectors</div>',
        unsafe_allow_html=True,
    )

# ── Market pulse ──────────────────────────────────────────────────────────────
st.markdown('<div class="sec-label">Market Pulse</div>', unsafe_allow_html=True)
pc1, pc2, pc3, pc4, pc5 = st.columns(5)
for col, key, label, is_vix in [
    (pc1, "NSE:NIFTY 50",   "Nifty 50",   False),
    (pc2, "NSE:NIFTY BANK", "Bank Nifty", False),
    (pc3, "NSE:INDIA VIX",  "India VIX",  True),
    (pc4, "NSE:GOLDBEES",   "Gold",       False),
    (pc5, "NSE:SILVERBEES", "Silver",     False),
]:
    q = quotes.get(key)
    if not q:
        continue
    chg = q["last_price"] - q["ohlc"]["close"]
    pct = chg / q["ohlc"]["close"] * 100
    direction = "flat" if is_vix else ("up" if chg >= 0 else "down")
    sign = "+" if chg >= 0 else ""
    col.markdown(
        pulse_card(label, f"{q['last_price']:,.2f}", f"{sign}{chg:,.2f}  ({sign}{pct:.2f}%)", direction),
        unsafe_allow_html=True,
    )

# ── Build working dataframe ───────────────────────────────────────────────────
rows = []
for _, r in universe.iterrows():
    sym   = r["symbol"]
    q     = quotes.get(f"NSE:{sym}")
    stats = daily_stats.get(sym)
    if not q or not stats:
        continue
    prev_close = q["ohlc"]["close"]
    ltp        = q["last_price"]
    pct_move   = (ltp - prev_close) / prev_close * 100
    rng        = stats["52w_high"] - stats["52w_low"]
    range_pos  = (ltp - stats["52w_low"]) / rng if rng else None

    rows.append({
        "Symbol":       sym,
        "_sym_raw":     sym,
        "_is_fno":      sym in FNO_STOCKS,
        "Sector":       r["sector"],
        "LTP":          ltp,
        "Move %":       pct_move,
        "52w Position": range_pos,
    })

df = pd.DataFrame(rows)

# ── Sector heatmap — single scrollable row, sorted high → low ─────────────────
sector_moves: dict = {}
for sector, idx_symbol in SECTOR_INDEX.items():
    q = quotes.get(f"NSE:{idx_symbol}")
    if q:
        pct = (q["last_price"] - q["ohlc"]["close"]) / q["ohlc"]["close"] * 100
        sector_moves[sector] = (pct, q)

sectors_by_move = sorted(sector_moves.items(), key=lambda x: x[1][0], reverse=True)

st.markdown('<div class="sec-label">Sector Heatmap — Top 5 Gainers &amp; Losers</div>', unsafe_allow_html=True)

# Show only top-5 gainers (front) + top-5 losers (back), separated by a divider tile
_n = min(5, len(sectors_by_move) // 2)
heatmap_sectors = sectors_by_move[:_n] + sectors_by_move[-_n:]

# Divider tile between gainers and losers
_divider = '<div style="width:2px;background:#e2e8f0;border-radius:2px;align-self:stretch;flex-shrink:0;"></div>'

gainer_tiles = "".join(
    sector_tile_html(sec, pct, q["last_price"])
    for sec, (pct, q) in sectors_by_move[:_n]
)
loser_tiles = "".join(
    sector_tile_html(sec, pct, q["last_price"])
    for sec, (pct, q) in sectors_by_move[-_n:]
)
st.markdown(
    f'<div class="heatmap-scroll">{gainer_tiles}{_divider}{loser_tiles}</div>',
    unsafe_allow_html=True,
)

# ── Top Movers: highest gainer → highest loser, 5 each ───────────────────────
st.markdown('<div class="sec-label">Top Movers — Gainers → Losers</div>', unsafe_allow_html=True)

_df_view = df[df["_is_fno"]] if fno_only else df

by_move     = _df_view.sort_values("Move %", ascending=False)
top_gainers = by_move.head(TOP_N_MOVERS)
top_losers  = by_move.tail(TOP_N_MOVERS).sort_values("Move %", ascending=True)

movers = (
    pd.concat([top_gainers, top_losers])
    .drop_duplicates(subset="_sym_raw")
    .sort_values("Move %", ascending=False)
)

st.dataframe(
    styled_df(movers, MOVERS_COLS),
    column_config=MOVERS_CFG,
    hide_index=True,
    width="stretch",
)

# ── Sector grid — 3 tiles per row ─────────────────────────────────────────────
st.markdown('<div class="sec-label">By Sector</div>', unsafe_allow_html=True)

# Build ordered list: index sectors first (by move), then no-index sectors (alpha)
# Fixed priority order — important sectors always shown first regardless of daily performance
SECTOR_PRIORITY = [
    "BANK", "IT", "PHARMA", "AUTO", "FMCG",
    "METAL", "FINSERV", "ENERGY", "CONSDURABLE", "REALTY",
    "INFRA", "CHEMICALS", "TELECOM", "CEMENT",
    "SERVICES", "TEXTILES", "MEDIA", "OTHER",
]
available_sectors = set(df["Sector"].unique())
# Priority sectors that exist in our universe first, then any remaining alphabetically
all_sectors = (
    [s for s in SECTOR_PRIORITY if s in available_sectors]
    + sorted(s for s in available_sectors if s not in SECTOR_PRIORITY)
)

for row_start in range(0, len(all_sectors), 3):
    chunk = all_sectors[row_start : row_start + 3]
    cols  = st.columns(3)

    for ci, sector in enumerate(chunk):
        # Sector index data (if available)
        if sector in sector_moves:
            idx_pct, idx_q = sector_moves[sector]
            hdr = sector_card_header(sector, idx_pct, idx_q["last_price"])
        else:
            hdr = sector_card_header(sector, None, None)

        with cols[ci]:
            st.markdown(hdr, unsafe_allow_html=True)

            sdf = df[df["Sector"] == sector]
            if fno_only:
                sdf = sdf[sdf["_is_fno"]]
            top3 = sdf.nlargest(3, "Move %")
            bot3 = sdf.nsmallest(3, "Move %").sort_values("Move %", ascending=True)
            combined = (
                pd.concat([top3, bot3])
                .drop_duplicates(subset="_sym_raw")
                .sort_values("Move %", ascending=False)
            )
            if combined.empty:
                st.caption("No F&O stocks in this sector.")
            else:
                st.dataframe(
                    styled_df(combined, SECTOR_COLS),
                    column_config=SECTOR_CFG,
                    hide_index=True,
                    width="stretch",
                )

    # Visual spacer between rows of tiles
    st.markdown("<div style='margin-bottom:1rem'></div>", unsafe_allow_html=True)

# ── Glossary ──────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "**Symbol tags** — `[SECTOR]` = sector tag · `[F&O]` = stock has futures & options on NSE.  "
    "**52w Range** — progress bar: 0 = 52-week low, 100% = 52-week high.  "
    "**Move %** — % change from previous close."
)
