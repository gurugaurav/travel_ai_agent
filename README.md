# ✈️ TripMind — Multi-Agent AI Travel Planner

> Plan complete trips in one prompt — flights, hotels, weather, itinerary, and packing list — powered by a team of specialized AI agents.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python) ![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B?logo=streamlit) ![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-brightgreen) ![OpenAI](https://img.shields.io/badge/LLM-GPT--4.1-black?logo=openai)

---

## What it does

TripMind takes a single natural-language travel request and coordinates a supervisor + 5 subagents to return a fully structured trip plan:

| Agent | Role |
|-------|------|
| **Supervisor** | Understands intent, coordinates agents, formats final output |
| **Planning Agent** | Budget allocation, hotel tier, trip context |
| **Flight Agent** | Real Google Flights data via `fli` scraper + SerpAPI fallback |
| **Hotel Agent** | Real Google Hotels data via `fast-hotel` |
| **Weather Agent** | 16-day forecast (Open-Meteo) + historical archive fallback |
| **Itinerary Agent** | Day-by-day plan with real venues, timings, and packing list |

### Example prompts
- *"Plan a 4-day trip from Pune to Goa in August for 2 people, budget ₹60,000"*
- *"Compare Manali vs Ladakh for a long weekend in September"*
- *"Beach trip next month, ₹80,000 budget"*

---

## Architecture

```
User → Streamlit UI → Supervisor (GPT-4.1)
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
   Planning Agent   Flight Agent    Hotel Agent
                          │               │
                    Weather Agent  Itinerary Agent
                          │
                     Final JSON → Rendered UI Cards
```

Built with **LangGraph** + **deepagents** for multi-agent orchestration and **InMemorySaver** for conversation checkpointing.

---

## Setup

### 1. Clone & install

```bash
git clone git@github.com:gurugaurav/travel_ai_agent.git
cd travel_ai_agent
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and fill in your API keys
```

| Key | Required | Where to get |
|-----|----------|--------------|
| `OPENAI_API_KEY` | Yes | [platform.openai.com](https://platform.openai.com/api-keys) |
| `TAVILY_API_KEY` | Yes | [tavily.com](https://tavily.com) — airport code lookup |
| `SERPAPI_API_KEY` | Optional | [serpapi.com](https://serpapi.com) — Google Flights fallback |
| `ARIZE_SPACE_ID` / `ARIZE_API_KEY` | Optional | [arize.com](https://arize.com) — LLM tracing |

### 3. Run

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`

---

## Project structure

```
travel_ai_agent/
├── app.py              # Streamlit UI — chat interface & card renderers
├── main.py             # CLI entry point
├── tracing.py          # Arize AX OpenTelemetry tracing setup
├── agents/
│   └── agent.py        # Supervisor + all 5 subagent definitions
├── tools/
│   ├── flights.py      # Airport code lookup (Tavily) + SerpAPI flights
│   ├── flights_fast.py # Fast flights scraper (fli — no API key needed)
│   ├── hotels.py       # Google Hotels via fast-hotel
│   └── weather.py      # Open-Meteo weather + archive API
├── skills/
│   ├── itinerary/      # Itinerary generation prompts/templates
│   └── packing/        # Packing list generation
├── memory/
│   └── AGENTS.md       # Persistent user travel profile (auto-updated)
├── .env.example        # Template — copy to .env and fill in keys
└── requirements.txt
```

---

## Features

- **Real data** — live flight prices, hotel availability, and weather forecasts (not mock data)
- **Budget-aware** — automatically splits budget across flights, hotel, food, activities, and transport
- **Memory** — remembers your home city, preferences, and past trips across sessions
- **Comparison mode** — compare 2–3 destinations side by side
- **Replanning** — if flights/hotels are over budget, agents retry with adjusted parameters
- **Structured UI** — results rendered as rich cards (flight routes, hotel details, weather, budget bar, day cards, packing grid)

---

## Tech stack

- **LLM**: GPT-4.1 via `langchain-openai`
- **Orchestration**: LangGraph + deepagents multi-agent framework
- **UI**: Streamlit
- **Flight data**: `fli` (free scraper) + SerpAPI Google Flights
- **Hotel data**: `fast-hotel`
- **Weather**: Open-Meteo (free, no key needed)
- **Airport lookup**: Tavily search
- **Tracing**: Arize AX + OpenInference LangChain instrumentation

---

## License

MIT

---

#travel #ai #multiagent #langchain #langgraph #openai #streamlit #python #traveltech #llm
