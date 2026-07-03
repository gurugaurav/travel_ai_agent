from pathlib import Path

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend

from agents.tools import search_flights, search_hotels, compute_budget, rank_destinations

ROOT = Path(__file__).resolve().parent.parent

MODEL = ChatOpenAI(model="gpt-5.4-nano")

SYSTEM_PROMPT = """You are TripMind, a friendly AI travel planning assistant.

Your job is to help users plan trips through natural conversation, then searching for real flights and hotels to recommend the best destination.

## Collecting information

Only ask for information that is genuinely missing from both the user's message AND memory.
Ask one or two questions at a time — never a checklist. Acknowledge what you already know.

Fields needed before searching:
  - origin — use Home city from memory if present
  - destinations — if one, plan it directly; if more than one, compare them
  - travel_date and return_date — always ask if not provided
  - budget (total INR)
  - travelers — use default from memory if present

Example: if memory says Home city=Pune and Default travelers=2, and user says
"I want to go to Goa in August", respond with:
"Got it — Goa sounds great! Flying from Pune with 2 travelers as usual?
Also, what are your travel and return dates in August, and what's your total budget?"

Never re-ask for info already given or already in memory. Never use the word "memory" in chat.

When the user corrects or reveals a lasting preference (home city, traveler count, budget
style, etc.), call `edit_file` on `memory/AGENTS.md` IMMEDIATELY — before replying or
asking the next question. Do not say "I'll update" and defer it; write the file first.

## Running the search

Once you have all required fields, say something like:
"Great, I have everything I need — searching now! This takes about 30 seconds..."

Then for EACH destination (in parallel if possible):
1. Call `search_flights` — pass origin, destination, travel_date, return_date, travelers
2. Call `search_hotels` — pass city, checkin_date, checkout_date, budget_per_night (~30% of budget ÷ nights), duration_days.
   Also pass `search_term` when the user's request implies a hotel style or preference:
   - "luxury trip" / "5-star" → search_term="luxury"
   - "beach trip" / "beach facing" / "sea view" → search_term="beach facing"
   - "budget trip" / "cheap" → search_term="budget"
   - "near airport" → search_term="near airport"
   - "resort" → search_term="resort"
   - Any other explicit hotel preference → pass it as search_term
3. Call `compute_budget` — pass round-trip flight total, hotel total, travelers, duration_days

Then call `rank_destinations` once with all candidates.

## Presenting results

Format results as clean markdown. For each destination show:
- Score and whether it fits the budget (✅ / ⚠️)
- Best flight option (airline, times, price per person)
- Best hotel (name, rating, price/night)
- Full budget breakdown
- Why it ranked as it did

End with a clear recommendation: "🏆 I recommend **Goa** because..."

## Follow-ups

After showing results, invite follow-up questions:
- Budget changes ("what if I had ₹60,000?")
- Date changes, adding more destinations
- Generating an itinerary or packing list (use the `itinerary` or `packing` skills)
- Any travel question about the destinations

Use the User Memory section (if present) to personalize — mention relevant preferences.
"""

# InMemorySaver keeps conversation history for the process lifetime.
# Each Streamlit session gets its own thread_id so conversations stay separate.
_checkpointer = InMemorySaver()

agent = create_deep_agent(
    model=MODEL,
    system_prompt=SYSTEM_PROMPT,
    tools=[search_flights, search_hotels, compute_budget, rank_destinations],
    memory=["memory/AGENTS.md"],
    skills=["skills/"],
    checkpointer=_checkpointer,
    backend=FilesystemBackend(root_dir=ROOT, virtual_mode=True),
)


def _extract_trip_data(messages: list) -> dict | None:
    """Scan tool messages to reconstruct structured trip data for card rendering."""
    import json as _json

    ranked = None
    hotels: dict[str, dict] = {}  # city_lower → search_hotels result
    flights: dict[str, dict] = {}  # dest_lower → search_flights result (keyed by all words in dest)

    for msg in messages:
        if getattr(msg, "type", "") != "tool":
            continue
        tool_name = getattr(msg, "name", "")
        raw = msg.content
        if isinstance(raw, dict):
            content = raw
        else:
            try:
                content = _json.loads(raw)
            except Exception:
                continue

        if tool_name == "rank_destinations" and isinstance(content, list):
            ranked = content
        elif tool_name == "search_hotels" and isinstance(content, dict):
            city = content.get("city", "")
            if city:
                hotels[city.strip().lower()] = content
        elif tool_name == "search_flights" and isinstance(content, dict):
            route = content.get("route", "")
            sep = "→" if "→" in route else "->"
            if sep in route:
                dest = route.split(sep, 1)[1].strip()
                flights[dest.strip().lower()] = content

    if not ranked:
        return None

    def _fuzzy_get(lookup: dict, key: str) -> dict:
        """Case-insensitive partial-match lookup — handles 'North Goa' vs 'Goa'."""
        k = key.strip().lower()
        if k in lookup:
            return lookup[k]
        for stored_key, val in lookup.items():
            if k in stored_key or stored_key in k:
                return val
        return {}

    destinations = []
    for r in ranked:
        dest = r["destination"]
        hotel_data = _fuzzy_get(hotels, dest)
        flight_data = _fuzzy_get(flights, dest)
        top_hotel = (hotel_data.get("options") or [{}])[0]
        ob = (flight_data.get("outbound") or [{}])[0]
        rb = (flight_data.get("return") or [{}])[0]
        rt_total = ob.get("total_price_inr", 0) + rb.get("total_price_inr", 0)
        destinations.append({
            "destination": dest,
            "score": r["score"],
            "budget": r["budget"],
            "reasoning": r["recommendation_reasoning"],
            "hotel": top_hotel,
            "outbound": ob,
            "returns": rb,
            "round_trip_total": rt_total,
        })

    return {
        "recommended": ranked[0]["destination"],
        "destinations": destinations,
    }


def chat_invoke(message: str, thread_id: str) -> tuple[str, dict | None]:
    """Send one message and return (reply_text, trip_data).

    trip_data is None for conversational turns; populated when the agent
    runs a full trip search so the UI can render destination cards.
    """
    result = agent.invoke(
        {"messages": [{"role": "user", "content": message}]},
        config={"configurable": {"thread_id": thread_id}},
    )
    messages = result.get("messages", [])

    reply = "Sorry, I couldn't generate a response."
    for msg in reversed(messages):
        content = getattr(msg, "content", "")
        role = getattr(msg, "type", "") or getattr(msg, "role", "")
        if isinstance(content, str) and content.strip() and role in ("ai", "assistant"):
            reply = content.strip()
            break

    trip_data = _extract_trip_data(messages)
    return reply, trip_data
