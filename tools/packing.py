"""Packing Agent — LLM-based personalized packing list.

Generates a categorized packing checklist based on destination, weather,
activities, trip duration, and user packing preferences from memory.
"""

import os
from langchain_openai import ChatOpenAI

_llm: "ChatOpenAI | None" = None


def _get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model=os.environ.get("FAST_MODEL", "gpt-4.1-mini"),
            temperature=0.3,
        )
    return _llm


def create_packing_list(
    destination: str,
    travel_date: str,
    return_date: str,
    duration_days: int,
    weather_summary: str,
    planned_activities: str,
    carry_on_only: bool = False,
    needs_adapter: bool = False,
    special_requirements: str = "",
) -> str:
    """Packing Agent: Generate a personalized packing checklist.

    Creates a smart, no-bloat packing list tailored to the destination climate,
    weather forecast, planned activities, and trip duration. Avoids obvious
    everyday items. Includes destination-specific pro tips.

    Args:
        destination: Trip destination, e.g. "Goa".
        travel_date: Departure date YYYY-MM-DD.
        return_date: Return date YYYY-MM-DD.
        duration_days: Trip length in days.
        weather_summary: Weather forecast summary (from Weather Agent).
        planned_activities: Activities from the itinerary, e.g. "beach, nightlife, markets".
        carry_on_only: If True, optimize list for carry-on only travel.
        needs_adapter: If True, include travel adapter in electronics section.
        special_requirements: Any special packing needs (medication, gear, etc.).

    Returns:
        Formatted markdown packing list with categorized sections and Pro Tips.
    """
    print(f"\n🎒  create_packing_list | {destination} | {duration_days} days | carry_on={carry_on_only}")

    luggage_note = "carry-on bag only — optimize for 7kg cabin baggage" if carry_on_only else "checked + cabin luggage allowed"
    adapter_note = "Include international travel adapter." if needs_adapter else ""

    prompt = f"""You are the Packing Agent for a travel planning system. Generate a concise,
practical packing list with zero bloat.

Trip details:
- Destination: {destination}
- Dates: {travel_date} to {return_date} ({duration_days} days)
- Weather: {weather_summary}
- Planned activities: {planned_activities or "sightseeing, beach, dining"}
- Luggage constraint: {luggage_note}
- Special requirements: {special_requirements or "none"}
{adapter_note}

Rules:
- NO obvious everyday items (toothbrush, soap — they know)
- NO generic filler items
- Be specific to the destination and activities
- For a beach destination: include beach-specific items
- For a hill station: include cold-weather specific items
- If weather has rain risk: include rain gear
- Keep clothing recommendations realistic for the duration

Format as:

## Packing List — {destination} ({duration_days} days)

### 👕 Clothing
- [specific items based on weather, activities, duration]

### 🧴 Essentials
- [documents, money, medication — destination-specific]

### 📱 Electronics & Accessories
- [phone, charger, power bank — only relevant items]

### 🏖️ Activity Gear
- [activity-specific only — beach kit, hiking gear, etc.]

### 💊 Health & Safety
- [destination-specific — mosquito repellent, sunscreen SPF, etc.]

### 💡 Pro Tips
1. [destination-specific hack]
2. [destination-specific hack]
3. [destination-specific hack]

Keep the whole list under 40 items total."""

    response = _get_llm().invoke(prompt)
    packing_list = response.content.strip()
    print(f"   → packing list generated ({len(packing_list.split(chr(10)))} lines)")
    return packing_list
