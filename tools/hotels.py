"""Hotel Agent tools — Google Hotels via fast_hotels package (no API key required)."""

import re
from dateutil import parser as dateparser
from fast_hotels.core import fetch as _fh_fetch
from fast_hotels.hotels_impl import HotelData as _HotelData, Guests as _Guests
from fast_hotels.filter import THSData as _THSData
from selectolax.lexbor import LexborHTMLParser as _LexborHTMLParser


def _parse_date(date_str: str) -> str:
    from datetime import datetime as _dt
    try:
        dt = dateparser.parse(date_str)
    except Exception:
        m = re.search(r"\d{4}-\d{2}-\d{2}", date_str)
        if not m:
            raise ValueError(f"Cannot parse date: '{date_str}'")
        dt = _dt.fromisoformat(m.group())
    today = _dt.today()
    while dt.date() < today.date():
        dt = dt.replace(year=dt.year + 1)
    return dt.strftime("%Y-%m-%d")


def search_hotels(
    city: str,
    checkin_date: str,
    checkout_date: str,
    budget_per_night: int,
    duration_days: int,
    search_term: str | None = None,
    guests: int = 2,
) -> dict:
    """Hotel Agent: Search real hotels via Google Hotels (no API key required).

    Interprets natural-language style preferences via search_term and returns
    top-5 options sorted by price. Recommends best fit for budget and preferences.

    Args:
        city: City to search in, e.g. "Goa" or "Manali".
        checkin_date: Check-in date, e.g. "2026-08-10" or "10 August 2026".
        checkout_date: Check-out date.
        budget_per_night: Maximum nightly rate in INR.
        duration_days: Number of nights.
        search_term: Optional preference filter — e.g. "beach facing", "luxury",
            "near airport", "budget", "resort". Passed directly to Google Hotels.
        guests: Number of adult guests (default 2).

    Returns:
        Dict with city, checkin, checkout, duration_days, budget_per_night,
        and options (list of up to 5 hotels). Each hotel has: hotel_name,
        price_per_night_inr, total_cost_inr, rating, within_budget.
    """
    print(f"\n🏨  search_hotels | {city} | {checkin_date}→{checkout_date} | "
          f"{duration_days}n | ₹{budget_per_night:,}/night"
          + (f" | '{search_term}'" if search_term else ""))

    checkin_str = _parse_date(checkin_date)
    checkout_str = _parse_date(checkout_date)
    location = f"{search_term} hotels in {city}" if search_term else f"{city}, India"

    filter_data = _THSData.from_interface(
        hotel_data=[_HotelData(
            checkin_date=checkin_str,
            checkout_date=checkout_str,
            location=location,
        )],
        guests=_Guests(adults=guests),
        room_type="standard",
    )
    params = {
        "ths": filter_data.as_b64().decode("utf-8"),
        "hl": "en",
        "curr": "INR",
    }

    options = []
    for _ in range(3):
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

            m = re.search(r"₹([0-9,]+)", card.text(strip=True))
            price_per_night = int(m.group(1).replace(",", "")) if m else None

            if name and price_per_night:
                options.append({
                    "hotel_name": name,
                    "price_per_night_inr": price_per_night,
                    "total_cost_inr": price_per_night * duration_days,
                    "rating": rating,
                    "within_budget": price_per_night <= budget_per_night,
                })
        if options:
            break

    options.sort(key=lambda h: h["price_per_night_inr"])
    options = options[:5]

    if options:
        top = options[0]
        budget_tag = "✅" if top["within_budget"] else "⚠️"
        print(f"   → top: {top['hotel_name']} ★{top.get('rating','—')} ₹{top['price_per_night_inr']:,}/night {budget_tag}")
    else:
        print("   → no hotels found")

    return {
        "city": city,
        "checkin": checkin_str,
        "checkout": checkout_str,
        "duration_days": duration_days,
        "budget_per_night": budget_per_night,
        "options": options,
    }
