"""Planning Agent — pure reasoning, no external APIs.

Allocates budget across categories, determines hotel tier, selects cities
(if multiple options), and produces structured search requirements (Trip Context).
"""

import json
import os
from langchain_openai import ChatOpenAI

_llm: "ChatOpenAI | None" = None


def _get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model=os.environ.get("REASONING_MODEL", "gpt-4.1"),
            temperature=0.2,
        )
    return _llm


def plan_trip(
    destination: str,
    origin: str,
    travel_date: str,
    return_date: str,
    budget_total: int,
    travelers: int = 1,
    currency: str = "INR",
    user_preferences: str = "",
    destination_alternatives: str = "",
) -> str:
    """Planning Agent: Allocate budget, determine hotel category, produce Trip Context.

    Pure reasoning agent — does not call any external APIs. Takes the user's
    trip request and produces a structured Trip Context JSON that guides all
    downstream agents (Flight, Hotel, Itinerary, Weather, Packing).

    Args:
        destination: Primary destination city (e.g. "Goa").
        origin: Departure city (e.g. "Pune").
        travel_date: Departure date in YYYY-MM-DD or human-readable format.
        return_date: Return date.
        budget_total: Total trip budget in the specified currency.
        travelers: Number of travelers.
        currency: Currency (default INR).
        user_preferences: Relevant user preferences from memory (seat, hotel rating,
            dietary, activity likes/dislikes, packing style, etc.).
        destination_alternatives: Comma-separated alternative destinations to compare,
            if the user wants to compare multiple cities.

    Returns:
        JSON string — the Trip Context with sections: trip, budget, search_requirements,
        hotel_category, and planning_notes.
    """
    print(f"\n🧠  plan_trip | {origin} → {destination} | {travel_date}→{return_date} | "
          f"₹{budget_total:,} for {travelers} traveler(s)")

    alts_section = ""
    if destination_alternatives:
        alts_section = f"\nAlternative destinations to compare: {destination_alternatives}"

    prompt = f"""You are the Planning Agent for a multi-agent travel planning system.

User's trip request:
- Origin: {origin}
- Destination: {destination}{alts_section}
- Travel date: {travel_date}
- Return date: {return_date}
- Total budget: {budget_total:,} {currency}
- Travelers: {travelers}
- User preferences: {user_preferences or "none specified"}

Your job: Produce a structured Trip Context JSON that guides the Flight, Hotel,
Itinerary, Weather, and Packing agents.

Calculate the trip duration from travel_date to return_date.

Budget allocation guidelines (adjust for travelers and duration):
- Flights: 30–40% of total budget (round-trip, all travelers)
- Hotel: 25–35% of total budget (total stay)
- Activities & sightseeing: 15–20%
- Food & dining: 10–15%
- Local transport: 5–8%
- Miscellaneous/buffer: 5–10%

Hotel category tiers (per night, {currency}):
- Budget (1–2 star): < 2,000/night
- Economy (3 star): 2,000–4,000/night
- Mid-range (3–4 star): 4,000–7,000/night
- Comfort (4 star): 7,000–12,000/night
- Luxury (5 star): > 12,000/night

Output ONLY a valid JSON object with this exact structure:
{{
  "trip": {{
    "origin": "...",
    "destination": "...",
    "travel_date": "YYYY-MM-DD",
    "return_date": "YYYY-MM-DD",
    "duration_days": <int>,
    "travelers": <int>,
    "currency": "..."
  }},
  "budget": {{
    "total": <int>,
    "flights_allocation": <int>,
    "hotel_allocation": <int>,
    "hotel_per_night": <int>,
    "activities_allocation": <int>,
    "food_allocation": <int>,
    "transport_allocation": <int>,
    "misc_allocation": <int>,
    "daily_spending_budget": <int>
  }},
  "hotel_category": "...",
  "search_requirements": {{
    "flight_search_term": "...",
    "hotel_search_term": "...",
    "max_flight_price_inr": <int>,
    "max_hotel_per_night_inr": <int>
  }},
  "planning_notes": "Brief reasoning about budget choices and any trade-offs."
}}

Be precise with numbers. Ensure allocations sum to the total budget.
Return ONLY the JSON, no markdown fences, no extra text."""

    response = _get_llm().invoke(prompt)
    raw = response.content.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    # Validate it's valid JSON
    try:
        parsed = json.loads(raw)
        print(f"   → {parsed['trip']['duration_days']}d | hotel ₹{parsed['budget']['hotel_per_night']:,}/night "
              f"({parsed['hotel_category']}) | flights budget ₹{parsed['budget']['flights_allocation']:,}")
        return json.dumps(parsed, ensure_ascii=False)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"   ⚠️  Planning output parse error: {e}")
        return raw
