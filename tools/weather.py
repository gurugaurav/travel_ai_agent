"""Weather tool — Open-Meteo API (free, no API key required)."""

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

_SEVERE_CODES = {65, 75, 80, 81, 82, 95, 96, 99}


def _fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read().decode())


def _geocode(destination: str) -> dict | None:
    """Geocode via Nominatim; tries India-scoped search first, then global."""
    for query, cc in [(f"{destination}, India", "IN"), (destination, None)]:
        params: dict = {"q": query, "format": "json", "limit": 1, "addressdetails": 1}
        if cc:
            params["countrycodes"] = cc.lower()
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
            }
    return None


def get_weather_forecast(destination: str, start_date: str, end_date: str) -> dict:
    """Fetch weather for the trip period using Open-Meteo (no API key needed).

    Uses live 16-day forecast when dates are within range; falls back to last
    year's historical data (Open-Meteo archive) for dates further out.

    Args:
        destination: City name e.g. "Goa", "Manali". For international cities
            include country: "Bali, Indonesia".
        start_date: YYYY-MM-DD
        end_date: YYYY-MM-DD

    Returns:
        Dict with daily_forecast, summary, clothing_recommendation, activity_suggestion.
    """
    print(f"\n🌤️  get_weather_forecast | {destination} | {start_date} → {end_date}")

    loc = _geocode(destination)
    if not loc:
        return {"error": f"Could not locate '{destination}'", "destination": destination}

    lat, lon = loc["latitude"], loc["longitude"]
    city_name = loc["name"]
    country = loc["country"]

    try:
        sd = date.fromisoformat(start_date)
        ed = date.fromisoformat(end_date)
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD.", "destination": destination}

    today = date.today()
    historical = (sd - today).days > 16

    if historical:
        # Use same dates from last year as a climate proxy
        hist_sd = sd.replace(year=sd.year - 1)
        hist_ed = ed.replace(year=ed.year - 1)
        url = (
            "https://archive-api.open-meteo.com/v1/archive?"
            + urllib.parse.urlencode({
                "latitude": lat, "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
                "timezone": "auto",
                "start_date": hist_sd.isoformat(),
                "end_date": hist_ed.isoformat(),
            })
        )
    else:
        url = (
            "https://api.open-meteo.com/v1/forecast?"
            + urllib.parse.urlencode({
                "latitude": lat, "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
                "timezone": "auto",
                "start_date": start_date,
                "end_date": min(ed, today + timedelta(days=15)).isoformat(),
            })
        )

    try:
        daily = _fetch_json(url).get("daily", {})
    except Exception as e:
        return {"error": f"Forecast fetch failed: {e}", "destination": destination}

    raw_dates = daily.get("time", [])
    max_temps = daily.get("temperature_2m_max", [])
    min_temps = daily.get("temperature_2m_min", [])
    precips = daily.get("precipitation_sum", [])
    codes = daily.get("weathercode", [])

    # Remap historical dates to the actual trip year
    year_shift = (sd.year - hist_sd.year) if historical else 0

    forecast_days = []
    for i, d in enumerate(raw_dates):
        if historical and year_shift:
            y, mo, day = d.split("-")
            d = f"{int(y) + year_shift}-{mo}-{day}"
        code = int(codes[i]) if i < len(codes) else 0
        forecast_days.append({
            "date": d,
            "condition": _WMO_DESCRIPTIONS.get(code, f"Code {code}"),
            "max_temp_c": round(max_temps[i], 1) if i < len(max_temps) and max_temps[i] is not None else None,
            "min_temp_c": round(min_temps[i], 1) if i < len(min_temps) and min_temps[i] is not None else None,
            "precipitation_mm": round(precips[i], 1) if i < len(precips) and precips[i] else 0,
            "severe": code in _SEVERE_CODES,
            "source": "historical_estimate" if historical else "forecast",
        })

    severe_days = [d for d in forecast_days if d["severe"]]
    temps = [d["max_temp_c"] for d in forecast_days if d["max_temp_c"] is not None]
    avg_max = round(sum(temps) / len(temps), 1) if temps else None

    if avg_max is None:
        clothing = "Check local forecasts closer to the trip date."
    elif avg_max >= 30:
        clothing = "Hot — light breathable clothing, sunscreen, hat essential."
    elif avg_max >= 22:
        clothing = "Warm — light clothes with a layer for evenings."
    elif avg_max >= 15:
        clothing = "Mild — mix of light and warm layers."
    else:
        clothing = "Cool — warm layers, jacket recommended."
    if any(d["precipitation_mm"] > 5 for d in forecast_days):
        clothing += " Rain gear or umbrella advised."

    n = len(forecast_days)
    ns = len(severe_days)
    if n == 0:
        activity_note = "No forecast data available — plan for typical seasonal weather."
    elif ns == 0:
        activity_note = "All days look great for outdoor activities."
    elif ns >= n // 2:
        activity_note = f"{ns} of {n} days have severe weather — plan indoor backup activities."
    else:
        activity_note = f"{n - ns} good days for outdoors; {ns} day(s) may need indoor alternatives."

    print(f"   → avg max {avg_max}°C | {ns} severe day(s) | {n} days")
    return {
        "destination": f"{city_name}, {country}".strip(", "),
        "period": f"{start_date} to {end_date}",
        "data_source": "historical_estimate (last year same dates)" if historical else "live_forecast",
        "daily_forecast": forecast_days,
        "summary": {"avg_max_temp_c": avg_max, "severe_weather_days": ns, "total_days": n},
        "clothing_recommendation": clothing,
        "activity_suggestion": activity_note,
    }
