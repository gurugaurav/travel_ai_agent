---
name: itinerary
description: Generates a detailed day-by-day travel itinerary using actual flight arrival/departure times, hotel location, weather, and budget
---

When asked to build an itinerary, use all available trip context — flight times, hotel name and area, weather forecast, daily budget, interests, and number of travelers.

## Rules
- Day 1 starts AFTER flight arrival + airport-to-hotel transfer time (not before check-in)
- Last day wraps up early enough to reach the airport with 90 min buffer before departure
- Name specific real venues: actual beach/restaurant/market/attraction names, not generic suggestions
- Include approximate INR cost per activity and local transport between spots
- Balance outdoor vs indoor activities based on the weather forecast
- For multi-city trips, show the inter-city travel day explicitly with mode and duration

## Format
Use this structure for each day:

## Day N — [Date] — [Theme e.g. "Arrival & Beach Sunset"]
**Morning (HH:MM–HH:MM):** ...
**Afternoon (HH:MM–HH:MM):** ...
**Evening (HH:MM–HH:MM):** ...
**Meals:** specific restaurant or food street recommendation with dish names
**Local transport:** auto/taxi/bike with estimated cost
**Estimated spend today:** ₹X,XXX per person

End with a **Pro Tips** section — 3–4 destination-specific hacks the user wouldn't find on a generic travel blog.
