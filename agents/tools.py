"""Tool functions for the TravelGPT subagents.

Flight search uses the `fli` package (Google Flights, no API key needed).
Hotel search uses the `fast_hotels` package (Google Hotels, no API key needed).
Budget and ranking are pure deterministic math.
"""

import os
import re
from datetime import datetime
from dateutil import parser as dateparser

from fli.models import (
    Airport, Airline,
    FlightSearchFilters, FlightSegment,
    PassengerInfo, SeatType,
)
from fli.search import SearchFlights
from tavily import TavilyClient as _TavilyClient
from fast_hotels.core import fetch as _fh_fetch
from fast_hotels.hotels_impl import HotelData as _HotelData, Guests as _Guests
from fast_hotels.filter import THSData as _THSData
from selectolax.lexbor import LexborHTMLParser as _LexborHTMLParser

_tavily_client: "_TavilyClient | None" = None
_iata_cache: dict[str, str] = {}  # session cache: city_lower → IATA code


def _tavily() -> _TavilyClient:
    global _tavily_client
    if _tavily_client is None:
        key = os.environ.get("TAVILY_API_KEY")
        if not key:
            raise RuntimeError("TAVILY_API_KEY not set")
        _tavily_client = _TavilyClient(api_key=key)
    return _tavily_client


def _to_airport(city: str) -> Airport:
    """Resolve a city name or IATA code to an Airport enum member.

    Resolution order:
    1. Session cache (instant)
    2. Tavily search + LLM extraction of the main airport IATA code
    3. Raw IATA passthrough (if input is already a 3-letter code)
    """
    key = city.strip().lower()

    # 1. Session cache
    if key in _iata_cache:
        return Airport[_iata_cache[key]]

    # 2. Tavily search → LLM extraction
    iata = None
    try:
        results = _tavily().search(
            query=f"main airport IATA code for {city} India",
            search_depth="basic",
            max_results=3,
        )
        context = "\n".join(
            r.get("content", "")[:500] for r in results.get("results", [])
        )
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)
        response = llm.invoke(
            f"Based on the search results below, what is the IATA airport code for "
            f"the main/primary airport serving '{city}'?\n"
            f"Reply with ONLY the 3-letter IATA code, nothing else.\n\n"
            f"Search results:\n{context}"
        )
        candidate = response.content.strip().upper()
        print(f"   🔍 Airport lookup '{city}' → Tavily+LLM returned: {candidate}")
        if len(candidate) == 3:
            Airport[candidate]  # validate it exists in fli enum
            iata = candidate
    except Exception as e:
        print(f"   ⚠️  Tavily/LLM airport lookup failed for '{city}': {e}")

    if iata:
        _iata_cache[key] = iata
        return Airport[iata]

    # 3. Raw IATA passthrough
    try:
        code = key.upper()
        Airport[code]
        _iata_cache[key] = code
        return Airport[code]
    except KeyError:
        raise ValueError(
            f"Unknown airport for '{city}'. "
            f"Pass a 3-letter IATA code (e.g. 'PNQ') or a city name."
        )


def _parse_date(date_str: str) -> str:
    """Parse a human date string to YYYY-MM-DD."""
    try:
        return dateparser.parse(date_str).strftime("%Y-%m-%d")
    except Exception:
        # fallback: try regex for YYYY-MM-DD
        m = re.search(r"\d{4}-\d{2}-\d{2}", date_str)
        if m:
            return m.group()
        raise ValueError(f"Cannot parse date: '{date_str}'")


def _fmt_duration(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    return f"{h}h {m:02d}m"


def _search_one_way(
    origin_airport: Airport,
    dest_airport: Airport,
    date_str: str,
    adults: int,
) -> list[dict]:
    """Run a one-way search and return top-3 results as clean dicts."""
    filters = FlightSearchFilters(
        passenger_info=PassengerInfo(adults=adults),
        flight_segments=[FlightSegment(
            departure_airport=[[origin_airport, 0]],
            arrival_airport=[[dest_airport, 0]],
            travel_date=date_str,
        )],
        seat_type=SeatType.ECONOMY,
    )
    results = SearchFlights().search(filters) or []
    out = []
    for r in results:
        if r.price is None:
            continue
        leg = r.legs[0] if r.legs else None
        out.append({
            "airline": r.primary_airline_name or "Unknown",
            "flight_number": leg.flight_number if leg else "",
            "price_per_person_inr": round(r.price / adults) if adults > 0 else round(r.price),
            "total_price_inr": round(r.price),
            "departure_time": leg.departure_datetime.strftime("%H:%M") if leg else "unknown",
            "arrival_time": leg.arrival_datetime.strftime("%H:%M") if leg else "unknown",
            "duration": _fmt_duration(r.duration),
            "stops": r.stops,
            "aircraft": leg.aircraft if leg else "",
        })
        if len(out) == 3:
            break
    return out


_flight_search = SearchFlights()


def search_flights(
    origin: str,
    destination: str,
    travel_date: str,
    return_date: str | None = None,
    travelers: int = 1,
) -> dict:
    """Search for real flights via Google Flights (no API key required).

    Returns structured outbound and optional return flight options with exact
    airline names, flight numbers, departure/arrival times, duration, and
    prices in INR direct from Google Flights data.

    Args:
        origin: Departure city name, e.g. "Pune" or IATA code "PNQ".
        destination: Arrival city name, e.g. "Goa" or IATA code "GOI".
        travel_date: Outbound date, e.g. "10 August 2026" or "2026-08-10".
        return_date: Return date for the reverse leg. If omitted only outbound is searched.
        travelers: Number of adult passengers (default 1).

    Returns:
        Dict with 'outbound' (list of top-3 options) and optionally 'return'
        (list of top-3 options). Each option has: airline, flight_number,
        price_per_person_inr, total_price_inr, departure_time, arrival_time,
        duration, stops, aircraft.
    """
    print(f"\n✈️  search_flights | {origin} → {destination} | {travel_date} → {return_date} | {travelers} traveler(s)")

    orig_ap = _to_airport(origin)
    dest_ap = _to_airport(destination)
    out_date = _parse_date(travel_date)

    result: dict = {
        "route": f"{origin} → {destination}",
        "outbound": _search_one_way(orig_ap, dest_ap, out_date, travelers),
    }

    if return_date:
        ret_date = _parse_date(return_date)
        result["return"] = _search_one_way(dest_ap, orig_ap, ret_date, travelers)

    ob = result["outbound"][0] if result.get("outbound") else {}
    rb = result.get("return", [{}])[0] if result.get("return") else {}
    print(f"   → outbound: {ob.get('airline','—')} ₹{ob.get('total_price_inr', 0):,} | return: {rb.get('airline','—')} ₹{rb.get('total_price_inr', 0):,}")

    return result


def search_hotels(
    city: str,
    checkin_date: str,
    checkout_date: str,
    budget_per_night: int,
    duration_days: int,
    search_term: str | None = None,
) -> dict:
    """Search for real hotels via Google Hotels (no API key required).

    Returns structured hotel options with exact names, ratings, and INR prices
    sourced live from Google Hotels.

    Args:
        city: City to search in, e.g. "Goa".
        checkin_date: Check-in date, e.g. "10 August 2026" or "2026-08-10".
        checkout_date: Check-out date, e.g. "14 August 2026" or "2026-08-14".
        budget_per_night: Maximum nightly rate in INR, e.g. 3000.
        duration_days: Number of nights.
        search_term: Optional filter term passed directly to Google Hotels search,
            e.g. "beach facing", "luxury", "near airport". When provided, the search
            becomes "<search_term> hotels in <city>" which mirrors typing that phrase
            into Google Hotels.

    Returns:
        Dict with 'city', 'checkin', 'checkout', 'duration_days', 'options' (list of
        top-5 hotels sorted by price). Each option has: hotel_name, price_per_night_inr,
        total_cost_inr, rating.
    """
    print(f"\n🏨  search_hotels | {city} | {checkin_date} → {checkout_date} | {duration_days} nights | budget ₹{budget_per_night:,}/night" + (f" | filter: {search_term}" if search_term else ""))

    checkin_str = _parse_date(checkin_date)
    checkout_str = _parse_date(checkout_date)
    location = f"{search_term} hotels in {city}" if search_term else f"{city}, India"

    filter_data = _THSData.from_interface(
        hotel_data=[_HotelData(
            checkin_date=checkin_str,
            checkout_date=checkout_str,
            location=location,
        )],
        guests=_Guests(adults=2),
        room_type="standard",
    )
    params = {
        "ths": filter_data.as_b64().decode("utf-8"),
        "hl": "en",
        "curr": "INR",
    }

    options = []
    for _attempt in range(3):
        res = _fh_fetch(params, location)
        parser = _LexborHTMLParser(res.text)
        for card in parser.css("div.uaTTDe"):
            name_el = card.css_first("h2.BgYkof")
            name = name_el.text(strip=True) if name_el else None

            rating_el = card.css_first("span.KFi5wf")
            rating = None
            if rating_el:
                try:
                    rating = float(rating_el.text(strip=True))
                except ValueError:
                    pass

            card_text = card.text(strip=True)
            m = re.search(r"₹([0-9,]+)", card_text)
            price_per_night = int(m.group(1).replace(",", "")) if m else None

            if name and price_per_night:
                options.append({
                    "hotel_name": name,
                    "price_per_night_inr": price_per_night,
                    "total_cost_inr": price_per_night * duration_days,
                    "rating": rating,
                })

        if options:
            break

    options.sort(key=lambda h: h["price_per_night_inr"])
    options = options[:5]

    if options:
        top = options[0]
        print(f"   → top pick: {top['hotel_name']} ★{top.get('rating','—')} ₹{top['price_per_night_inr']:,}/night")
    else:
        print("   → no hotels found")

    return {
        "city": city,
        "checkin": checkin_str,
        "checkout": checkout_str,
        "duration_days": duration_days,
        "options": options,
    }


def compute_budget(
    total_flight_cost: int,
    hotel_total_cost: int,
    travelers: int,
    duration_days: int,
) -> dict:
    """Compute the full trip budget breakdown for a destination.

    Args:
        total_flight_cost: Total round-trip flight cost for ALL travelers combined (INR).
            This is outbound + return, all passengers included.
        hotel_total_cost: Total hotel cost for the entire stay in INR.
        travelers: Number of travelers (used for per-person activity/food/transport estimates).
        duration_days: Trip duration in days.

    Returns:
        Dict with flights, hotel, activities, food, transport, misc, total (all INR).
    """
    print(f"\n💰  compute_budget | flights ₹{total_flight_cost:,} + hotel ₹{hotel_total_cost:,} | {travelers} traveler(s) × {duration_days} days")

    flights = total_flight_cost
    hotel = hotel_total_cost
    activities = 500 * travelers * duration_days
    food = 700 * travelers * duration_days
    transport = 300 * travelers * duration_days

    subtotal = flights + hotel + activities + food + transport
    misc = round(subtotal * 0.1)
    total = subtotal + misc

    print(f"   → total ₹{total:,}")

    return {
        "flights": flights,
        "hotel": hotel,
        "activities": activities,
        "food": food,
        "transport": transport,
        "misc": misc,
        "total": total,
    }


def rank_destinations(candidates: list[dict]) -> list[dict]:
    """Rank candidate destinations by a weighted score and return them best-first.

    Each candidate must be a dict with:
        destination (str), total_cost (int, INR), budget_limit (int, INR),
        experience_score (float 0-100), weather_score (float 0-100),
        travel_time_score (float 0-100).

    Scoring weights: budget_fit 0.40, experience 0.30, weather 0.15, travel_time 0.15.

    budget_fit penalty curve (steeper than linear for over-budget trips):
        - Within budget              → 100
        - 1–10% over budget          → 60–80  (steep initial drop)
        - 10–25% over budget         → 20–60  (continues declining)
        - >25% over budget           → 0

    Returns:
        List of dicts sorted descending by score. Each item has: destination, score,
        budget (total, fits_budget, overage_pct), and recommendation_reasoning
        (budget_fit, experience_score, weather_score, accessibility).
    """
    print(f"\n📊  rank_destinations | {len(candidates)} candidate(s): {[c['destination'] for c in candidates]}")

    ranked = []
    for c in candidates:
        total_cost = c["total_cost"]
        budget_limit = c["budget_limit"]

        if total_cost <= budget_limit:
            budget_fit = 100.0
        else:
            overage_pct = (total_cost - budget_limit) / budget_limit  # 0.0 → ∞
            if overage_pct >= 0.25:
                budget_fit = 0.0
            else:
                # Steep drop: 0% over → 100, 10% over → 60, 25% over → 0
                budget_fit = max(0.0, 100.0 - (overage_pct / 0.25) * 100.0)

        score = round(
            0.40 * budget_fit
            + 0.30 * c["experience_score"]
            + 0.15 * c["weather_score"]
            + 0.15 * c["travel_time_score"],
            1,
        )

        overage_pct_display = (
            round((total_cost - budget_limit) / budget_limit * 100, 1)
            if total_cost > budget_limit
            else 0.0
        )

        ranked.append(
            {
                "destination": c["destination"],
                "score": score,
                "budget": {
                    "total": total_cost,
                    "fits_budget": total_cost <= budget_limit,
                    "overage_pct": overage_pct_display,
                },
                "recommendation_reasoning": {
                    "budget_fit": round(budget_fit, 1),
                    "experience_score": float(c["experience_score"]),
                    "weather_score": float(c["weather_score"]),
                    "accessibility": float(c["travel_time_score"]),
                },
            }
        )

    ranked.sort(key=lambda r: r["score"], reverse=True)

    for r in ranked:
        fits = "✅" if r["budget"]["fits_budget"] else "⚠️"
        print(f"   → {r['destination']} score={r['score']} {fits} ₹{r['budget']['total']:,}")

    return ranked
