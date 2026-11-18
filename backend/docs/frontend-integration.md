# Frontend integration notes (Situation Room)

Status: **the Situation Room backend is complete.** The newer endpoints (country events, SDG signals,
regions, summary, map, AI insights) are documented in `docs/situation-room-api.md`, including a
field-by-field frontend mapping. This file keeps the original contract decisions for events,
countries and profiles, which are unchanged.

Before setting `VITE_API_URL`, make the frontend changes listed at the bottom (especially 1 and 8):
without them real events are hidden and missing numbers crash the country panel.

## Contract decisions (backend adapts to the frontend, not the reverse)

| Topic | Frontend convention | Backend does |
|---|---|---|
| JSON keys | camelCase | camelCase |
| Severity | `low / moderate / high / critical` | same. Query params also accept `medium` |
| Country id | ISO alpha-2 (`IN`) | `countryId` = alpha-2, `countryCode3` also provided |
| Regions | 6: Asia, Europe, Africa, North America, South America, Oceania | same 6 (Middle East countries fall under Asia; the UN sub-region will be sent as `subregion`) |
| Event body | bare array | bare array; total count in `X-Total-Count` header |
| Time | `occurredAt` ISO string | `occurredAt` = article publication time (UTC) |

### Categories
Frontend today: Political, Economic, Environmental, Humanitarian, Development, International relations.
Backend emits those **plus** `Security`, `Health`, `Other` (real UN news is full of conflict and
health stories that the six do not cover). Spec mapping: "Conflict / Security" -> `Security`,
"Social" -> `Development`. Query aliases `conflict`, `conflict / security`, `social` are accepted.

## Event shape

```json
{
  "id": "ev-3f9a1c2b7d10",
  "title": "Airstrikes kill more than 100 civilians",
  "summary": "…or null if the source gives no description",
  "url": "https://news.un.org/en/story/…",
  "occurredAt": "2026-11-08T12:00:00Z",
  "source": "UN News",
  "sourceDomain": "news.un.org",
  "sourceCountry": null,
  "category": "Security",
  "severity": "critical",
  "topics": ["Peace and Security"],
  "classification": { "method": "rules", "aiGenerated": false, "signals": ["category/title:airstrike*", "severity/title:reported toll 100"] },
  "countryId": null, "countryCode3": null, "countryName": null,
  "region": null, "latitude": null, "longitude": null, "locationMethod": null,
  "isSample": false
}
```

`sourceCountry` is the **publisher's** country (GDELT). It is not where the event happened.
`countryId: null` means *global / unknown*. Right now that is **every** event, by design
(see "Why no country yet" in the README).

## Frontend changes needed before real events display well

I have not touched your frontend. These are the places that assume every event has a country:

1. `pages/SituationRoom/utils.js` `filterEvents`: `if (!country) return false;` silently drops
   every unmapped event. Change to keep them when no region is selected:
   ```js
   const country = countriesById[event.countryId]; // undefined for global events
   if (region !== 'All' && country?.region !== region) return false;
   ```
2. `EventFeed.jsx`, `Timeline.jsx`, `EventModal.jsx`: show `country?.name ?? 'Global / unmapped'`
   instead of `{country?.name}` (EventModal's `subtitle` template currently prints the text "undefined").
3. `data/taxonomy.js`: add `Security` and `Health` to `EVENT_CATEGORIES` (e.g. lucide `Shield`,
   `HeartPulse`) so they get filter chips and icons.
4. `EventModal.jsx`: the "Demonstration entry" badge, "Source: None - sample entry" row and the
   fine print are hard-coded. Show them only when `event.isSample`, and otherwise render
   `event.source` and a link to `event.url`.
5. `EventFeed.jsx` always renders a "Sample" badge. Render it only when `event.isSample`.
6. Page header and panel badges say "Sample data · backend not connected". Use `dataMode` from
   `situationService.js`.
7. `SituationRoom.jsx` says "of 6 regions": consistent with the backend's 6.

Tell me and I will produce these as a patch file.

## Countries

`GET /api/countries` (optional `?q=india`, `?region=Asia`) returns a bare array. Each item is the
shape `CountryPanel`/`WorldMap` already read, plus extras:

```json
{
  "id": "IN", "code": "IND", "name": "India",
  "region": "Asia", "subregion": "Southern Asia", "capital": "New Delhi",
  "position": [22.0, 79.0], "latitude": 22.0, "longitude": 79.0,
  "flag": "https://.../in.svg", "flagEmoji": "🇮🇳",
  "populationM": 1428.628, "gdpB": 3549.92,
  "indicators": { "lifeExpectancy": 67.7, "renewableShare": 21.0, "internetUse": 46.3 },
  "dataYears": { "population": "2023", "gdp": "2023", "lifeExpectancy": "2023", "renewableShare": "2022", "internetUse": "2023" },
  "metadataSource": "REST Countries"
}
```

(Numbers above are illustrative, not real output.)

* **Any value can be `null`** (World Bank has none, or a fetch failed). Never `0`.
* `position` can be `null` if coordinates are unknown.
* The response header `X-Data-Warnings` lists data problems (e.g. `population: HTTP 503`).
* `code` is the old endpoint's alpha-3 key; `region` values changed from e.g. "South Asia" to the six
  frontend regions (nothing in the frontend reads the old endpoint yet).

## Country profile

`GET /api/countries/{IN or IND}/profile`

```json
{
  "country": "IND",
  "source": "World Bank Open Data",
  "identity": { "id": "IN", "code": "IND", "name": "India", "region": "Asia", "subregion": "Southern Asia",
                "capital": "New Delhi", "latitude": 0, "longitude": 0, "position": [0, 0],
                "flag": "...", "flagEmoji": "...", "metadataSource": "REST Countries" },
  "indicators": {
    "gdp_per_capita": { "year": "2024", "value": 0, "label": "GDP per capita", "unit": "current US$",
                        "group": "economic", "source": "World Bank Open Data", "sourceCode": "NY.GDP.PCAP.CD",
                        "indicatorName": "GDP per capita (current US$)", "status": "available", "stale": false,
                        "error": null, "sourceLastUpdated": "2026-10-08", "fetchedAt": "2026-11-10T10:00:00Z" }
  },
  "groups": { "economic": ["gdp", "gdp_per_capita", "..."], "social": ["..."], "environmental": ["..."] },
  "missing": [ { "key": "school_enrollment", "status": "error", "reason": "ReadTimeout: ..." } ],
  "lastUpdated": "2026-11-10T10:00:00Z"
}
```

`status`: `available` | `no_data` (World Bank has no value) | `error` (could not be fetched) | `pending`
(still loading when the request's 12-second deadline passed; it finishes in the background, so showing
"loading, retry shortly" and re-requesting after a few seconds will find it). A single failing or slow
indicator is reported here; the endpoint still answers 200. `stale: true` = an older cached value
shown because refreshing failed. Years differ per indicator; always show `year` next to a value.
HTTP 404 = unknown country; 502 only when nothing could be loaded (every indicator `error` or `pending`).

## Frontend field -> backend source

| What the UI shows | Field | Source |
|---|---|---|
| Name, region, capital, flag | `identity.*` / country list | REST Countries (snapshot or pycountry fallback) |
| Pin position | `position` | REST Countries (country centre) |
| Population, GDP | `populationM`, `gdpB` (list); `indicators.population/gdp` (profile) | World Bank SP.POP.TOTL, NY.GDP.MKTP.CD |
| GDP per capita | `indicators.gdp_per_capita` | World Bank NY.GDP.PCAP.CD (the UI currently computes it itself) |
| Life expectancy | `indicators.lifeExpectancy` / `life_expectancy` | World Bank SP.DYN.LE00.IN |
| Renewable share | `indicators.renewableShare` / `renewable_electricity` | World Bank EG.ELC.RNEW.ZS |
| Internet use | `indicators.internetUse` / `internet_use` | World Bank IT.NET.USER.ZS |
| GDP growth, inflation, unemployment, poverty, undernourishment, drinking water, school enrollment, CO2, PM2.5, forest | profile `indicators.*` | World Bank (see `services/worldbank.py`) |
| Source / year / unit / last updated / missing | `source`, `year`, `unit`, `sourceLastUpdated`, `fetchedAt`, `missing` | per indicator |
| SDG signals | not built yet (next stage) | |
| Country events | not built yet (next stage) | |

## More frontend changes needed for countries

8. **Null-safe formatting.** `formatPopulation`, `formatGdp` and `gdpPerCapita` in `utils/format.js` crash or print
   `$NaN` on `null`. Show "Not available" when a value is null. Prefer `indicators.gdp_per_capita` from the profile
   over dividing `gdpB / populationM`.
9. **Skip markers with a null `position`** in `buildMarkers` (Leaflet throws on a null position).
10. `deriveSdgIndicators` shows "On track (demo)" labels. The backend deliberately does not judge progress; switch to
    the (coming) SDG signals endpoint and show values and years only.
11. Optionally show `dataYears` / `year` and `flag` next to the numbers.
