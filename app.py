"""TripMind — Multi-Agent Travel Planning UI."""

from dotenv import load_dotenv
load_dotenv()

import tracing
tracing.init_tracing(project_name="tripmind-ui")

import json
import re
import uuid
import markdown as md_lib
import streamlit as st
from agents.agent import chat_invoke

st.set_page_config(
    page_title="TripMind",
    page_icon="✈️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.main .block-container { max-width: 680px; padding: 0 1rem 5rem; }

/* Hero */
.hero-title {
    font-size: 1.55rem; font-weight: 800; margin: 1.2rem 0 0.2rem;
    background: linear-gradient(135deg,#155252,#27ae7a);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
}
.hero-sub { color:#5a7272; font-size:0.84rem; margin:0 0 1rem; }

/* User bubble */
.user-bubble {
    background:#155252; color:#fff; border-radius:18px 18px 4px 18px;
    padding:11px 16px; display:inline-block; font-size:0.92rem; line-height:1.5;
    max-width:84%; box-shadow:0 2px 10px rgba(21,82,82,.28);
}
.user-row { display:flex; justify-content:flex-end; margin:6px 0 10px; }

/* Base card */
.sc {
    background:#fff; border-radius:14px; border:1px solid #dde8e5;
    box-shadow:0 2px 10px rgba(21,82,82,.07); overflow:hidden; margin:8px 0;
}
.sc-head {
    display:flex; align-items:center; justify-content:space-between;
    padding:10px 16px 8px; border-bottom:1px solid #f0f4f3;
}
.sc-label { font-size:0.7rem; font-weight:700; letter-spacing:.09em; color:#5a7272; text-transform:uppercase; }

/* Pills */
.pill { display:inline-block; border-radius:20px; padding:3px 10px; font-size:0.7rem; font-weight:700; letter-spacing:.04em; }
.pill-green  { background:#d4f5e5; color:#0e6b3d; }
.pill-orange { background:#fde8d0; color:#8a4000; }
.pill-red    { background:#fdddd8; color:#8b1a0e; }
.pill-teal   { background:#d4eaea; color:#155252; }
.pill-blue   { background:#dbeafe; color:#1d4ed8; }
.pill-gray   { background:#f1f5f9; color:#475569; }

/* Trip Overview grid */
.ov-grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; padding:14px 16px 16px; }
.ov-item { display:flex; align-items:flex-start; gap:8px; }
.ov-icon { font-size:1.1rem; flex-shrink:0; margin-top:1px; }
.ov-label { font-size:0.68rem; color:#5a7272; font-weight:500; margin-bottom:1px; }
.ov-value { font-size:0.88rem; color:#1a2e2e; font-weight:600; line-height:1.3; }

/* Flight */
.fl-airline { font-size:0.82rem; color:#5a7272; font-weight:500; margin-bottom:10px; }
.fl-leg { margin:10px 0; }
.fl-leg-label { font-size:0.68rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase; color:#5a7272; margin-bottom:6px; }
.fl-route { display:flex; align-items:center; }
.fl-airport { flex-shrink:0; }
.fl-iata  { font-size:1.45rem; font-weight:800; color:#155252; letter-spacing:-.02em; }
.fl-time  { font-size:0.8rem; color:#5a7272; margin-top:2px; }
.fl-mid   { flex:1; text-align:center; padding:0 10px; }
.fl-line  { position:relative; height:2px; background:#dde8e5; margin:0 4px 6px; }
.fl-plane { position:absolute; top:-8px; left:50%; transform:translateX(-50%); font-size:.95rem; }
.fl-dur   { font-size:0.78rem; font-weight:600; color:#1a2e2e; }
.fl-stops { font-size:0.72rem; color:#5a7272; margin-top:1px; }
.fl-divider { border:none; border-top:1px dashed #dde8e5; margin:10px 0; }
.fl-total { background:#f0f9f5; border-radius:8px; padding:9px 14px; display:flex; justify-content:space-between; align-items:center; margin-top:6px; }
.fl-total-label { font-size:0.8rem; color:#5a7272; }
.fl-total-value { font-size:1rem; font-weight:700; color:#155252; }

/* Hotel */
.ht-name  { font-size:.98rem; font-weight:700; color:#1a2e2e; }
.ht-loc   { font-size:.8rem; color:#5a7272; margin-top:2px; }
.ht-price { font-size:.84rem; color:#5a7272; margin-top:8px; }
.ht-price strong { color:#155252; }

/* Weather */
.wx-temp  { font-size:2rem; font-weight:800; color:#155252; line-height:1; }
.wx-unit  { font-size:.95rem; color:#5a7272; }
.wx-row   { display:flex; align-items:center; justify-content:space-between; margin-bottom:6px; }
.wx-cond  { font-size:.86rem; color:#5a7272; margin-top:4px; }
.wx-detail{ font-size:.8rem; color:#7a9292; margin-top:2px; }

/* Budget */
.bud-row { display:flex; align-items:center; justify-content:space-between; padding:7px 0; border-bottom:1px solid #f5f8f7; }
.bud-row:last-of-type { border-bottom:none; }
.bud-left { display:flex; align-items:center; gap:10px; }
.bud-dot  { width:9px; height:9px; border-radius:50%; flex-shrink:0; }
.bud-cat  { font-size:.86rem; color:#1a2e2e; }
.bud-amt  { font-size:.86rem; font-weight:600; color:#1a2e2e; }
.bud-total{ display:flex; justify-content:space-between; align-items:center; padding:10px 0 0; margin-top:4px; border-top:2px solid #dde8e5; font-weight:700; font-size:.93rem; color:#155252; }
.bud-bar-bg   { height:5px; background:#e8f0ef; border-radius:3px; overflow:hidden; margin-top:12px; }
.bud-bar-fill { height:100%; border-radius:3px; background:linear-gradient(90deg,#155252,#27ae7a); }

/* Day cards */
.days-label { font-size:.7rem; font-weight:700; color:#5a7272; letter-spacing:.09em; text-transform:uppercase; padding:12px 16px 6px; }
.days-scroll { display:flex; gap:10px; overflow-x:auto; padding:0 16px 16px; scroll-snap-type:x mandatory; -webkit-overflow-scrolling:touch; }
.days-scroll::-webkit-scrollbar { height:3px; }
.days-scroll::-webkit-scrollbar-thumb { background:#c0d4d4; border-radius:2px; }
.day-card { flex:0 0 175px; border:1.5px solid #dde8e5; border-radius:12px; padding:13px; background:#fff; scroll-snap-align:start; }
.day-card.first { border-color:#155252; }
.day-num   { font-size:.66rem; font-weight:700; letter-spacing:.1em; color:#27ae7a; text-transform:uppercase; margin-bottom:5px; }
.day-theme { font-size:.86rem; font-weight:700; color:#1a2e2e; margin-bottom:5px; line-height:1.3; }
.day-prev  { font-size:.76rem; color:#5a7272; line-height:1.45; }

/* Packing */
.pack-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; padding:14px 16px; }
.pack-cat  { background:#f5f9f8; border-radius:10px; padding:10px 12px; }
.pack-icon { font-size:.95rem; margin-bottom:4px; }
.pack-name { font-size:.7rem; font-weight:700; color:#155252; text-transform:uppercase; letter-spacing:.05em; margin-bottom:5px; }
.pack-item { font-size:.78rem; color:#3a5252; padding:2px 0; display:flex; align-items:flex-start; gap:5px; line-height:1.4; }
.pack-item::before { content:"•"; color:#27ae7a; flex-shrink:0; font-weight:700; }

/* Recommendation */
.rec-block { background:#155252; border-radius:14px; padding:18px 20px; margin:8px 0; }
.rec-quote { font-size:.93rem; font-style:italic; line-height:1.6; color:#cce8e5; }
.rec-actions { display:flex; flex-wrap:wrap; gap:8px; margin-top:14px; }
.rec-btn { background:rgba(255,255,255,.12); color:#fff; border:1px solid rgba(255,255,255,.28); border-radius:20px; padding:6px 14px; font-size:.8rem; font-weight:500; }

/* Comparison */
.cmp-grid { display:grid; gap:12px; margin:8px 0; }
.cmp-grid.c2 { grid-template-columns:1fr 1fr; }
.cmp-grid.c3 { grid-template-columns:1fr 1fr 1fr; }
.cmp-card { border-radius:14px; border:2px solid #dde8e5; background:#fff; overflow:hidden; box-shadow:0 2px 10px rgba(21,82,82,.06); }
.cmp-head { padding:12px 14px 8px; font-weight:800; font-size:.95rem; }
.cmp-tag  { font-size:.78rem; font-weight:400; color:#5a7272; margin-top:1px; }
.cmp-body { padding:0 14px 14px; }
.cmp-row  { display:flex; gap:6px; padding:5px 0; border-bottom:1px solid #f5f8f7; font-size:.82rem; }
.cmp-row:last-child { border-bottom:none; }
.cmp-row-label { color:#5a7272; font-weight:500; min-width:80px; flex-shrink:0; }
.cmp-row-val { color:#1a2e2e; }
.cmp-highlights { padding:8px 0 0; }
.cmp-hl-item { font-size:.78rem; color:#1a2e2e; padding:2px 0; display:flex; gap:5px; }
.cmp-hl-item::before { content:"✦"; color:#27ae7a; flex-shrink:0; font-size:.65rem; margin-top:3px; }
.cmp-verdict { background:#f0f9f5; border-radius:8px; margin:10px 0 0; padding:8px 10px; font-size:.78rem; color:#0e6b3d; font-weight:600; }
.cmp-rec { background:#155252; border-radius:12px; padding:14px 16px; margin:8px 0; font-size:.88rem; font-style:italic; color:#cce8e5; line-height:1.55; }

/* Markdown (type:text) */
.md-body { font-size:.9rem; color:#1a2e2e; line-height:1.65; padding:2px 0; }
.md-body p { margin:.3em 0; }
.md-body ul { margin:.4em 0 .4em 1.2em; padding:0; }
.md-body li { margin:.2em 0; }
.md-body strong { color:#0f172a; }
.md-body h3,.md-body h4 { font-size:.92rem; margin:.7em 0 .25em; }
.md-body table { width:100%; border-collapse:collapse; font-size:.84rem; margin:.5em 0; }
.md-body th { background:#f5f8f7; padding:6px 10px; text-align:left; font-weight:600; border-bottom:2px solid #dde8e5; color:#334155; }
.md-body td { padding:5px 10px; border-bottom:1px solid #f0f4f3; }
.md-body tr:last-child td { border-bottom:none; }
.md-body tr:nth-child(even) td { background:#f8fbfa; }
.md-body code { background:#f1f5f9; border-radius:4px; padding:1px 5px; font-size:.83em; color:#7c3aed; }

.stChatInput > div { border-radius:14px !important; }
[data-testid="stSidebar"] { background:#f5f8f7; }
</style>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────────────────────
DOT_COLORS = ["#155252","#27ae7a","#e67e22","#7c3aed","#0891b2","#dc2626","#94a3b8","#ec4899"]
CMP_PALETTES = [
    ("#155252","#e6f5f2","#9fd4c8"),
    ("#059669","#ecfdf5","#6ee7b7"),
    ("#7c3aed","#f5f3ff","#c4b5fd"),
    ("#d97706","#fffbeb","#fcd34d"),
]
PACK_ICONS = {"rain":"🌧️","clothing":"👕","essential":"📋","document":"📄",
              "electronic":"📱","activity":"🏖️","health":"💊","pro tip":"💡","hygiene":"🧴"}
def _pack_icon(cat): return next((v for k,v in PACK_ICONS.items() if k in cat.lower()),"🎒")

def _fmt_inr(amount_inr) -> str:
    try: return f"₹{int(amount_inr):,}"
    except: return str(amount_inr)

def _md(text: str) -> str:
    return md_lib.markdown(str(text).strip(), extensions=["tables","nl2br","sane_lists"])


# ── JSON parsing ──────────────────────────────────────────────────────────────
def _parse_response(raw: str) -> dict:
    """Try to extract a JSON object from the agent response."""
    raw = raw.strip()
    # Direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Wrapped in markdown code fence
    m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
    if m:
        try: return json.loads(m.group(1))
        except: pass
    # First { ... } block
    m = re.search(r'\{.*\}', raw, re.DOTALL)
    if m:
        try: return json.loads(m.group(0))
        except: pass
    # Fallback: treat as plain text
    return {"type": "text", "content": raw}


# ── Section renderers ─────────────────────────────────────────────────────────
def _html_overview(data: dict) -> str:
    ov = data.get("overview", {})
    def item(icon, label, val):
        if not val: return ""
        return (f'<div class="ov-item"><span class="ov-icon">{icon}</span>'
                f'<div><div class="ov-label">{label}</div>'
                f'<div class="ov-value">{val}</div></div></div>')
    dur = ov.get("duration_days","")
    pill = f'<span class="pill pill-green">{dur} Days</span>' if dur else ""
    grid = (item("🗓️","Dates", ov.get("dates","")) +
            item("👥","Travelers", ov.get("travelers","")) +
            item("💰","Budget", ov.get("budget_total","")) +
            item("📍","Destination", ov.get("destination","")))
    return (f'<div class="sc"><div class="sc-head">'
            f'<span class="sc-label">Trip Overview</span>{pill}</div>'
            f'<div class="ov-grid">{grid}</div></div>')

def _html_leg(leg: dict, label: str) -> str:
    if not leg: return ""
    stops = leg.get("stops", 0)
    stop_str = "Non-stop" if stops == 0 else f'{stops} stop{"s" if stops>1 else ""}'
    return (f'<div class="fl-leg">'
            f'<div class="fl-leg-label">{label}</div>'
            f'<div class="fl-route">'
            f'<div class="fl-airport"><div class="fl-iata">{leg.get("origin_iata","")}</div>'
            f'<div class="fl-time">{leg.get("dep","")}</div></div>'
            f'<div class="fl-mid"><div class="fl-line"><span class="fl-plane">✈️</span></div>'
            f'<div class="fl-dur">{leg.get("duration","")}</div>'
            f'<div class="fl-stops">{stop_str}</div></div>'
            f'<div class="fl-airport" style="text-align:right">'
            f'<div class="fl-iata">{leg.get("dest_iata","")}</div>'
            f'<div class="fl-time">{leg.get("arr","")}</div></div>'
            f'</div></div>')

def _html_flight(data: dict) -> str:
    fl = data.get("flight", {})
    if not fl: return ""
    has_return = bool(fl.get("return"))
    nonstop = fl.get("outbound",{}).get("stops",1) == 0
    stop_pill = ('<span class="pill pill-green">Non-stop</span>' if nonstop
                 else '<span class="pill pill-orange">Connecting</span>')
    outbound_html = _html_leg(fl.get("outbound",{}), "Outbound" if has_return else "")
    return_html   = _html_leg(fl.get("return",{}), "Return") if has_return else ""
    divider = '<hr class="fl-divider">' if has_return and return_html else ""
    total_inr = fl.get("total_inr") or fl.get("combined_total_inr")
    travelers = data.get("overview",{}).get("travelers", 2)
    price_html = ""
    if total_inr:
        price_html = (f'<div class="fl-total">'
                      f'<span class="fl-total-label">Total for {travelers} adults</span>'
                      f'<span class="fl-total-value">{_fmt_inr(total_inr)}</span></div>')
    airline_str = fl.get("airline","")
    fn = fl.get("flight_number","")
    if fn: airline_str += f" · {fn}"
    return (f'<div class="sc"><div class="sc-head">'
            f'<span class="sc-label">Recommended Flights</span>{stop_pill}</div>'
            f'<div style="padding:10px 16px 14px">'
            f'<div class="fl-airline">{airline_str}</div>'
            f'{outbound_html}{divider}{return_html}{price_html}</div></div>')

def _html_hotel(data: dict) -> str:
    ht = data.get("hotel", {})
    if not ht: return ""
    rating = ht.get("rating","")
    star_pill = f'<span class="pill pill-teal">★ {rating}</span>' if rating else ""
    area  = f'<div class="ht-loc">📍 {ht["area"]}</div>' if ht.get("area") else ""
    parts = []
    if ht.get("price_per_night_inr"): parts.append(f'{_fmt_inr(ht["price_per_night_inr"])}/night')
    if ht.get("nights"):              parts.append(f'{ht["nights"]} nights')
    if ht.get("total_inr"):           parts.append(f'Total: <strong>{_fmt_inr(ht["total_inr"])}</strong>')
    price_html = f'<div class="ht-price">{" · ".join(parts)}</div>' if parts else ""
    return (f'<div class="sc"><div class="sc-head">'
            f'<span class="sc-label">Best Hotel</span>{star_pill}</div>'
            f'<div style="padding:12px 16px 14px">'
            f'<div class="ht-name">{ht.get("name","")}</div>'
            f'{area}{price_html}</div></div>')

def _html_weather(data: dict) -> str:
    wx = data.get("weather", {})
    if not wx: return ""
    temp = str(wx.get("temp",""))
    temp_num = temp.split("–")[0].split("-")[0].replace("°C","").strip()
    warn = wx.get("warning","")
    warn_pill = (f'<span class="pill pill-red">⚠ {warn}</span>' if warn
                 else '<span class="pill pill-teal">Forecast</span>')
    temp_html = (f'<div style="display:flex;align-items:flex-end;gap:4px;">'
                 f'<span class="wx-temp">{temp_num}</span>'
                 f'<span class="wx-unit">°C</span></div>') if temp_num else ""
    cond_html  = f'<div class="wx-cond">{wx.get("condition","")}</div>' if wx.get("condition") else ""
    humid_html = f'<div class="wx-detail">Humidity: {wx["humidity"]}</div>' if wx.get("humidity") else ""
    return (f'<div class="sc"><div class="sc-head">'
            f'<span class="sc-label">Weather Forecast</span>{warn_pill}</div>'
            f'<div style="padding:12px 16px 14px">'
            f'<div class="wx-row">{temp_html}{warn_pill}</div>'
            f'{cond_html}{humid_html}</div></div>')

def _html_budget(data: dict) -> str:
    items = data.get("budget_breakdown", [])
    if not items: return ""
    rows = ""
    total = 0
    for i, entry in enumerate(items):
        amt = entry.get("amount_inr", 0)
        try: total += int(amt)
        except: pass
        color = DOT_COLORS[i % len(DOT_COLORS)]
        rows += (f'<div class="bud-row"><div class="bud-left">'
                 f'<div class="bud-dot" style="background:{color}"></div>'
                 f'<span class="bud-cat">{entry.get("category","")}</span></div>'
                 f'<span class="bud-amt">{_fmt_inr(amt)}</span></div>')
    budget_str = data.get("overview",{}).get("budget_total","")
    try:
        budget_num = int(re.sub(r'[^\d]','',budget_str)) if budget_str else 0
        pct = min(round(total / budget_num * 100), 100) if budget_num else 80
    except: pct = 80
    bar = (f'<div class="bud-bar-bg"><div class="bud-bar-fill" style="width:{pct}%"></div></div>')
    return (f'<div class="sc"><div class="sc-head">'
            f'<span class="sc-label">Budget Breakdown</span></div>'
            f'<div style="padding:10px 16px 14px">{rows}'
            f'<div class="bud-total"><span>Total Planned</span><span>{_fmt_inr(total)}</span></div>'
            f'{bar}</div></div>')

def _html_days(data: dict) -> str:
    days = data.get("itinerary", [])
    if not days: return ""
    cards = ""
    for i, d in enumerate(days):
        cls = "day-card first" if i == 0 else "day-card"
        theme = d.get("theme","")
        summary = d.get("summary","") or ""
        summary = re.sub(r'\*+','',summary)[:110]
        cards += (f'<div class="{cls}">'
                  f'<div class="day-num">DAY {d.get("day","")}</div>'
                  f'<div class="day-theme">{theme}</div>'
                  f'<div class="day-prev">{summary}</div></div>')
    label = f'Itinerary ({len(days)} Day{"s" if len(days)!=1 else ""})'
    return (f'<div class="sc">'
            f'<div class="days-label">{label}</div>'
            f'<div class="days-scroll">{cards}</div></div>')

def _html_packing(data: dict) -> str:
    cats = data.get("packing", [])
    if not cats: return ""
    grid = ""
    for entry in cats:
        name  = entry.get("category","")
        items = entry.get("items", [])
        items_html = "".join(f'<div class="pack-item">{i}</div>' for i in items[:6])
        grid += (f'<div class="pack-cat">'
                 f'<div class="pack-icon">{_pack_icon(name)}</div>'
                 f'<div class="pack-name">{name}</div>'
                 f'{items_html}</div>')
    return (f'<div class="sc"><div class="sc-head">'
            f'<span class="sc-label">Packing List</span>'
            f'<span class="pill pill-teal">🎒 Smart List</span></div>'
            f'<div class="pack-grid">{grid}</div></div>')

def _html_recommendation(data: dict) -> str:
    rec = data.get("recommendation","")
    if not rec: return ""
    return (f'<div class="rec-block">'
            f'<div class="rec-quote">"{rec}"</div>'
            f'</div>')

def _html_comparison(data: dict) -> str:
    options = data.get("options",[])
    n = min(len(options), 3)
    cls = f"c{n}" if n <= 3 else "c3"
    cards = ""
    for i, opt in enumerate(options[:3]):
        c, bg, border = CMP_PALETTES[i % len(CMP_PALETTES)]
        rows = ""
        for label, key in [("✈️ Flight", "flight"), ("🏨 Hotel", "hotel"),
                           ("🌤️ Weather","weather"), ("💰 Budget","budget_estimate"),
                           ("👥 Best for","best_for")]:
            val = opt.get(key,"")
            if val: rows += (f'<div class="cmp-row"><span class="cmp-row-label">{label}</span>'
                             f'<span class="cmp-row-val">{val}</span></div>')
        highlights = opt.get("highlights",[])
        hl_html = ""
        if highlights:
            hl_html = '<div class="cmp-highlights">' + \
                      "".join(f'<div class="cmp-hl-item">{h}</div>' for h in highlights[:4]) + \
                      '</div>'
        verdict = opt.get("verdict","")
        verdict_html = f'<div class="cmp-verdict">✓ {verdict}</div>' if verdict else ""
        cards += (f'<div class="cmp-card" style="border-color:{border};">'
                  f'<div class="cmp-head" style="background:{bg};color:{c};">'
                  f'{opt.get("name","")}'
                  f'<div class="cmp-tag">{opt.get("tagline","")}</div></div>'
                  f'<div class="cmp-body">{rows}{hl_html}{verdict_html}</div></div>')
    rec = data.get("recommendation","")
    rec_html = f'<div class="cmp-rec">"{rec}"</div>' if rec else ""
    title = data.get("title","")
    title_html = (f'<div style="font-size:.82rem;font-weight:700;color:#5a7272;'
                  f'letter-spacing:.06em;text-transform:uppercase;margin:6px 0 8px;">'
                  f'{title}</div>') if title else ""
    return f'{title_html}<div class="cmp-grid {cls}">{cards}</div>{rec_html}'


# ── Main renderer ─────────────────────────────────────────────────────────────
def render_ai_response(raw: str):
    data = _parse_response(raw)
    kind = data.get("type","text")

    if kind == "trip_plan":
        parts = []
        title = data.get("title","")
        if title:
            parts.append(f'<div style="font-size:1.15rem;font-weight:800;color:#1a2e2e;margin:4px 0 10px;">{title}</div>')
        parts += [_html_overview(data), _html_flight(data), _html_hotel(data),
                  _html_weather(data), _html_budget(data),
                  _html_days(data), _html_packing(data), _html_recommendation(data)]
        st.markdown("".join(p for p in parts if p), unsafe_allow_html=True)

    elif kind == "comparison":
        st.markdown(_html_comparison(data), unsafe_allow_html=True)

    else:
        # type: text — render markdown
        content = data.get("content", raw)
        st.markdown(f'<div class="md-body">{_md(content)}</div>', unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📓 Travel Profile")
    try:
        with open("memory/AGENTS.md") as f:
            profile_text = f.read()
        edited = st.text_area("", value=profile_text, height=320, label_visibility="collapsed")
        if st.button("💾 Save Profile", use_container_width=True):
            with open("memory/AGENTS.md","w") as f:
                f.write(edited)
            st.success("Saved!")
    except FileNotFoundError:
        st.caption("No profile at memory/AGENTS.md")
    st.divider()
    if st.button("🗑️ New Conversation", use_container_width=True):
        for k in ["thread_id","messages"]:
            st.session_state.pop(k, None)
        st.rerun()


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="hero-title">✈️ TripMind</div>'
    '<p class="hero-sub">Multi-agent AI travel planner — flights · hotels · weather · itinerary · packing</p>',
    unsafe_allow_html=True,
)

# ── Session state ─────────────────────────────────────────────────────────────
if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {
            "role": "assistant",
            "content": json.dumps({
                "type": "text",
                "content": (
                    "Hi! I'm **TripMind**, your multi-agent AI trip planner. 👋\n\n"
                    "I coordinate a team of specialized agents — flights, hotels, weather, "
                    "itinerary, and packing — so you get a complete travel plan in one go.\n\n"
                    "Try:\n"
                    "- *\"Plan a 4-day trip from Pune to Goa in August for 2 people, budget ₹60,000\"*\n"
                    "- *\"Compare Manali vs Ladakh for a long weekend in September\"*\n"
                    "- *\"Beach trip next month, ₹80,000 budget\"*"
                ),
            }),
        }
    ]

# ── Conversation ──────────────────────────────────────────────────────────────
for msg in st.session_state["messages"]:
    if msg["role"] == "user":
        st.markdown(
            f'<div class="user-row"><div class="user-bubble">{msg["content"]}</div></div>',
            unsafe_allow_html=True,
        )
    else:
        render_ai_response(msg["content"])

# ── Chat input ────────────────────────────────────────────────────────────────
if prompt := st.chat_input("Where would you like to go?"):
    st.session_state["messages"].append({"role": "user", "content": prompt})
    st.markdown(
        f'<div class="user-row"><div class="user-bubble">{prompt}</div></div>',
        unsafe_allow_html=True,
    )
    with st.spinner("Agents working…"):
        reply = chat_invoke(prompt, thread_id=st.session_state["thread_id"])
    render_ai_response(reply)
    st.session_state["messages"].append({"role": "assistant", "content": reply})
