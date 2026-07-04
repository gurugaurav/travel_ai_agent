"""Weather Agent tool — Open-Meteo API (free, no API key required)."""

import json
import urllib.request
import urllib.parse
from datetime import date, timedelta


_WMO_DESCRIPTIONS = {
    0: "Clear sky",
    1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Icy fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
}


def _wmo_label(code: int) -> str:
    return _WMO_DESCRIPTIONS.get(code, f"Code {code}")


def _is_severe(code: int) -> bool:
    return code in {65, 75, 80, 81, 82, 95, 96, 99}


def _fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read().decode())


def _geocode(destination: str) -> dict | None:
    """Geocode a destination using Nominatim (OpenStreetMap). Prefers India."""
    # Try India-scoped search first, then global fallback
    queries = [
        (f"{destination}, India", "IN"),
        (destination, None),
    ]
    req = urllib.request.Request.__new__(urllib.request.Request)
    for query, country_code in queries:
        params: dict = {"q": query, "format": "json", "limit": 1, "addressdetails": 1}
        if country_code:
            params["countrycodes"] = country_code.lower()
        url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(params)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "TripMind/1.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                results = json.loads(r.read().decode())
        except Exception:
            continue

        if results:
            r0 = results[0]
            return {
                "latitude": float(r0["lat"]),
                "longitude": float(r0["lon"]),
                "name": r0.get("display_name", destination).split(",")[0].strip(),
                "country": r0.get("address", {}).get("country", ""),
                "country_code": r0.get("address", {}).get("country_code", "").upper(),
            }

    return None


def get_weather_forecast(
    destination: str,
    start_date: str,
    end_date: str,
    country: str = "India",
) -> dict:
    """Weather Agent: Fetch weather forecast using Open-Meteo (no API key needed).

    Retrieves daily forecasts for the trip period including temperature range,
    precipitation, and weather conditions. Flags severe weather days and
    suggests indoor/outdoor activity balance based on the forecast.

    Args:
        destination: City name, e.g. "Goa", "Manali", "Bali". For international
            destinations outside India, include the country: "Bali, Indonesia".
        start_date: Forecast start date in YYYY-MM-DD format.
        end_date: Forecast end date in YYYY-MM-DD format.
        country: Country hint for disambiguation (default "India").

    Returns:
        Dict with daily forecasts, summary statistics, severe_weather_days,
        clothing_recommendation, and activity_suggestions.
    """
    print(f"\n🌤️  get_weather_forecast | {destination} | {start_date} → {end_date}")

    # Geocode with India preference
    loc = _geocode(destination)
    if not loc:
        return {"error": f"Could not locate '{destination}'", "destination": destination}

    lat = loc["latitude"]
    lon = loc["longitude"]
    city_name = loc.get("name", destination)
    country = loc.get("country", "")

    # Open-Meteo only supports 16-day forecasts from today
    # For future dates beyond 16 days, we'll return climatological hints
    today = date.today()
    try:
        sd = date.fromisoformat(start_date)
        ed = date.fromisoformat(end_date)
    except ValueError:
        return {"error": f"Invalid date format. Use YYYY-MM-DD.", "destination": destination}

    days_out = (sd - today).days
    forecast_days = []

    if days_out <= 16:
        # Real forecast available from Open-Meteo forecast API
        actual_end = min(ed, today + timedelta(days=15))
        wx_url = (
            "https://api.open-meteo.com/v1/forecast?"
            + urllib.parse.urlencode({
                "latitude": lat, "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
                "timezone": "auto",
                "start_date": start_date,
                "end_date": actual_end.isoformat(),
            })
        )
        historical = False
    else:
        # Beyond 16-day forecast window — use same dates from last year as proxy.
        # Open-Meteo archive API (free, covers all years back to 1940).
        hist_sd = sd.replace(year=sd.year - 1)
        hist_ed = ed.replace(year=ed.year - 1)
        wx_url = (
            "https://archive-api.open-meteo.com/v1/archive?"
            + urllib.parse.urlencode({
                "latitude": lat, "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
                "timezone": "auto",
                "start_date": hist_sd.isoformat(),
                "end_date": hist_ed.isoformat(),
            })
        )
        historical = True

    try:
        wx = _fetch_json(wx_url)
    except Exception as e:
        return {"error": f"Forecast fetch failed: {e}", "destination": destination}

    daily = wx.get("daily", {})
    raw_dates = daily.get("time", [])
    max_temps = daily.get("temperature_2m_max", [])
    min_temps = daily.get("temperature_2m_min", [])
    precips = daily.get("precipitation_sum", [])
    codes = daily.get("weathercode", [])

    # When using historical data, rewrite dates to trip year so output is labelled correctly
    if historical:
        year_offset = sd.year - hist_sd.year
        def _remap_date(d: str) -> str:
            y, mo, day = d.split("-")
            return f"{int(y)+year_offset}-{mo}-{day}"
        display_dates = [_remap_date(d) for d in raw_dates]
    else:
        display_dates = raw_dates

    for i, d in enumerate(display_dates):
        max_t = max_temps[i] if i < len(max_temps) else None
        min_t = min_temps[i] if i < len(min_temps) else None
        precip = precips[i] if i < len(precips) else 0
        code = int(codes[i]) if i < len(codes) else 0
        forecast_days.append({
            "date": d,
            "condition": _wmo_label(code),
            "max_temp_c": round(max_t, 1) if max_t is not None else None,
            "min_temp_c": round(min_t, 1) if min_t is not None else None,
            "precipitation_mm": round(precip, 1) if precip else 0,
            "severe": _is_severe(code),
            "source": "historical_estimate" if historical else "forecast",
        })

    # Summary stats
    severe_days = [d for d in forecast_days if d["severe"]]
    temps = [d["max_temp_c"] for d in forecast_days if d["max_temp_c"] is not None]
    avg_max = round(sum(temps) / len(temps), 1) if temps else None

    # Clothing recommendation
    if avg_max is None:
        clothing = "Check local forecasts closer to the trip date."
    elif avg_max >= 30:
        clothing = "Hot weather — light breathable clothing, sunscreen, hat essential."
    elif avg_max >= 22:
        clothing = "Warm weather — light clothes with a layer for evenings."
    elif avg_max >= 15:
        clothing = "Mild weather — mix of light and warm layers."
    else:
        clothing = "Cool weather — warm layers, jacket recommended."

    if any(d["precipitation_mm"] > 5 for d in forecast_days):
        clothing += " Rain gear or umbrella advised."

    # Activity suggestion
    good_days = len(forecast_days) - len(severe_days)
    if len(forecast_days) == 0:
        activity_note = "Forecast not available for dates beyond 16 days — plan for typical seasonal weather."
    elif len(severe_days) == 0:
        activity_note = "All days look great for outdoor activities."
    elif len(severe_days) >= len(forecast_days) // 2:
        activity_note = f"{len(severe_days)} of {len(forecast_days)} days have severe weather — plan indoor backup activities."
    else:
        activity_note = f"{good_days} good days for outdoors; {len(severe_days)} day(s) may need indoor alternatives."

    result = {
        "destination": f"{city_name}, {country}".strip(", "),
        "latitude": lat,
        "longitude": lon,
        "period": f"{start_date} to {end_date}",
        "forecast_available": len(forecast_days) > 0,
        "data_source": "historical_estimate (last year same dates)" if historical else "live_forecast",
        "daily_forecast": forecast_days,
        "summary": {
            "avg_max_temp_c": avg_max,
            "severe_weather_days": len(severe_days),
            "total_forecast_days": len(forecast_days),
        },
        "clothing_recommendation": clothing,
        "activity_suggestion": activity_note,
    }

    print(f"   → avg max {avg_max}°C | {len(severe_days)} severe day(s) | {len(forecast_days)} days forecast")
    return result
