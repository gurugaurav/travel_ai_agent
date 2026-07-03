"""TripMind — Chat UI."""

from dotenv import load_dotenv
load_dotenv()

# import tracing
# tracing.init_tracing(project_name="tripmind-ui")

import uuid

import streamlit as st
from main import chat_invoke

st.set_page_config(
    page_title="TripMind",
    page_icon="✈️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.block-container { max-width: 860px; padding: 0 1rem 1rem; }
.hero-title {
    font-size: clamp(1.6rem, 5vw, 2.2rem);
    font-weight: 800;
    background: linear-gradient(135deg, #0369a1, #0ea5e9, #6366f1);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0;
    line-height: 1.2;
}
.hero-sub { color: #64748b; font-size: 0.9rem; margin: 0.2rem 0 0; }

/* Trip cards */
.cards-row {
    display: flex;
    gap: 14px;
    flex-wrap: wrap;
    margin: 12px 0 4px;
}
.trip-card {
    flex: 1 1 200px;
    min-width: 180px;
    background: #ffffff;
    border: 1.5px solid #e2e8f0;
    border-radius: 14px;
    padding: 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    position: relative;
    transition: box-shadow 0.2s;
}
.trip-card.recommended {
    border-color: #0ea5e9;
    box-shadow: 0 4px 16px rgba(14,165,233,0.18);
}
.rec-badge {
    position: absolute;
    top: -11px;
    left: 50%;
    transform: translateX(-50%);
    background: linear-gradient(90deg, #0369a1, #0ea5e9);
    color: #fff;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    padding: 3px 10px;
    border-radius: 20px;
    white-space: nowrap;
}
.card-city {
    font-size: 1.2rem;
    font-weight: 800;
    color: #0f172a;
    margin: 4px 0 8px;
    text-align: center;
}
.score-bar-wrap { margin: 0 0 10px; }
.score-label {
    display: flex;
    justify-content: space-between;
    font-size: 0.72rem;
    color: #64748b;
    margin-bottom: 3px;
}
.score-bar {
    height: 6px;
    background: #e2e8f0;
    border-radius: 99px;
    overflow: hidden;
}
.score-fill {
    height: 100%;
    border-radius: 99px;
    background: linear-gradient(90deg, #0ea5e9, #6366f1);
}
.card-row {
    display: flex;
    align-items: flex-start;
    gap: 6px;
    font-size: 0.78rem;
    color: #334155;
    margin-bottom: 5px;
}
.card-icon { font-size: 0.9rem; flex-shrink: 0; }
.card-label { color: #94a3b8; font-size: 0.68rem; display: block; line-height: 1; }
.card-val { font-weight: 600; color: #1e293b; line-height: 1.3; }
.budget-total {
    margin-top: 10px;
    text-align: center;
    font-size: 1.05rem;
    font-weight: 800;
    color: #0369a1;
}
.budget-ok { color: #16a34a; }
.budget-over { color: #dc2626; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    if st.button("🗑️ New Conversation", use_container_width=True):
        for key in ["thread_id", "messages", "trip_data"]:
            st.session_state.pop(key, None)
        st.rerun()

# ── Header ──────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="hero-title">✈️ TripMind</div>'
    '<p class="hero-sub">Chat to plan your trip — I\'ll ask if I need more details</p>',
    unsafe_allow_html=True,
)
st.markdown("")

# ── Session state ────────────────────────────────────────────────────────────
if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {
            "role": "assistant",
            "content": (
                "Hi! I'm TripMind, your agentic AI trip planner. 👋\n\n"
                "Tell me where you'd like to go and I'll compare destinations, find real flights & hotels, "
                "and recommend the best option for your budget.\n\n"
                "You can start with something like:\n"
                "- *\"Plan a trip from Pune to Goa or Kerala in August\"*\n"
                "- *\"I want a 4-day beach trip for 2 people with a ₹40,000 budget\"*\n"
                "- *\"Compare Manali vs Ladakh for a long weekend\"*"
            ),
        }
    ]


_CARD_STYLE = """
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Inter,system-ui,sans-serif;background:transparent}
.cards-row{display:flex;gap:14px;flex-wrap:wrap;padding:4px 0 8px}
.trip-card{flex:1 1 210px;min-width:195px;background:#fff;border:1.5px solid #e2e8f0;border-radius:16px;padding:18px 16px 14px;box-shadow:0 2px 10px rgba(0,0,0,.07);position:relative}
.trip-card.recommended{border-color:#0ea5e9;box-shadow:0 4px 18px rgba(14,165,233,.2)}
.rec-badge{position:absolute;top:-12px;left:50%;transform:translateX(-50%);background:linear-gradient(90deg,#0369a1,#0ea5e9);color:#fff;font-size:.62rem;font-weight:700;letter-spacing:.07em;padding:3px 12px;border-radius:20px;white-space:nowrap}
.card-city{font-size:1.15rem;font-weight:800;color:#0f172a;text-align:center;margin:2px 0 12px}

/* Overall score */
.overall-score{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px}
.overall-label{font-size:.7rem;color:#64748b;font-weight:500}
.overall-val{font-size:.85rem;font-weight:800;color:#0369a1}
.score-bar{height:7px;background:#e2e8f0;border-radius:99px;overflow:hidden;margin-bottom:12px}
.score-fill{height:100%;border-radius:99px;background:linear-gradient(90deg,#0ea5e9,#6366f1)}

/* Factor rows */
.factors{border-top:1px solid #f1f5f9;padding-top:10px;margin-bottom:10px}
.factor-row{margin-bottom:8px}
.factor-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:3px}
.factor-name{font-size:.68rem;color:#64748b;font-weight:500}
.factor-score{font-size:.68rem;font-weight:700;color:#334155}
.factor-bar{height:4px;background:#f1f5f9;border-radius:99px;overflow:hidden}
.fb-budget{background:linear-gradient(90deg,#16a34a,#4ade80)}
.fb-experience{background:linear-gradient(90deg,#f59e0b,#fbbf24)}
.fb-weather{background:linear-gradient(90deg,#0ea5e9,#38bdf8)}
.fb-access{background:linear-gradient(90deg,#8b5cf6,#a78bfa)}

/* Detail rows */
.details{border-top:1px solid #f1f5f9;padding-top:10px}
.detail-row{display:flex;gap:6px;align-items:flex-start;margin-bottom:6px}
.d-icon{font-size:.85rem;flex-shrink:0;margin-top:1px}
.d-body{}
.d-label{font-size:.62rem;color:#94a3b8;display:block;line-height:1;margin-bottom:1px}
.d-val{font-size:.75rem;font-weight:600;color:#1e293b;line-height:1.4}
.d-val.dim{color:#94a3b8;font-weight:400}

/* Budget footer */
.budget-footer{margin-top:10px;text-align:center;font-size:1rem;font-weight:800}
.budget-ok{color:#16a34a}.budget-over{color:#dc2626}
</style>
"""


def _bar(pct: float, cls: str) -> str:
    p = min(100, max(0, pct))
    return f'<div class="factor-bar"><div class="{cls}" style="width:{p}%;height:100%"></div></div>'


def _render_trip_cards(trip_data: dict) -> str:
    recommended = trip_data["recommended"]
    cards_html = _CARD_STYLE + '<div class="cards-row">'

    for d in trip_data["destinations"]:
        dest = d["destination"]
        is_rec = dest.lower() == recommended.lower()
        score = d["score"]
        reasoning = d.get("reasoning", {})
        budget_fit   = reasoning.get("budget_fit", 0)
        experience   = reasoning.get("experience_score", 0)
        weather      = reasoning.get("weather_score", 0)
        accessibility = reasoning.get("accessibility", 0)

        budget_info = d["budget"]
        fits  = budget_info.get("fits_budget", True)
        total = budget_info.get("total", 0)
        overage = budget_info.get("overage_pct", 0)

        hotel = d.get("hotel", {})
        ob    = d.get("outbound", {})
        rb    = d.get("returns", {})

        hotel_name  = hotel.get("hotel_name", "")
        hotel_price = hotel.get("price_per_night_inr", 0)
        hotel_rating = hotel.get("rating", "")
        ob_airline  = ob.get("airline", "")
        ob_price    = ob.get("total_price_inr", 0)
        rb_airline  = rb.get("airline", "")
        rb_price    = rb.get("total_price_inr", 0)

        card_cls = "trip-card recommended" if is_rec else "trip-card"
        badge    = '<div class="rec-badge">⭐ RECOMMENDED</div>' if is_rec else ""

        # Flight detail
        if ob_airline and ob_price:
            flight_out  = f"{ob_airline} ₹{ob_price:,}"
            flight_ret  = f"{rb_airline} ₹{rb_price:,}" if (rb_airline and rb_price) else "—"
            flight_html = f'{flight_out}<br><span style="color:#94a3b8;font-size:.68rem">↩ {flight_ret}</span>'
        else:
            flight_html = '<span class="dim">Bus / Train recommended</span>'

        # Hotel detail
        if hotel_name:
            rating_str  = f" ★{hotel_rating}" if hotel_rating else ""
            price_str   = f" · ₹{hotel_price:,}/night" if hotel_price else ""
            hotel_html  = f"{hotel_name}{rating_str}{price_str}"
        else:
            hotel_html  = '<span class="dim">—</span>'

        # Budget footer
        budget_cls  = "budget-ok" if fits else "budget-over"
        budget_icon = "✅" if fits else "⚠️"
        over_str    = f" (+{overage}%)" if not fits and overage else ""

        cards_html += f"""
        <div class="{card_cls}">
            {badge}
            <div class="card-city">{dest}</div>

            <div class="overall-score">
                <span class="overall-label">Overall match</span>
                <span class="overall-val">{score}/100</span>
            </div>
            <div class="score-bar"><div class="score-fill" style="width:{score}%"></div></div>

            <div class="factors">
                <div class="factor-row">
                    <div class="factor-header">
                        <span class="factor-name">💰 Budget fit</span>
                        <span class="factor-score">{budget_fit:.0f}/100</span>
                    </div>
                    {_bar(budget_fit, "fb-budget")}
                </div>
                <div class="factor-row">
                    <div class="factor-header">
                        <span class="factor-name">🎉 Experience</span>
                        <span class="factor-score">{experience:.0f}/100</span>
                    </div>
                    {_bar(experience, "fb-experience")}
                </div>
                <div class="factor-row">
                    <div class="factor-header">
                        <span class="factor-name">🌤️ Weather</span>
                        <span class="factor-score">{weather:.0f}/100</span>
                    </div>
                    {_bar(weather, "fb-weather")}
                </div>
                <div class="factor-row">
                    <div class="factor-header">
                        <span class="factor-name">🚀 Accessibility</span>
                        <span class="factor-score">{accessibility:.0f}/100</span>
                    </div>
                    {_bar(accessibility, "fb-access")}
                </div>
            </div>

            <div class="details">
                <div class="detail-row">
                    <span class="d-icon">✈️</span>
                    <div class="d-body">
                        <span class="d-label">Flights (round trip)</span>
                        <span class="d-val">{flight_html}</span>
                    </div>
                </div>
                <div class="detail-row">
                    <span class="d-icon">🏨</span>
                    <div class="d-body">
                        <span class="d-label">Best hotel</span>
                        <span class="d-val">{hotel_html}</span>
                    </div>
                </div>
            </div>

            <div class="budget-footer {budget_cls}">{budget_icon} ₹{total:,} total{over_str}</div>
        </div>
        """

    cards_html += "</div>"
    return cards_html


# ── Render conversation ──────────────────────────────────────────────────────
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"], avatar="✈️" if msg["role"] == "assistant" else None):
        st.markdown(msg["content"])
        if msg.get("trip_data"):
            st.html(_render_trip_cards(msg["trip_data"]))

# ── Chat input ───────────────────────────────────────────────────────────────
if prompt := st.chat_input("Where would you like to go?"):
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="✈️"):
        with st.spinner("Thinking…"):
            reply, trip_data = chat_invoke(prompt, thread_id=st.session_state["thread_id"])
        st.markdown(reply)
        if trip_data:
            st.html(_render_trip_cards(trip_data))

    st.session_state["messages"].append({
        "role": "assistant",
        "content": reply,
        "trip_data": trip_data,
    })
