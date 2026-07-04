"""Flight search using fli (free Google Flights scraper — no API key needed).

Provides search_flights_fast() as an alternative to the SerpAPI-based search_flights().
Accepts IATA codes directly — no separate airport lookup step required.
"""

import re
from datetime import datetime

from dateutil import parser as dateparser
from fli.models import FlightSearchFilters, FlightSegment, PassengerInfo
from fli.models.airport import Airport
from fli.models.google_flights.base import TripType, SeatType, MaxStops
from fli.search.flights import SearchFlights


def _parse_date(date_str: str) -> str:
    try:
        dt = dateparser.parse(date_str)
    except Exception:
        m = re.search(r"\d{4}-\d{2}-\d{2}", date_str)
        if not m:
            raise ValueError(f"Cannot parse date: '{date_str}'")
        dt = datetime.fromisoformat(m.group())

    today = datetime.today()
    while dt.date() < today.date():
        dt = dt.replace(year=dt.year + 1)
        print(f"   ℹ️  Date was in the past — advanced to {dt.strftime('%Y-%m-%d')}")

    return dt.strftime("%Y-%m-%d")


def _fmt_mins(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    return f"{h}h {m:02d}m"


_SEAT_MAP = {
    "economy": SeatType.ECONOMY,
    "premium-economy": SeatType.PREMIUM_ECONOMY,
    "business": SeatType.BUSINESS,
    "first": SeatType.FIRST,
}

_STOPS_MAP = {
    None: MaxStops.ANY,
    0: MaxStops.NON_STOP,
    1: MaxStops.ONE_STOP_OR_FEWER,
    2: MaxStops.TWO_OR_FEWER_STOPS,
}


def search_flights_fast(
    origin_iata: str,
    dest_iata: str,
    date: str,
    travelers: int = 1,
    max_stops: int | None = None,
    seat: str = "economy",
) -> dict:
    """Search one-way flights using fli (free Google Flights scraper).

    No API key required. Use as an alternative to search_flights when SerpAPI
    quota is exhausted or unavailable.

    Args:
        origin_iata: Departure IATA airport code, e.g. "PNQ".
        dest_iata:   Arrival IATA airport code, e.g. "GOX".
        date:        Flight date — "2026-08-01" or natural language like "1 August 2026".
        travelers:   Number of adult passengers (default 1).
        max_stops:   Max stops — None (any), 0 (nonstop only), 1, or 2.
        seat:        Seat class — "economy", "premium-economy", "business", "first".

    Returns:
        Dict with:
          route (str): "ORIGIN → DEST"
          flights (list): options sorted nonstop-first then by price. Each has:
            airline (str), flight_number (str), price_inr (float),
            price_per_person_inr (float), departure_time (HH:MM),
            arrival_time (HH:MM), duration (str e.g. "2h 05m"),
            stops (int), direct (bool)
        On error: adds "error" key with message.
    """
    origin_iata = origin_iata.upper().strip()
    dest_iata = dest_iata.upper().strip()
    date_str = _parse_date(date)
    print(f"\n✈️  search_flights_fast | {origin_iata}→{dest_iata} | {date_str} | {travelers} pax | max_stops={max_stops}")

    # Validate airport codes
    try:
        origin_airport = Airport[origin_iata]
    except KeyError:
        return {"route": f"{origin_iata} → {dest_iata}", "flights": [], "error": f"Invalid airport code: '{origin_iata}'"}
    try:
        dest_airport = Airport[dest_iata]
    except KeyError:
        return {"route": f"{origin_iata} → {dest_iata}", "flights": [], "error": f"Invalid airport code: '{dest_iata}'"}

    stops_filter = _STOPS_MAP.get(max_stops, MaxStops.ANY)
    seat_type = _SEAT_MAP.get(seat, SeatType.ECONOMY)

    try:
        filters = FlightSearchFilters(
            trip_type=TripType.ONE_WAY,
            passenger_info=PassengerInfo(adults=travelers),
            flight_segments=[
                FlightSegment(
                    departure_airport=[[origin_airport, 0]],
                    arrival_airport=[[dest_airport, 0]],
                    travel_date=date_str,
                )
            ],
            stops=stops_filter,
            seat_type=seat_type,
        )
        client = SearchFlights()
        raw_results = client.search(filters, currency="INR")
    except Exception as e:
        print(f"   ⚠️  fli error: {e}")
        return {"route": f"{origin_iata} → {dest_iata}", "flights": [], "error": str(e)}

    if not raw_results:
        print("   → no results")
        return {"route": f"{origin_iata} → {dest_iata}", "flights": []}

    flights = []
    for r in raw_results:
        # skip entries with no price
        if r.price is None:
            continue

        first_leg = r.legs[0]
        last_leg = r.legs[-1]
        price_total = round(r.price)
        price_pp = round(r.price / travelers) if travelers > 0 else price_total

        flights.append({
            "airline": r.primary_airline_name or (r.primary_airline.name if r.primary_airline else "Unknown"),
            "flight_number": first_leg.flight_number,
            "price_inr": price_total,
            "price_per_person_inr": price_pp,
            "departure_time": first_leg.departure_datetime.strftime("%H:%M"),
            "arrival_time": last_leg.arrival_datetime.strftime("%H:%M"),
            "duration": _fmt_mins(r.duration),
            "stops": r.stops,
            "direct": r.stops == 0,
        })

    flights.sort(key=lambda f: (not f["direct"], f["price_inr"]))

    nonstop_count = sum(1 for f in flights if f["direct"])
    print(f"   → {len(flights)} result(s) with price, {nonstop_count} nonstop")
    if flights:
        best = flights[0]
        tag = "direct" if best["direct"] else f"{best['stops']}-stop"
        print(f"   → best: {best['airline']} {best['departure_time']}→{best['arrival_time']} ₹{best['price_inr']:,} [{tag}]")

    return {"route": f"{origin_iata} → {dest_iata}", "flights": flights}
