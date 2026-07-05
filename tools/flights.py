"""Flight tools — two-step: airport code lookup (Tavily) + flight search (fli / SerpAPI).

Requires env vars:
  TAVILY_API_KEY   — tavily.com key (used for airport code lookup)
  SERPAPI_API_KEY  — serpapi.com key (used for Google Flights search, if search_flights is called)
"""

import os
import re
from datetime import datetime

from dateutil import parser as dateparser
from tavily import TavilyClient
import serpapi


# ── Tool 1: Airport code lookup (Tavily) ──────────────────────────────────────

def get_airport_code(city: str) -> dict:
    """Flight Agent — Step 1: Look up the IATA airport code(s) for a city via Tavily search.

    Searches the web for the city's commercial airport(s) and their IATA codes.
    Call this for every origin and destination before calling search_flights_fast.

    Args:
        city: City or region name, e.g. "Pune", "Goa", "Kochi", "Bali".

    Returns:
        Dict with:
          city (str), search_results (list of {title, content, url})
        On failure: {"city": city, "error": "..."}.
    """
    print(f"\n🔍  get_airport_code [Tavily] | {city}")

    try:
        client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
        response = client.search(
            query=f"all IATA airport codes for {city}, India commercial airport",
            max_results=5,
            search_depth="basic",
            include_answer=True,
        )
    except Exception as e:
        return {"city": city, "error": f"Tavily search failed: {e}"}

    results = []
    for r in response.get("results", [])[:5]:
        results.append({
            "title":   r.get("title", ""),
            "content": r.get("content", "")[:400],
            "url":     r.get("url", ""),
        })

    # Include the quick answer if Tavily provides one
    answer = response.get("answer", "")
    if answer:
        print(f"   → Tavily answer: {answer[:120]}")

    print(f"   → {len(results)} result(s) returned")
    return {"city": city, "answer": answer, "search_results": results}


# ── Tool 2: Flight search ──────────────────────────────────────────────────────

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


def _parse_items(items: list, adults: int) -> list[dict]:
    offers = []
    for item in items:
        segs = item.get("flights", [])
        if not segs:
            continue
        price_total = item.get("price")
        if not price_total:
            continue

        first = segs[0]
        last = segs[-1]
        stops = len(segs) - 1
        price_pp = round(price_total / adults) if adults > 0 else price_total
        dep_time = first["departure_airport"]["time"][11:16]
        arr_time = last["arrival_airport"]["time"][11:16]

        layovers = [
            {"city": lv.get("name", lv.get("id", "?")), "duration": _fmt_mins(lv.get("duration", 0))}
            for lv in item.get("layovers", [])
        ]

        offers.append({
            "airline": first.get("airline", ""),
            "flight_number": first.get("flight_number", ""),
            "price_per_person_inr": price_pp,
            "total_price_inr": price_total,
            "departure_time": dep_time,
            "arrival_time": arr_time,
            "duration": _fmt_mins(item.get("total_duration", 0)),
            "stops": stops,
            "direct": stops == 0,
            "layovers": layovers,
            "from": first["departure_airport"]["id"],
            "to": last["arrival_airport"]["id"],
        })

    offers.sort(key=lambda r: (not r["direct"], r["total_price_inr"]))
    return offers[:3]


def search_flights(
    origin_iata: str,
    dest_iata: str,
    date: str,
    travelers: int = 1,
    direct_only: bool = False,
) -> dict:
    """Flight Agent — Step 2: Search one-way flights via Google Flights (SerpAPI).

    Call this independently for each leg — outbound and return — so you can
    mix airports freely (e.g. fly into GOX, return from GOI if cheaper).

    Args:
        origin_iata: Departure IATA code, e.g. "PNQ".
        dest_iata: Arrival IATA code, e.g. "GOX".
        date: Flight date, e.g. "2026-08-01" or "1 August 2026".
        travelers: Number of adult passengers.
        direct_only: If True, return only nonstop options.

    Returns:
        Dict with route (str) and flights (list of up to 3 options).
        Each flight: airline, flight_number, price_per_person_inr, total_price_inr,
        departure_time, arrival_time, duration, stops, direct (bool),
        layovers [{city, duration}], from, to.
    """
    date_str = _parse_date(date)
    print(f"\n✈️  search_flights | {origin_iata}→{dest_iata} | {date_str} | {travelers} pax | direct_only={direct_only}")

    try:
        client = serpapi.Client(api_key=os.environ["SERPER_API_KEY"])
        raw = client.search({
            "engine": "google_flights",
            "departure_id": origin_iata,
            "arrival_id": dest_iata,
            "outbound_date": date_str,
            "currency": "INR",
            "hl": "en",
            "adults": travelers,
            "type": "2",
        })
    except Exception as e:
        print(f"[warning] SerpAPI error: {e}")
        return {"route": f"{origin_iata} → {dest_iata}", "flights": []}

    all_items = list(raw.get("best_flights", [])) + list(raw.get("other_flights", []))
    parsed = _parse_items(all_items, travelers)

    nonstop = [f for f in parsed if f["direct"]]
    if nonstop:
        print(f"{len(nonstop)} nonstop flight(s) found")
        flights = nonstop[:3]
    elif direct_only:
        print("No nonstop flights found")
        flights = []
    else:
        print("No nonstop — returning best connecting options")
        flights = parsed[:3]

    if flights:
        best = flights[0]
        tag = "direct" if best["direct"] else f"{best['stops']}-stop"
        print(f"   → best: {best['airline']} {best['departure_time']}→{best['arrival_time']} ₹{best['total_price_inr']:,} [{tag}]")

    return {"route": f"{origin_iata} → {dest_iata}", "flights": flights}
