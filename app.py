"""TripMind — Multi-Agent Travel Planning UI."""

from dotenv import load_dotenv
load_dotenv()

import tracing
tracing.init_tracing(project_name="tripmind-ui")

import uuid
import streamlit as st
from agents.agent import chat_invoke

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
    font-size: clamp(1.6rem, 5vw, 2.2rem); font-weight: 800;
    background: linear-gradient(135deg, #0369a1, #0ea5e9, #6366f1);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text; margin: 0; line-height: 1.2;
}
.hero-sub { color: #64748b; font-size: 0.9rem; margin: 0.2rem 0 0; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    if st.button("🗑️ New Conversation", use_container_width=True):
        for key in ["thread_id", "messages"]:
            st.session_state.pop(key, None)
        st.rerun()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="hero-title">✈️ TripMind</div>'
    '<p class="hero-sub">Multi-agent AI travel planner — flights, hotels, weather, itinerary & packing</p>',
    unsafe_allow_html=True,
)
st.markdown("")

# ── Session state ─────────────────────────────────────────────────────────────
if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {
            "role": "assistant",
            "content": (
                "Hi! I'm TripMind, your multi-agent AI trip planner. 👋\n\n"
                "I coordinate a team of specialized agents — flights, hotels, weather, "
                "itinerary, and packing — so you get a complete travel plan in one go.\n\n"
                "Try:\n"
                "- *\"Plan a 4-day trip from Pune to Goa in August for 2 people, budget ₹60,000\"*\n"
                "- *\"Compare Manali vs Ladakh for a long weekend in September\"*\n"
                "- *\"Beach trip next month, ₹80,000 budget\"*"
            ),
        }
    ]

# ── Render conversation ───────────────────────────────────────────────────────
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"], avatar="✈️" if msg["role"] == "assistant" else None):
        st.markdown(msg["content"])

# ── Chat input ────────────────────────────────────────────────────────────────
if prompt := st.chat_input("Where would you like to go?"):
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="✈️"):
        with st.spinner("Agents working…"):
            reply = chat_invoke(prompt, thread_id=st.session_state["thread_id"])
        st.markdown(reply)

    st.session_state["messages"].append({"role": "assistant", "content": reply})
