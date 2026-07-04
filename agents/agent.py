"""TripMind Supervisor — multi-agent travel planning orchestrator.

Architecture:
  Main supervisor → delegates to 4 specialized subagents:
    - flight-agent   : searches real flights (SerpAPI Google Flights)
    - hotel-agent    : searches real hotels (Google Hotels via fast_hotels)
    - weather-agent  : fetches weather forecasts (Open-Meteo)
    - itinerary-agent: builds day-by-day plan from flight + hotel + weather context
  Supervisor directly calls plan_trip (pure reasoning, no external API).
"""

from pathlib import Path

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend

from tools import (
    plan_trip,
    get_airport_code,
    search_flights,
    search_hotels,
    get_weather_forecast,
    create_itinerary,
    create_packing_list,
)

ROOT = Path(__file__).resolve().parent.parent

MODEL = ChatOpenAI(model="gpt-4.1")


# ── Subagents ─────────────────────────────────────────────────────────────────

flight_subagent = {
    "name": "flight-agent",
    "description": (
        "Searches for real flights using Google Flights data (SerpAPI). "
        "Call once per leg — outbound and return are separate calls to search_flights. "
        "Provide origin city, destination city, date, and number of travelers. "
        "For cities with multiple airports, searches all of them and returns the best options."
    ),
    "system_prompt": (
        "You are the Flight Search Agent for TripMind.\n\n"
        "Step 1: call get_airport_code for origin and destination to get search results.\n"
        "Step 2: read the results and pick all IATA code(s) for each city.\n"
        "Step 3: call search_flights with those codes.\n\n"
        "If a city has more than 1 airport, check all of them. and return all results.\n"
        "If a city has no airport or no flight, check whether there is an alternate nearby airport code in the search results and retry.\n\n"
        "Return the full dict from search_flights without summarising or omitting any data."
    ),
    "tools": [get_airport_code, search_flights],
}

hotel_subagent = {
    "name": "hotel-agent",
    "description": (
        "Searches for real hotels using Google Hotels data. "
        "Provide city, checkin_date, checkout_date, budget_per_night, duration_days, "
        "and optionally search_term (e.g. 'beach facing', 'pool, breakfast included')."
    ),
    "system_prompt": (
        "You are the Hotel Search Agent for TripMind. "
        "Your only job is to call search_hotels with the parameters the supervisor gives you "
        "and return the raw result. "
        "Return the full dict including all options without summarising or omitting data."
    ),
    "tools": [search_hotels],
}

weather_subagent = {
    "name": "weather-agent",
    "description": (
        "Fetches weather forecasts or historical climate estimates for a destination. "
        "Provide destination, start_date, and end_date. "
        "Automatically uses historical archive data for dates beyond 16 days."
    ),
    "system_prompt": (
        "You are the Weather Agent for TripMind. "
        "Your only job is to call get_weather_forecast with the parameters given "
        "and return the raw result including daily_forecast, summary, "
        "clothing_recommendation, and activity_suggestion. "
        "Return the full dict without summarising or omitting data."
    ),
    "tools": [get_weather_forecast],
}

itinerary_subagent = {
    "name": "itinerary-agent",
    "description": (
        "Creates a detailed day-by-day travel itinerary and packing list. "
        "Call this AFTER you have flight, hotel, and weather data. "
        "Pass the full context — destination, dates, duration, "
        "outbound_arrival_time (HH:MM from flight result), "
        "return_departure_time (HH:MM from flight result), "
        "airport_to_hotel_transfer_mins, airport_to_hotel_transfer_mins_last_day, "
        "hotel_name, hotel_area, daily_budget_inr, weather_summary, "
        "interests (from user/memory), travelers, and multi_city_route if applicable. "
        "Also pass planned_activities (brief comma-separated list of activities) "
        "so the packing list can be tailored correctly."
    ),
    "system_prompt": (
        "You are the Itinerary Planning Agent for TripMind. "
        "You receive the complete trip context (flight details, hotel details, weather data) "
        "from the supervisor and build a polished day-by-day itinerary plus packing list. "
        "\n\n"
        "Rules:\n"
        "- Day 1 starts from the flight arrival time (not before).\n"
        "- Last day ends at checkout and accounts for airport transfer time.\n"
        "- Use weather data to recommend indoor vs outdoor activities per day.\n"
        "- Use hotel location (city area) for realistic activity clustering.\n"
        "- Call create_itinerary first, then create_packing_list.\n"
        "- Return both outputs combined — do NOT summarise or shorten them."
    ),
    "tools": [create_itinerary, create_packing_list],
}


# ── System Prompt ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are TripMind, an intelligent multi-agent travel planning assistant.
You are the Supervisor — the ONLY agent that talks directly to the user.

## Your Architecture
You coordinate 4 specialized subagents plus a direct planning tool:
- **plan_trip** (your own tool) → pure reasoning, allocates budget, produces Trip Context
- **flight-agent** → searches real Google Flights data (SerpAPI)
- **hotel-agent**  → searches real Google Hotels data (fast_hotels)
- **weather-agent** → Open-Meteo API, 16-day forecast + historical archive fallback
- **itinerary-agent** → day-by-day plan built from flight + hotel + weather context

You never perform flight/hotel/weather lookups yourself — always delegate to the subagent.

## Memory
User preferences are stored in memory/AGENTS.md across 9 categories:
User Profile, Travel Preferences, Flight Preferences, Hotel Preferences,
Activity Preferences, Dietary Preferences, Packing Preferences, Budget Preferences,
Previous Trips.

Read memory at session start. Never say "memory" to the user — use it silently.
Use `edit_file` on memory/AGENTS.md IMMEDIATELY when the user reveals a lasting preference
(home city, typical budget, number of travelers, preferred seat, etc.) — do it BEFORE replying.

## Information Gathering
Fields needed before planning:
- **origin**: home city/airport → use memory if present (default: Pune)
- **destination(s)**: where they want to go (1 or multiple to compare)
- **travel_date**: departure date
- **return_date**: return date
- **budget_total**: total budget in INR → use memory default if not given
- **travelers**: number of travelers → use memory default if not given

Ask one or two questions at a time, never a checklist. Acknowledge what you already know.

## Hotel Search Rules
- ALWAYS show whatever hotels the hotel-agent returns — never say "no hotels found" if the agent returned results.
- The hotel-agent returns real Google Hotels data. Trust the data; do not apply your own filter on top.
- If options exceed budget, show them anyway and flag with ⚠️ over budget.
- Pass search_term as a short natural-language phrase (e.g. "pool beach breakfast") — not a structured filter.

## Flight Search Rules
- Always try nonstop first — the flight-agent does this automatically.
- If only connecting flights come back (stops > 0), tell the user:
  "I found only connecting flights via our data source. Direct flights may exist —
  verify on Google Flights or MakeMyTrip before booking."
- The `arrival_time` in flight results is the FINAL destination arrival (last leg).
- Show layover city/duration from the `layovers` field when relevant.

## Multi-City Trip Logic
When the user visits multiple cities (e.g. Kochi + Alleppey, Jaipur + Agra):
1. Identify the ARRIVAL airport (usually the first city).
2. Identify the DEPARTURE airport for the return:
   - Last city has airport → fly home from there.
   - Last city has NO airport (e.g. Alleppey, Agra) → nearest airport (e.g. Kochi, Delhi).
3. Tell flight-agent: origin, destination=city1, return_origin=departure_city.
4. Tell itinerary-agent the full multi_city_route string.



## Execution Flow
Once you have all required info, say:
"Perfect, I have everything I need — searching now! Give me about 30 seconds..."
Then execute in this order:
1. Call **plan_trip** directly → get Trip Context with budget allocation + hotel category.

2. Call **flight-agent**: origin, destination, dates, travelers, return_origin if multi-city
3. Based on flight price, check remaining budget and adjust hotel category if needed. You can incude this adjustment in hotel search term.   
   call these agetn parellay.
   - **hotel-agent**: city, dates, budget_per_night from Trip Context, include search term from preferences.
   - **weather-agent**: destination, start_date, end_date
3. Collect all results, then delegate to:
   - **itinerary-agent**: pass the FULL context —
       destination, dates, duration, travelers,
       flight outbound arrival_time + return departure_time,
       hotel name/location,
       weather daily_forecast + clothing_recommendation,
       budget breakdown,
       airport_to_hotel_transfer_mins (from table above),
       multi_city_route (if applicable)
    - While planning itnaries, keep transfer time in mind

## Replanning
If flights or hotels exceed budget or return no results:
- Try alternate dates (±2–3 days)
- Try a lower hotel tier (lower budget_per_night)
- Suggest trade-offs: "I can find flights for ₹X if you fly Thursday instead — want me to check?"
- Rerun the relevant subagent with adjusted parameters.

## Presenting Results
Format as clean markdown. Show:
1. **Trip Overview** — destination, dates, duration, travelers
2. **Best Flight Option** — airline, times, price per person + total
3. **Best Hotel** — name, rating, price/night, total cost
4. **Budget Breakdown** — table with all categories
5. **Weather Summary** — key conditions, clothing tip
6. **Day-by-Day Itinerary** — from itinerary-agent output
7. **Packing List** — from itinerary-agent output
8. **Final Recommendation** — "✈️ My recommendation: [destination] — [2-line reason]"

## Follow-ups
After presenting results, invite questions:
- Budget changes, date changes, destination swaps
- "Generate an itinerary for just Day 2"
- Hotel or flight alternatives

## Memory Updates
After completing a trip plan, update memory/AGENTS.md with:
- Any new permanent preferences revealed during the conversation
- Add trip to Previous Trips section if user confirmed/booked it
"""


# ── Agent ──────────────────────────────────────────────────────────────────────

_checkpointer = InMemorySaver()

agent = create_deep_agent(
    model=MODEL,
    system_prompt=SYSTEM_PROMPT,
    tools=[plan_trip],
    subagents=[flight_subagent, hotel_subagent, weather_subagent, itinerary_subagent],
    memory=["memory/AGENTS.md"],
    skills=["skills/"],
    checkpointer=_checkpointer,
    backend=FilesystemBackend(root_dir=ROOT, virtual_mode=True),
)


# ── UI helpers ─────────────────────────────────────────────────────────────────

def _extract_trip_data(messages: list) -> dict | None:
    """Scan tool messages from the current turn to extract trip data for the UI card."""
    import json as _json

    last_human_idx = -1
    for i, msg in enumerate(messages):
        role = getattr(msg, "type", "") or getattr(msg, "role", "")
        if role in ("human", "user"):
            last_human_idx = i

    current_turn = messages[last_human_idx + 1:] if last_human_idx >= 0 else messages

    hotel_data: dict = {}
    flight_data: dict = {}
    plan_data: dict = {}

    for msg in current_turn:
        if getattr(msg, "type", "") != "tool":
            continue
        tool_name = getattr(msg, "name", "")
        raw = msg.content
        try:
            content = _json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            continue

        if tool_name == "plan_trip" and isinstance(content, dict):
            plan_data = content

        elif tool_name == "search_hotels" and isinstance(content, dict):
            city = content.get("city", "unknown")
            hotel_data[city.lower()] = content

        elif tool_name == "search_flights" and isinstance(content, dict):
            route = content.get("route", "")
            for sep in ["→", "->"]:
                if sep in route:
                    dest = route.split(sep, 1)[1].strip().lower()
                    flight_data[dest] = content
                    break

    if not hotel_data and not flight_data:
        return None

    if flight_data:
        dest_key = next(iter(flight_data))
        fd = flight_data[dest_key]
        hd = hotel_data.get(dest_key) or (next(iter(hotel_data.values())) if hotel_data else {})

        ob = (fd.get("outbound") or [{}])[0]
        rb = (fd.get("return") or [{}])[0]
        top_hotel = (hd.get("options") or [{}])[0]
        budget_info = plan_data.get("budget", {})

        return {
            "destination": fd.get("route", dest_key).split("→")[-1].strip() if "→" in fd.get("route", "") else dest_key.title(),
            "outbound": ob,
            "returns": rb,
            "hotel": top_hotel,
            "budget": budget_info,
            "plan": plan_data,
        }

    return None


def chat_invoke(message: str, thread_id: str) -> tuple[str, dict | None]:
    """Send one user message and return (reply_text, trip_data)."""
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
