# India vs World API

Status: **backend complete.** Frontend integration changes are listed at the end and are **not** implemented
(the frontend was not modified).

## Purpose

Compare India with other countries (or any 2 to 5 countries) on 16 World Bank indicators across three
dimensions: economic, social development and environmental. The API returns **transparent analytical data**,
not a verdict:

* every value keeps its unit, reporting year, source, World Bank code and status;
* differences from a baseline, per-indicator ordering, highest/lowest and data coverage are calculated;
* there is **no composite score, no development index and no overall country ranking**. GDP and population are
  labelled as *contextual* (size), never as better or worse;
* nothing is estimated or filled in. A missing value is `null` with a status that says why.

It is built on the existing services: `worldbank.INDICATORS` (the one indicator registry),
`worldbank.fetch_country_indicators` (parallel fetch, cache, stale fallback, deadline),
`country_data.find_country` (identity) and `country_profile.build_profile`. There is no second cache and no
second registry.

## Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/compare?countries=IND,USA,BRA` | Compare 2 to 5 countries |
| `GET /api/compare/indicators` | Indicator catalogue (no upstream calls) |

### `GET /api/compare`

| Parameter | Required | Description |
|---|---|---|
| `countries` | yes | Comma-separated ISO 3166-1 **alpha-2 or alpha-3** codes, case-insensitive, spaces allowed. 2 to 5 **distinct** countries. `IN` and `IND` are the same country and count once. |
| `baseline` | no | Country the differences are measured from (alpha-2 or alpha-3; must be one of `countries`). Default: **India (`IND`) when it is selected, otherwise the first country listed** (a warning says so). |

Country codes in the response are always **alpha-3** (as in the original endpoint), whichever format was sent.

Limits: minimum **2**, maximum **5** distinct countries. At most 12 codes may appear in the query string.

### `GET /api/compare/indicators`

Returns the catalogue described under [Indicator catalogue](#indicator-catalogue).

## Response structure

Values below are **illustrative** (they show the shape, they are not real statistics). Real values come from
the World Bank at request time.

```jsonc
{
  "source": "World Bank Open Data",

  // Backward compatible with the original endpoint: comparison[ISO3][indicatorKey].{year, value}
  // plus the full set of fields for every indicator.
  "comparison": {
    "IND": {
      "gdp": {
        "key": "gdp",
        "value": 1000000000000,
        "year": "2024",
        "label": "GDP",
        "unit": "current US$",
        "group": "economic",
        "source": "World Bank Open Data",
        "sourceCode": "NY.GDP.MKTP.CD",
        "indicatorName": "GDP (current US$)",
        "status": "available",            // available | no_data | error | pending
        "stale": false,                   // true: refresh failed, last good cached value served
        "error": null,                    // reason when status is error / pending
        "sourceLastUpdated": "2026-10-08",
        "fetchedAt": "2026-11-26T10:00:00Z"
      }
      // ... 15 more indicators, in registry order
    },
    "USA": { /* same shape */ }
  },

  "countries": ["IND", "USA"],            // alpha-3, request order, duplicates removed
  "baseline": { "country": "IND", "name": "India", "basis": "default_india" },
                                          // basis: default_india | requested | first_country

  "countryMetadata": {
    "IND": {
      "id": "IN", "code": "IND", "alpha2": "IN", "alpha3": "IND",
      "name": "India", "region": "Asia", "subregion": "Southern Asia", "capital": "New Delhi",
      "latitude": 20.0, "longitude": 77.0, "position": [20.0, 77.0],
      "flag": "https://.../in.svg", "flagEmoji": "🇮🇳",
      "metadataSource": "REST Countries", "isBaseline": true
    }
  },

  "indicatorMetadata": [ /* the full catalogue, see below */ ],

  "analytics": {
    "gdp": {
      "key": "gdp", "label": "GDP", "unit": "current US$", "group": "economic",
      "direction": "contextual",          // higher_is_better | lower_is_better | contextual
      "differenceUnit": "current US$",    // "percentage points" for % indicators
      "comparable": true,                 // at least two countries have a usable value
      "baseline": { "country": "IND", "value": 1000000000000, "year": "2024", "available": true },
      "values": [
        {
          "country": "USA", "value": 3000000000000, "year": "2025", "status": "available",
          "stale": false, "usable": true, "reason": null, "isBaseline": false,
          "absoluteDifference": 2000000000000,   // value - baseline value, in differenceUnit
          "percentDifference": 200.0,            // (value - baseline) / |baseline| * 100
          "percentDifferenceNote": null,         // baseline_is_zero | baseline_unavailable | value_unavailable
          "yearDifference": 1,                   // reporting year minus the baseline's year
          "comparedWithBaseline": "higher",      // higher | lower | equal
          "performanceVsBaseline": null,         // better | worse | same (directional indicators only)
          "valueRank": 1,                        // 1 = highest value (ties share a rank)
          "performanceRank": null                // 1 = best (directional indicators only)
        }
      ],
      "orderedByValue": ["USA", "IND"],          // highest value first; says nothing about "better"
      "orderedBestToWorst": null,                // only for directional indicators
      "highest": { "country": "USA", "value": 3000000000000, "year": "2025", "tie": false },
      "lowest":  { "country": "IND", "value": 1000000000000, "year": "2024", "tie": false },
      "coverage": {
        "requested": 2, "available": 2, "ratio": 1.0,
        "countriesWithData": ["IND", "USA"],
        "countriesMissing": []                   // [{country, status, reason, detail}]
      },
      "years": { "IND": "2024", "USA": "2025" },
      "yearsDiffer": true,
      "notes": ["Reporting years differ between countries; differences mix different years."]
    }
  },

  "dataQuality": {
    "IND": {
      "total": 16, "available": 16, "noData": 0, "error": 0, "pending": 0, "stale": 0,
      "coverage": 1.0, "complete": true, "staleIndicators": [],
      "missing": []                              // [{key, status, reason}] for every unavailable indicator
    }
  },

  "dataStatus": "partial",                       // complete | partial
  "warnings": [
    "Reporting years differ for GDP: IND 2024, USA 2025."
  ],
  "lastUpdated": "2026-11-26T10:00:00Z"          // oldest fetch time among the countries
}
```

### Response headers

| Header | When |
|---|---|
| `X-Data-Warnings` | `warnings` is not empty. ASCII, truncated to 1000 characters. |
| `X-Data-Status` | `dataStatus` is `partial`. |

Both are already listed in the CORS `expose_headers`.

## How differences are calculated

For each indicator, over the countries that have a **usable** value:

| Quantity | Rule |
|---|---|
| `absoluteDifference` | `value - baseline value`, in the indicator's unit (percentage points for `%` indicators). |
| `percentDifference` | `(value - baseline) / abs(baseline) * 100`, rounded to 2 decimals. Using `abs(baseline)` means a positive number always means "above the baseline", even when the baseline is negative (e.g. GDP growth). **Never calculated when the baseline is zero or unavailable**: it is `null` and `percentDifferenceNote` says why. A zero *value* is a real value and is compared normally (-100% when the baseline is positive). |
| `orderedByValue` | Highest value first. Ties are broken by country code. |
| `orderedBestToWorst` | Only for `higher_is_better` / `lower_is_better` indicators; `null` for contextual ones. |
| `valueRank`, `performanceRank` | Competition ranking (1, 1, 3). `performanceRank` is `null` for contextual indicators. |
| `highest`, `lowest` | Only when at least two countries have usable values. `tie: true` when another country has the exact same value. |
| `coverage` | How many of the selected countries have a usable value, and which are missing and why. |

A value is **usable** when its status is `available`, it is a finite number, and its unit equals the unit in
the indicator registry. Anything else (`no_data`, `error`, `pending`, wrong unit, invalid value) stays visible in
`values` with `usable: false` and a `reason`, and is excluded from every calculation. Values of different units
are never compared. A malformed upstream value (NaN, a string, a boolean) is reported as `status: "error"`
with an explanation, never coerced into a number.

There is no average, median, score or ranking across indicators or across the whole set of countries.

### Reporting years

World Bank indicators are annual and countries report in different years (for example, survey-based
poverty figures can be several years old). Every country-indicator pair keeps its own `year`.

* `years` lists the reporting year per country; `yearsDiffer` is true when the usable values come from different years;
* `yearDifference` is each country's year minus the baseline's year;
* a warning is added per indicator whose years differ. Treat such differences as "latest available", not as a same-year comparison.

## Indicator catalogue

`GET /api/compare/indicators` returns `{source, count, categories, indicators}`. The data comes from the
`worldbank.INDICATORS` registry; only the reading of a difference (`direction`, `interpretation`) and chart
formatting hints are added.

| Key | Label | Unit | World Bank code | SDGs | Direction |
|---|---|---|---|---|---|
| **Economic** | | | | | |
| `gdp` | GDP | current US$ | `NY.GDP.MKTP.CD` | 8 | contextual |
| `gdp_per_capita` | GDP per capita | current US$ | `NY.GDP.PCAP.CD` | 8 | higher is better |
| `gdp_growth` | GDP growth | annual % | `NY.GDP.MKTP.KD.ZG` | 8 | contextual |
| `population` | Population | people | `SP.POP.TOTL` | | contextual |
| `inflation` | Inflation, consumer prices | annual % | `FP.CPI.TOTL.ZG` | 8 | contextual |
| `unemployment` | Unemployment | % of labour force | `SL.UEM.TOTL.ZS` | 8 | lower is better |
| **Social** | | | | | |
| `life_expectancy` | Life expectancy at birth | years | `SP.DYN.LE00.IN` | 3 | higher is better |
| `school_enrollment` | Secondary school enrollment | % gross | `SE.SEC.ENRR` | 4 | higher is better |
| `poverty_rate` | Poverty headcount ratio (international poverty line) | % of population | `SI.POV.DDAY` | 1 | lower is better |
| `undernourishment` | Prevalence of undernourishment | % of population | `SN.ITK.DEFC.ZS` | 2 | lower is better |
| `drinking_water` | Safely managed drinking water | % of population | `SH.H2O.SMDW.ZS` | 6 | higher is better |
| `internet_use` | Individuals using the Internet | % of population | `IT.NET.USER.ZS` | 9 | higher is better |
| **Environmental** | | | | | |
| `co2_emissions` | CO2 emissions per capita (excl. LULUCF) | t CO2e per capita | `EN.GHG.CO2.PC.CE.AR5` | 13 | lower is better |
| `renewable_electricity` | Renewable electricity output | % of total electricity output | `EG.ELC.RNEW.ZS` | 7 | higher is better |
| `pm25` | PM2.5 air pollution, mean annual exposure | µg/m³ | `EN.ATM.PM25.MC.M3` | 11 | lower is better |
| `forest_area` | Forest area | % of land area | `AG.LND.FRST.ZS` | 15 | contextual |

Each catalogue entry:

```json
{
  "key": "internet_use", "label": "Individuals using the Internet", "unit": "% of population",
  "category": "social", "worldBankCode": "IT.NET.USER.ZS", "sdgs": [9],
  "source": "World Bank Open Data",
  "direction": "higher_is_better",
  "interpretation": "Share of people who used the Internet in the last three months.",
  "differenceUnit": "percentage points",
  "format": { "kind": "percent", "decimals": 1, "prefix": "", "suffix": "%", "compact": false },
  "chart": { "axisLabel": "Individuals using the Internet (% of population)", "canBeNegative": false, "recommendedChart": "bar" }
}
```

`format.kind` is one of `currency`, `count`, `percent`, `years`, `tonnes_per_capita`, `concentration`, `number`.
`direction` meanings: `higher_is_better` / `lower_is_better` (a difference has a clear reading, with the caveats in
`interpretation`) and `contextual` (size or a measure with no better/worse reading, for example GDP, population,
inflation, GDP growth, forest area). The codes of the registry are used as is; the World Bank may report
nothing for some of them for some countries, which shows up as `no_data`.

## Data sources

| Data | Source |
|---|---|
| Indicator values, units, years | World Bank Open Data API (`api.worldbank.org/v2`) |
| Country identity, region, capital, coordinates, flag | REST Countries (v5), with the project's snapshot / pycountry fallback |

## Caching and performance

* Indicator values are cached per `country:indicator` by the World Bank service (24 h by default,
  `WORLDBANK_CACHE_SECONDS`). Country metadata is cached by `country_data`. The comparison adds **no cache of
  its own**: a repeated or overlapping comparison (`IND,USA` then `IND,USA,BRA`) only fetches what is missing.
* Errors are not cached, so the next request retries. If a refresh fails and an older good value exists, it is
  returned with `stale: true`.
* Concurrency is bounded at two levels: at most 5 countries are processed at a time (one shared pool), and the
  World Bank service's own shared pool (8 workers) limits upstream requests.
* Each country honours the World Bank service's deadline (`WORLDBANK_PROFILE_DEADLINE`, default 12 s,
  must stay <= 15). An indicator not finished by then is `pending` (it keeps loading in the background; the next
  request finds it cached). Countries load in parallel, so a 5-country comparison waits about one deadline, not five.
* Reliability settings are unchanged: timeout <= 5 s, retries >= 2.

## Missing-data behaviour

A comparison never fails because some indicators are unavailable.

* Each indicator keeps its status: `available`, `no_data` (World Bank has no value), `error` (could not be fetched),
  `pending` (still loading).
* `dataQuality[country]` counts each status and lists every missing indicator with its reason.
* `analytics[indicator].coverage` shows which countries have data for that indicator.
* `warnings` summarise gaps per country, stale values, differing reporting years, unusable values and a
  non-India baseline.
* `dataStatus` is `partial` unless every indicator of every country is available and fresh.
* HTTP 502 happens **only** when every indicator of every country failed or is still loading.

## Error responses

All errors use FastAPI's `{"detail": "..."}` body.

| Status | When | Example `detail` |
|---|---|---|
| 400 | Fewer than 2 or more than 5 distinct countries (after removing duplicates), more than 12 codes, or `baseline` not among the selected countries | `Please provide between 2 and 5 countries (got 1 distinct)` |
| 404 | A country code (or `baseline`) is not a known ISO alpha-2/alpha-3 code | `Invalid country code: ZZZ, 12` |
| 422 | `countries` parameter missing | FastAPI validation error |
| 502 | Nothing could be loaded from the World Bank yet | `No World Bank data could be loaded yet. Retry in a few seconds.` |

The 400 and 404 messages keep the prefixes of the original endpoint
(`Please provide between 2 and 5 countries`, `Invalid country code`).

## PowerShell examples

Start the API from the `backend` folder:

```powershell
cd C:\path\to\UN-NEXUS-AI\backend
.\venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --port 8000
```

In a second PowerShell window:

```powershell
$base = "http://127.0.0.1:8000/api"

# India vs USA
$r = Invoke-RestMethod "$base/compare?countries=IND,USA"
$r.countries
$r.comparison.IND.gdp_per_capita | Format-List
$r.warnings

# India vs USA vs China, alpha-2 and alpha-3 mixed, duplicates ignored
$r = Invoke-RestMethod "$base/compare?countries=in,USA,CN,usa"
$r.countries            # IND USA CHN

# Five countries, Brazil as the baseline
$r = Invoke-RestMethod "$base/compare?countries=IND,USA,CHN,BRA,DEU&baseline=BRA"
$r.baseline

# One indicator: values, differences from the baseline, ordering and year mismatches
$r = Invoke-RestMethod "$base/compare?countries=IND,USA,CHN"
$r.analytics.life_expectancy.values | Format-Table country, value, year, absoluteDifference, percentDifference, performanceVsBaseline
$r.analytics.life_expectancy.orderedBestToWorst
$r.analytics.pm25.yearsDiffer

# What is missing, per country
$r.dataQuality.IND.missing
$r.dataQuality.USA | Format-List total, available, noData, error, pending, stale, coverage

# Indicator catalogue
$c = Invoke-RestMethod "$base/compare/indicators"
$c.indicators | Format-Table key, unit, category, worldBankCode, direction

# Errors: PowerShell raises on 4xx/5xx; read the status and message like this
try { Invoke-RestMethod "$base/compare?countries=IND" } catch { $_.Exception.Response.StatusCode.value__; $_.ErrorDetails.Message }
try { Invoke-RestMethod "$base/compare?countries=IND,ZZZ" } catch { $_.Exception.Response.StatusCode.value__; $_.ErrorDetails.Message }

# Response headers
(Invoke-WebRequest "$base/compare?countries=IND,USA").Headers["X-Data-Status"]
```

Run the tests:

```powershell
cd C:\path\to\UN-NEXUS-AI\backend
.\venv\Scripts\Activate.ps1
python -m pytest -q
python -m pytest tests\test_comparison.py tests\test_comparison_api.py -q
```

## Limitations

* The registry's World Bank codes for the indicators added after the original profile (for example
  `SI.POV.DDAY`, `SN.ITK.DEFC.ZS`, `SH.H2O.SMDW.ZS`, `EN.ATM.PM25.MC.M3`) have not been confirmed live by this
  project (see the note in `worldbank.py`). If the World Bank returns nothing, the indicator is `no_data` or
  `error`, never guessed.
* Poverty, undernourishment and drinking-water figures are survey- or model-based and often several years old.
* Everything depends on two external services (World Bank and REST Countries). The World Bank being slow
  produces `pending`/`error`/`stale` entries rather than a failed request; REST Countries falls back to the
  project's snapshot.
* The comparison covers the 16 registry indicators. Frontend metrics that are not in the registry (see below)
  need to be added to `worldbank.INDICATORS` first.

## Frontend integration (NOT implemented; for your information)

`frontend/src/pages/IndiaVsWorld/` currently renders hand-entered **sample data** (`data/comparisonData.js`,
`data/countries.js`) and does not call the API. Changes it would need, none of which were made:

1. **Fetch.** Call `GET /api/compare?countries=IND,<ids>` (the picker's ISO alpha-2 ids work as they are) and read
   `comparison[ISO3][key].value`, `.year`, `.status`. Responses use alpha-3 keys; map them with `countryMetadata[ISO3].alpha2`.
2. **Indicator mapping.**

   | Frontend id | API key | Note |
   |---|---|---|
   | `gdp` | `gdp` | API is **current US$** (frontend shows US$ billion: divide by 1e9) |
   | `gdpPc` | `gdp_per_capita` | API provides it directly; the frontend computes it from GDP and population |
   | `population` | `population` | API is **people** (frontend shows millions: divide by 1e6) |
   | `lifeExpectancy` | `life_expectancy` | |
   | `renewable` | `renewable_electricity` | |
   | `co2` | `co2_emissions` | API is t CO2e per capita, excluding LULUCF |
   | `internet` | `internet_use` | |
   | `u5mr`, `urban`, `electricity` | none | Not in the registry. Add them to `worldbank.INDICATORS` to support them. |

   API indicators the frontend does not show yet: `gdp_growth`, `inflation`, `unemployment`, `school_enrollment`,
   `poverty_rate`, `undernourishment`, `drinking_water`, `pm25`, `forest_area`.
3. **Metadata.** Use `GET /api/compare/indicators` for labels, units, `direction` (replaces the hard-coded `better`
   field: `higher_is_better`/`lower_is_better`/`contextual` map to `higher`/`lower`/`neutral`) and `format` hints. The
   frontend's own groups (`Economy`, `People & health`, ...) differ from the API categories
   (`economic`, `social`, `environmental`).
4. **Missing values.** Values can be `null`. The sample code assumes every value exists (`formatValue`, sorting,
   `Math.log`), so null handling and `status` badges (`no_data`, `error`, `pending`, `stale`) are required. Show
   `year` next to each value and surface `warnings`.
5. **Ranks, medians and the radar.** The "rank out of 24", "sample median" and the 0 to 100 "Overall profile" radar are
   computed client-side over a fixed sample. The API deliberately provides no composite score and no overall ranking;
   it provides per-indicator `valueRank` / `performanceRank` **among the selected countries only**. The "where India does
   well / lags" panels and the radar would have to be redefined on that basis (or kept as a frontend-only
   visualisation clearly labelled as relative to the selection).
6. **Badges.** Replace the "Sample data" badges with the data source and reporting year.
7. **Limit.** `MAX_COMPARE = 5` in the frontend matches the API maximum of 5 countries *in total*, India included.
   The frontend picks up to 5 countries **besides** India, so it must cap the selection at 4 or the request returns HTTP 400.
