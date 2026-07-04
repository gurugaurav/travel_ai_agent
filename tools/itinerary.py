"""Itinerary Agent — LLM-based day-by-day travel plan.

Uses flight times, hotel location, weather forecast, interests, and budget
to produce a detailed and realistic itinerary.
"""

import os
from langchain_openai import ChatOpenAI

_llm: "ChatOpenAI | None" = None


def _get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model=os.environ.get("REASONING_MODEL", "gpt-4.1"),
            temperature=0.4,
        )
    return _llm


def create_itinerary(
    destination: str,
    travel_date: str,
    return_date: str,
    duration_days: int,
    hotel_name: str,
    hotel_area: str,
    outbound_arrival_time: str,
    airport_to_hotel_transfer_mins: int,
    return_departure_time: str,
    airport_to_hotel_transfer_mins_last_day: int,
    daily_budget_inr: int,
    weather_summary: str,
    interests: str = "",
    dietary_preferences: str = "",
    travelers: int = 1,
    multi_city_route: str = "",
) -> str:
    """Itinerary Agent: Create a detailed day-by-day travel plan.

    Builds a realistic itinerary that accounts for actual flight arrival/departure
    times INCLUDING airport-to-hotel transfer time, weather, interests, and budget.
    Day 1 free time = arrival_time + transfer_mins. Last day must end early enough
    to reach the departure airport with at least 90 minutes to spare.

    Args:
        destination: Primary destination, e.g. "Goa" or "Kochi & Alleppey".
        travel_date: Departure date YYYY-MM-DD.
        return_date: Return date YYYY-MM-DD.
        duration_days: Trip length in days.
        hotel_name: Name of the booked hotel (first hotel for multi-city).
        hotel_area: Area/neighborhood of the hotel.
        outbound_arrival_time: Time flight LANDS at destination airport (HH:MM).
            This is the FINAL destination arrival — not a layover time.
        airport_to_hotel_transfer_mins: Estimated minutes to travel from airport
            to hotel (e.g. 30 for Goa, 45 for Kochi, 90 for Manali).
        return_departure_time: Return flight departure time (HH:MM). Travelers must
            leave the hotel early enough to reach the airport with 90 min buffer.
        airport_to_hotel_transfer_mins_last_day: Transfer time from last hotel
            to departure airport in minutes.
        daily_budget_inr: Budget per person per day (activities + food + local transport).
        weather_summary: Weather forecast summary from Weather Agent.
        interests: User interests, e.g. "beaches, nightlife, local food, markets".
        dietary_preferences: Dietary restrictions or cuisine preferences.
        travelers: Number of travelers.
        multi_city_route: For multi-city trips, describe the full route
            e.g. "Kochi (3 nights) → Alleppey (2 nights) → back to Kochi airport".

    Returns:
        Formatted markdown itinerary with ## Day N headings, morning/afternoon/evening
        sections, real venue names, approximate costs, and travel tips.
    """
    print(f"\n📅  create_itinerary | {destination} | {duration_days} days | ₹{daily_budget_inr:,}/day/person")

    # Calculate check-in time (arrival + transfer)
    try:
        arr_h, arr_m = map(int, outbound_arrival_time.split(":"))
        checkin_total_mins = arr_h * 60 + arr_m + airport_to_hotel_transfer_mins
        checkin_h, checkin_m = divmod(checkin_total_mins, 60)
        checkin_time = f"{checkin_h:02d}:{checkin_m:02d}"
    except Exception:
        checkin_time = "afternoon"

    # Calculate latest hotel checkout time on last day
    try:
        dep_h, dep_m = map(int, return_departure_time.split(":"))
        leave_hotel_mins = dep_h * 60 + dep_m - airport_to_hotel_transfer_mins_last_day - 90
        leave_h, leave_m = divmod(max(0, leave_hotel_mins), 60)
        leave_hotel_time = f"{leave_h:02d}:{leave_m:02d}"
    except Exception:
        leave_hotel_time = "morning"

    multi_city_note = f"\nThis is a multi-city trip: {multi_city_route}" if multi_city_route else ""

    prompt = f"""You are the Itinerary Agent for a travel planning system. Create a detailed,
specific, and realistic day-by-day itinerary.{multi_city_note}

Trip details:
- Destination: {destination}
- Dates: {travel_date} to {return_date} ({duration_days} days)
- Hotel: {hotel_name} ({hotel_area})
- Day 1: Flight lands at {outbound_arrival_time}. Transfer to hotel ≈ {airport_to_hotel_transfer_mins} min.
  Hotel check-in available from approximately {checkin_time}. Plan Day 1 AFTER this time.
- Last day: Return flight departs {return_departure_time}. Transfer to airport ≈ {airport_to_hotel_transfer_mins_last_day} min.
  Must leave hotel by {leave_hotel_time} at the latest. Plan last day activities before this.
- Daily budget per person: ₹{daily_budget_inr:,} (activities + food + local transport)
- Travelers: {travelers}
- Interests: {interests or "sightseeing, local food, beaches"}
- Dietary preferences: {dietary_preferences or "no restrictions"}
- Weather: {weather_summary}

Hard rules:
1. Day 1 activities MUST start after {checkin_time} (arrival + transfer time)
2. Last day MUST wrap up by {leave_hotel_time} — include airport transfer in the plan
3. Name SPECIFIC real places: actual beach/restaurant/market/attraction names
4. Include approximate INR cost per activity
5. Include local transport between spots (auto/taxi cost estimate)
6. Balance outdoor vs indoor based on weather forecast
7. For multi-city routes: show inter-city travel day explicitly with travel time and mode

Format each day as:
## Day N — [Date] — [Theme]
**Morning (HH:MM–HH:MM):** ...
**Afternoon (HH:MM–HH:MM):** ...
**Evening (HH:MM–HH:MM):** ...
**Meals:** ...
**Local transport:** ...
**Estimated spend today:** ₹X,XXX per person

End with **Pro Tips** — 3–4 destination-specific hacks."""

    response = _get_llm().invoke(prompt)
    itinerary = response.content.strip()
    print(f"   → itinerary generated ({len(itinerary.split(chr(10)))} lines)")
    return itinerary
