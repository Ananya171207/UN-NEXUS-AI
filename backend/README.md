# UN NEXUS AI - backend (Global Situation Room)

FastAPI backend for the Global Situation Room module: countries, World Bank indicators, UN News + GDELT
events, country events, SDG signals, regional monitoring, dashboard summary, map data, and an **optional**
AI layer. Everything works without an AI key.

## Run it (Windows PowerShell)

```powershell
cd backend
.\venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
pip install -r requirements.txt      # no new runtime dependencies were added in the final stages
pip install -r requirements-dev.txt  # pytest + httpx, for tests only
python -m pytest -q -rs              # automated tests: every external call is mocked, no network needed
uvicorn app.main:app --reload        # start the API
```

Swagger UI: http://127.0.0.1:8000/docs  |  Health: http://127.0.0.1:8000/health

Live check against the real services (not mocked): `python scripts/smoke_test.py` (add `--api` with the server running).

## Environment variables
All optional; see `.env.example` (copy to `.env`, never commit it). To switch the AI layer on:

```powershell
# in backend\.env
LLM_PROVIDER=gemini      # or openai
LLM_API_KEY=your-key-here
```

## Endpoints

| Endpoint | What it does |
|---|---|
| `GET /`, `GET /health` | preserved |
| `GET /api/countries`, `/{code}`, `/{code}/profile` | country list, identity, profile with 16 World Bank indicators |
| `GET /api/events` | event feed. Filters: `limit, offset, category, severity, min_severity, country`. Total in `X-Total-Count` |
| `GET /api/events/status` | health of UN News / GDELT |
| `GET /api/countries/{code}/events` | events reliably linked to one country (envelope with pagination and filters) |
| `GET /api/countries/{code}/sdg-signals` | real World Bank values grouped by SDG (no progress scores) |
| `GET /api/events/regions` | 7-region monitoring counts |
| `GET /api/situation-room/summary` | the four dashboard cards, with their definitions |
| `GET /api/events/map` | verified city markers + per-country markers |
| `GET /api/countries/{code}/insights` | data-backed facts + optional labelled AI note |
| `GET /api/events/regions/{region}/intelligence` | counts + optional labelled AI summary |
| `GET /api/events/{id}/insights` | one event: grounded summary, SDG links, classification reasoning |
| `POST /api/events/enrich` | optional: pre-compute AI labels (cached, capped) |
| `/indicators/...`, `/compare` | untouched (`/compare` belongs to another module) |

Full request/response examples and the frontend field mapping: **`docs/situation-room-api.md`**.

## Layout

```
app/
  main.py                      CORS, logging, routers
  config.py                    env-driven settings
  routes/
    events.py                  /api/events, /api/events/status
    country_events.py          /api/countries/{code}/events
    country_sdg.py             /sdg-signals, /insights
    situation.py               /events/regions, /events/map, /situation-room/summary, regional intelligence
    ai.py                      /events/{id}/insights, /events/enrich
    filters.py                 shared query parsing + the one filtered-event loader
    countries.py               original file (compare/indicators untouched)
  services/
    event_sources.py           UN News + GDELT: cache, circuit breaker, dedupe
    classifier.py              rule-based category + severity (with `signals`)
    locations.py               where did the event happen? gazetteer + cities, with evidence
    regions.py                 country -> 7 monitoring regions
    events.py                  pipeline -> event shape, filters
    monitoring.py              regions / summary / map built from ONE event list
    sdg.py, event_sdg.py       country SDG signals; event -> SDG keyword rules
    worldbank.py, country_data.py, country_profile.py   (unchanged behaviour)
    llm.py                     Gemini/OpenAI client: timeout, cooldown, hourly cap
    ai_common.py               SQLite-backed cache, grounding checks
    ai_events.py               per-event AI enrichment + feed overlay
    ai_insights.py             country insights, regional intelligence
  models/                      Pydantic schemas
tests/                         pytest/unittest suites, all external calls mocked
```

## Tests
`python -m pytest -q -rs` - nothing should be skipped. If a test is skipped, `httpx` is missing:
`pip install -r requirements-dev.txt`.

## Add to `.gitignore`
```
backend/app/data/ai_cache.sqlite3
backend/.env
```
