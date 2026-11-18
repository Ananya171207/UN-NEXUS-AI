# Situation Room API: handover and frontend mapping

Base URL (dev): `http://127.0.0.1:8000` - Swagger: `/docs`. JSON keys are camelCase. CORS allows
`http://localhost:5173` and exposes `X-Total-Count`, `X-Data-Warnings`, `X-Data-Status`.

## 1. Concepts the frontend must know

**Country id.** `countryId` is ISO alpha-2 (`SD`), the same `id` as `/api/countries`. `countryCode3` / `countryCode` is alpha-3.

**Event location is evidence-based.** `countryId` is set only when the article's own wording places the event
there (`location.evidence` quotes it). The publisher's country is never used. Events that name no country,
or several without a clear place, have `countryId: null` ("global / unmapped"). They still appear in the feed.

**Two region fields.** `region` = old 6 continental regions (unchanged; Middle East countries inside Asia/Africa).
`monitoringRegion` = the 7 regions used by regional monitoring, summary and map (adds **Middle East**:
AE BH EG IQ IR IL JO KW LB OM PS QA SA SY TR YE; these are *only* in Middle East, never also in Asia/Africa).
The `region` query parameter on the new endpoints filters by `monitoringRegion`, so the region filter in the
UI needs a **Middle East** chip.

**Severity.** `low | moderate | high | critical`. "Medium" in the brief = `moderate`; query params also accept `medium`.

**Categories.** Political, Security (= Conflict / Security), Humanitarian, Economic, Environmental, Health,
Development (= Social), International relations, Other.

**AI is always labelled.** Anything AI-written sits inside an object with `aiGenerated: true` and a `status`
(`generated | cached | disabled | unavailable | rejected | insufficient_data`). Data objects have `aiGenerated: false`
or no such flag. With no LLM key every endpoint still works (`status: "disabled"`).

## 2. Endpoints

### GET /api/countries/{code}/events
Params: `limit` (1-200, default 50), `offset`, `category`, `severity`, `min_severity`, `min_confidence` (`medium|high`).
404 unknown country; 200 with `total: 0` when none. Newest first. `X-Total-Count` header too.
```json
{"countryId":"SD","countryCode":"SDN","countryName":"Sudan","total":3,"limit":50,"offset":0,
 "events":[{"id":"ev-3f9a1c2b7d10","title":"Airstrikes kill more than 100 civilians in Sudan","summary":null,
   "url":"https://news.un.org/en/story/...","occurredAt":"2026-11-08T12:00:00Z","source":"UN News","category":"Security",
   "severity":"critical","countryId":"SD","countryName":"Sudan","region":"Africa","monitoringRegion":"Africa",
   "latitude":null,"longitude":null,"locationMethod":"gazetteer-title",
   "location":{"status":"assigned","method":"gazetteer-title","confidence":"high","precision":"country","city":null,
     "evidence":[{"field":"title","match":"Sudan","rule":"place_word"}],"candidates":["SD"]},
   "classification":{"method":"rules","aiGenerated":false,"signals":["..."]}}],
 "note":"Only events whose own wording ties them to this country are listed ..."}
```

### GET /api/countries/{code}/sdg-signals?sdg=3,7
Real World Bank values grouped by goal. **No progress scores, no on/off track.** Goals present: 1,2,3,4,6,7,8,9,11,13,15
(`goalsWithoutIndicators` lists the rest: "no indicator", not "no progress").
```json
{"countryId":"IN","countryCode":"IND","countryName":"India","dataType":"indicator_values","aiGenerated":false,
 "source":"World Bank Open Data","methodology":"...","outdatedAfterYears":5,
 "goals":[{"sdg":1,"name":"No Poverty","hasData":true,"availableCount":1,"totalCount":1,"signals":[
   {"indicatorKey":"poverty_rate","indicatorName":"...","indicatorCode":"SI.POV.DDAY","value":12.9,"year":"2021",
    "unit":"% of population","source":"World Bank Open Data","availability":"available","stale":false,"outdated":false,
    "relation":"matches_sdg_indicator","sdgIndicator":"1.1.1","explanation":"Share of people living below ...","error":null}]}]}
```
`availability`: `available | no_data | error | pending`. `value`/`year` are null unless available. `outdated` = year older than
`outdatedAfterYears`. `relation`: `matches_sdg_indicator` (same measure as the UN SDG indicator in `sdgIndicator`) or
`related_context`. 404 unknown country; 502 only if every indicator failed; `X-Data-Status` header if some still load.

### GET /api/events/regions
Filters: `category, severity, min_severity, country, min_confidence`. Always returns all 7 regions.
```json
{"regions":[{"region":"Africa","total":2,"critical":1,"high":0,"moderate":1,"low":0,"countryCount":1,"countryCodes":["SD"],
  "highestSeverity":"critical","topEvents":[{"id":"ev-...","title":"...","severity":"critical","category":"Security",
  "countryId":"SD","countryName":"Sudan","occurredAt":"...","url":"..."}]}],
 "totals":{"events":8,"withRegion":6,"withoutRegion":2,"regionsWithEvents":4},"assignmentRule":"..."}
```

### GET /api/situation-room/summary
Filters: `category, severity, min_severity, country, region, min_confidence`.
```json
{"countriesInView":{"value":195,"of":195},"eventsShown":8,"highCriticalEvents":3,"regionsWithEvents":{"value":4,"of":7},
 "severityBreakdown":{"critical":1,"high":2,"moderate":3,"low":2},"categoryBreakdown":{"Health":2,"Security":3},
 "unmappedEvents":2,"filters":{...},"definitions":{...},"warnings":[],"generatedAt":"2026-11-10T09:00:00Z"}
```
Definitions: **eventsShown** = unique events matching the filters (including unmapped ones); **highCriticalEvents** = unique
matching events that are high/critical; **regionsWithEvents** = distinct monitoring regions with at least one matching,
country-mapped event; **countriesInView** = countries in the dataset inside the selected region (all if none; 1 for a country filter).
Regions, summary, map and feed use the same filtered event list, so their numbers always agree.

### GET /api/events/map
Same filters as summary. `markers`: events with **verified city coordinates** (a curated list of unambiguous cities, only when
the city follows a place word such as "in Kyiv"). `countryMarkers`: one per country with events, at the **country centre**
(`coordinatesMean: "country_centre"`, not the event location). Events without a reliable country are in neither (see `totals`).
```json
{"markers":[{"eventId":"ev-...","title":"Fighting in Kyiv wounds dozens","latitude":50.4501,"longitude":30.5234,"precision":"city",
  "city":"Kyiv","countryId":"UA","countryCode":"UKR","countryName":"Ukraine","region":"Europe","monitoringRegion":"Europe",
  "category":"Security","severity":"high","occurredAt":"...","url":"...","locationConfidence":"high","evidence":[...]}],
 "countryMarkers":[{"countryId":"SD","countryCode":"SDN","countryName":"Sudan","latitude":15.0,"longitude":30.0,
  "coordinatesMean":"country_centre","eventCount":2,"highestSeverity":"critical","severityCounts":{...},"eventIds":["ev-..","ev-.."]}],
 "totals":{"events":8,"eventMarkers":1,"eventsWithoutCoordinates":5,"eventsWithoutCountry":2,"countriesWithoutPosition":0,"invalidCoordinatesDropped":0},"note":"..."}
```

### GET /api/countries/{code}/insights
`facts` (World Bank values + recent linked events, never AI) and `interpretation` (optional AI note, must cite fact ids).
Needs at least 3 indicator facts, otherwise `interpretation.status = "insufficient_data"`. No trends are described (only the
latest value of each indicator exists).

### GET /api/events/regions/{region}/intelligence
`development` (deterministic counts + top events) and `narrative` (optional AI summary whose points cite event ids). Needs >= 3 events.

### GET /api/events/{id}/insights
```json
{"eventId":"ev-...","aiStatus":"disabled","summary":{"aiGenerated":false,"status":"source_text","text":"<source description>","label":"Description provided by the source"},
 "classification":{"category":"Health","severity":"high","method":"rules","aiGenerated":false,"signals":["..."],"severityReason":null},
 "sdgs":[{"sdg":3,"name":"Good Health and Well-being","reason":"The headline mentions: cholera, outbreak*.","confidence":"medium","method":"rules","aiGenerated":false,"evidence":[...]}],
 "sdgMethod":"rules","sdgNote":"A link to a goal means ... not that any country's SDG progress has changed.","location":{...}}
```
With an LLM: `summary.aiGenerated: true` (only if the source has real description text and the summary adds no numbers),
SDGs carry `confidence` 0-1 and a quoted `evidence`. 404 unknown id.

### POST /api/events/enrich?limit=20
Optional. Sends up to `limit` unprocessed events (most severe first) to the LLM in batches; results are cached forever per prompt version.
`X-Admin-Token` header required if `ADMIN_TOKEN` is set. Returns `{status, requested, stored, rejected, alreadyCached, llmConfigured}`.

## 3. Frontend field mapping

| UI element | Endpoint | Fields |
|---|---|---|
| Map country pins | `/api/events/map` -> `countryMarkers` | `latitude, longitude, eventCount, highestSeverity` (pin colour), `countryId` |
| Map event pins (optional) | `/api/events/map` -> `markers` | `latitude, longitude, title, severity, url` |
| Country search / selection | `/api/countries?q=` | `id, name, region, position, flag` |
| Country profile panel | `/api/countries/{id}/profile` | unchanged |
| SDG signals panel | `/api/countries/{id}/sdg-signals` | `goals[].signals[]` - show `value`, `unit`, `year`, `source`; grey out `availability != available`; badge `outdated` |
| Country events list | `/api/countries/{id}/events` | `events[]` (same shape as the feed), `total` |
| Global event feed | `/api/events` | unchanged; `countryId` may be null |
| Category / severity filters | any events endpoint | `category`, `severity` / `min_severity` |
| Stat cards | `/api/situation-room/summary` | `countriesInView.value`, `eventsShown`, `highCriticalEvents`, `regionsWithEvents.value` (+ `.of`) |
| Regional monitoring | `/api/events/regions` | `regions[]` |
| "Read more" on an event | `event.url` | original article |
| Event detail / AI | `/api/events/{id}/insights` | `summary`, `sdgs`, `aiStatus` |

**Changes the frontend needs** (the React code was not available to me; these follow from the contracts above):
1. Handle `countryId: null` events (show as global; do not drop them).
2. Add a **Middle East** region option and use `monitoringRegion` for regional views; keep `region` for the old 6-region filter.
3. Replace any demo "On track / Off track" SDG bands with the real values from `sdg-signals` (the backend deliberately gives no progress verdict).
4. Show an "AI-generated" badge whenever `aiGenerated` is true, and the source link next to it.
5. Treat `location.confidence = "medium"` as less certain than `"high"` if you want to show it.

## 4. AI: what needs an LLM, cost, performance

| Task | Method | LLM? |
|---|---|---|
| Event country / city | gazetteer + place-word rules, evidence quoted | No. LLM only validates a quoted country for events the rules left unmapped |
| Region, SDG signals, summary numbers, map | deterministic | No |
| Event SDG links | keyword rules; LLM refines when available | Optional |
| Classification | rules; LLM overlay from cache when configured | Optional |
| Event summary, country note, regional summary | LLM, grounded and labelled | Yes (optional) |

Cost control: the feed never calls the LLM; articles are sent in batches of `AI_BATCH_SIZE`; each article is processed once
(cached by content hash + prompt version); `LLM_MAX_CALLS_PER_HOUR` is a hard cap; a failed call triggers a cooldown.
Rough size: one batch of 8 events is about 1.5k input + 1.5k output tokens, so 100 events is roughly 13 calls (~20k input and ~20k
output tokens). At flash/mini-class pricing that is on the order of cents or less, but check your provider's current prices.
Latency: `/events/{id}/insights` makes at most one call (a few seconds) the first time, then is instant from cache.

Safety: article text is passed as untrusted data; model JSON is validated field by field; summaries cannot contain numbers
absent from the source; SDG items and locations must quote the article; country/regional notes must cite real fact/event ids.
Anything failing validation is dropped and the rules-based result is used.

## 5. Persistence
- **Events**: not stored; the feed is cached in memory for 120 s. Fine for a live dashboard.
- **AI results**: stored in a small SQLite file (`app/data/ai_cache.sqlite3`, standard library, no new dependency) so paid results survive restarts. If the file cannot be used it falls back to memory.
- **Historical trends / user data**: not implemented. Needed only for "events over time" charts or accounts; that is when to add PostgreSQL (store events by id + the cached AI results).

## 6. Known limitations
- Mapped events are fewer than all news: UN News headlines often name no country; GDELT gives titles only. Stricter on purpose.
- Medium-confidence assignments ("Trump visits China" style bare mentions) are heuristics; `min_confidence=high` gives the strict list.
- Event-level coordinates exist only for about 45 curated cities. Everything else is country-level.
- Only the latest value per World Bank indicator is available: no trends or changes over time. Only 15 indicators map to SDGs (goals 1,2,3,4,6,7,8,9,11,13,15).
- Several World Bank series are not the exact official SDG indicators; `relation` says which are.
- `occurredAt` is the article's publication time, not necessarily the event time.
- Gemini/OpenAI calls could not be tested live in my environment (mocked only); default model names may need updating via `LLM_MODEL`.
- The cache is per process: with several workers each has its own.
