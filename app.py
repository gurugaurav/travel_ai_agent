"""TripMind — Multi-Agent Travel Planning UI."""

from dotenv import load_dotenv
load_dotenv()

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
</style>
""", unsafe_allow_html=True)

_CARD_STYLE = """
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Inter,system-ui,sans-serif;background:transparent}
.trip-summary{background:#fff;border:1.5px solid #e2e8f0;border-radius:16px;padding:20px;box-shadow:0 2px 10px rgba(0,0,0,.07);margin:8px 0}
.ts-title{font-size:1.1rem;font-weight:800;color:#0f172a;margin-bottom:14px;display:flex;align-items:center;gap:8px}
.ts-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.ts-block{background:#f8fafc;border-radius:10px;padding:12px}
.ts-label{font-size:.65rem;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px}
.ts-val{font-size:.85rem;font-weight:700;color:#1e293b;line-height:1.4}
.ts-sub{font-size:.72rem;color:#64748b;margin-top:2px}
.budget-table{width:100%;border-collapse:collapse;margin-top:12px;font-size:.8rem}
.budget-table th{text-align:left;padding:6px 8px;background:#f1f5f9;color:#64748b;font-weight:600;font-size:.68rem;text-transform:uppercase}
.budget-table td{padding:6px 8px;border-bottom:1px solid #f1f5f9;color:#334155}
.budget-table tr:last-child td{border-bottom:none;font-weight:700;color:#0369a1}
</style>
"""


def _fmt_inr(amount) -> str:
    if not amount:
        return "—"
    try:
        return f"₹{int(amount):,}"
    except (TypeError, ValueError):
        return str(amount)


def _render_trip_summary(trip_data: dict) -> str:
    dest = trip_data.get("destination", "")
    ob = trip_data.get("outbound", {})
    rb = trip_data.get("returns", {})
    hotel = trip_data.get("hotel", {})
    budget = trip_data.get("budget", {})
    plan = trip_data.get("plan", {})
    trip_info = plan.get("trip", {}) if isinstance(plan, dict) else {}

    duration = trip_info.get("duration_days", "")
    travelers = trip_info.get("travelers", "")

    # Flight row
    ob_text = f"{ob.get('airline','—')} · {ob.get('departure_time','—')}→{ob.get('arrival_time','—')} · {_fmt_inr(ob.get('total_price_inr'))} · {'Direct' if ob.get('direct') else str(ob.get('stops',0))+' stop'}" if ob else "—"
    rb_text = f"{rb.get('airline','—')} · {rb.get('departure_time','—')}→{rb.get('arrival_time','—')} · {_fmt_inr(rb.get('total_price_inr'))}" if rb else "—"

    # Hotel row
    hotel_name = hotel.get("hotel_name", "—")
    hotel_rating = f"★{hotel.get('rating','')}" if hotel.get("rating") else ""
    hotel_price = _fmt_inr(hotel.get("price_per_night_inr"))
    hotel_total = _fmt_inr(hotel.get("total_cost_inr"))

    # Budget table
    budget_rows = ""
    labels = [
        ("Flights", "flights_allocation"),
        ("Hotel", "hotel_allocation"),
        ("Activities", "activities_allocation"),
        ("Food & Dining", "food_allocation"),
        ("Local Transport", "transport_allocation"),
        ("Misc / Buffer", "misc_allocation"),
    ]
    for label, key in labels:
        val = budget.get(key)
        if val:
            budget_rows += f"<tr><td>{label}</td><td style='text-align:right'>{_fmt_inr(val)}</td></tr>"

    total = budget.get("total")
    if total:
        budget_rows += f"<tr><td><strong>Total</strong></td><td style='text-align:right'><strong>{_fmt_inr(total)}</strong></td></tr>"

    budget_section = ""
    if budget_rows:
        budget_section = f"""
        <table class="budget-table">
            <thead><tr><th>Category</th><th style="text-align:right">Amount</th></tr></thead>
            <tbody>{budget_rows}</tbody>
        </table>"""

    html = _CARD_STYLE + f"""
    <div class="trip-summary">
        <div class="ts-title">✈️ {dest} {f"· {duration} days" if duration else ""} {f"· {travelers} traveler(s)" if travelers else ""}</div>
        <div class="ts-grid">
            <div class="ts-block">
                <div class="ts-label">Outbound Flight</div>
                <div class="ts-val">{ob_text}</div>
            </div>
            <div class="ts-block">
                <div class="ts-label">Return Flight</div>
                <div class="ts-val">{rb_text}</div>
            </div>
            <div class="ts-block">
                <div class="ts-label">Hotel</div>
                <div class="ts-val">{hotel_name} {hotel_rating}</div>
                <div class="ts-sub">{hotel_price}/night · {hotel_total} total</div>
            </div>
            <div class="ts-block">
                <div class="ts-label">Daily Budget / Person</div>
                <div class="ts-val">{_fmt_inr(budget.get("daily_spending_budget"))}</div>
                <div class="ts-sub">activities + food + transport</div>
            </div>
        </div>
        {budget_section}
    </div>
    """
    return html


with st.sidebar:
    if st.button("🗑️ New Conversation", use_container_width=True):
        for key in ["thread_id", "messages"]:
            st.session_state.pop(key, None)
        st.rerun()

st.markdown(
    '<div class="hero-title">✈️ TripMind</div>'
    '<p class="hero-sub">Multi-agent AI travel planner — flights, hotels, itinerary & packing in one conversation</p>',
    unsafe_allow_html=True,
)
st.markdown("")

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {
            "role": "assistant",
            "content": (
                "Hi! I'm TripMind, your multi-agent AI trip planner. 👋\n\n"
                "I coordinate a team of specialized agents — for flights, hotels, weather, "
                "itinerary, and packing — so you get a complete travel plan in one conversation.\n\n"
                "Try:\n"
                "- *\"Plan a 4-day trip from Pune to Goa in August for 2 people, budget ₹60,000\"*\n"
                "- *\"Compare Manali vs Ladakh for a long weekend in September\"*\n"
                "- *\"I want a beach trip next month, budget ₹80,000\"*"
            ),
        }
    ]

for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"], avatar="✈️" if msg["role"] == "assistant" else None):
        st.markdown(msg["content"])
        if msg.get("trip_data"):
            st.html(_render_trip_summary(msg["trip_data"]))

if prompt := st.chat_input("Where would you like to go?"):
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="✈️"):
        with st.spinner("Agents working…"):
            reply, trip_data = chat_invoke(prompt, thread_id=st.session_state["thread_id"])
        st.markdown(reply)
        if trip_data:
            st.html(_render_trip_summary(trip_data))

    st.session_state["messages"].append({
        "role": "assistant",
        "content": reply,
        "trip_data": trip_data,
    })
