"""Live smoke test against the REAL UN News / GDELT services.

Run from the backend folder (venv active):

    python scripts/smoke_test.py                 # check the real sources directly
    python scripts/smoke_test.py --api           # ...and a running server on :8000
    python scripts/smoke_test.py --api http://127.0.0.1:8000

Nothing here is mocked. It tells you what actually works from YOUR machine.
GDELT may legitimately answer 429; that is reported, not treated as a crash.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests  # noqa: E402

from app.services import event_sources as es  # noqa: E402
from app.services.classifier import classify_event  # noqa: E402

results = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))


print("\n== 1. Sources, called directly ==")
un = es.fetch_un_news(5)
check("UN News returns articles", len(un) > 0, f"{len(un)} articles")
for a in un[:3]:
    print(f"     - {a['published']}  {a['title'][:80]}")
if un:
    print(f"     topic tags on first UN article: {un[0]['topics'] or 'none provided by feed'}")
    check("UN articles have ISO dates", all(a["published"] for a in un))

gd = es.fetch_gdelt_news(5)
gd_status = es.get_source_status()[1]
print(f"     GDELT status: {gd_status['status']}"
      + (f" - {gd_status['lastError']}" if gd_status["lastError"] else ""))
print(f"     [INFO] GDELT returned {len(gd)} articles (optional source; a 429 is not a failure)")
for a in gd[:3]:
    print(f"     - {a['published']}  {a['title'][:80]}  [publisher country: {a['source_country']}]")

print("\n== 2. Combined feed + classification ==")
combined = es.fetch_all_events(20)
check("Combined feed is not empty", len(combined) > 0, f"{len(combined)} unique articles")
dates = [a["published"] or "" for a in combined]
check("Sorted newest first", dates == sorted(dates, reverse=True))
for a in combined[:8]:
    c = classify_event(a["title"], a["description"], a["topics"])
    print(f"     {c.severity:<8} {c.category:<24} {a['title'][:70]}")
print("     ^ eyeball these: do the labels look sensible? Report any that look wrong.")

if "--api" in sys.argv:
    idx = sys.argv.index("--api")
    base = sys.argv[idx + 1] if len(sys.argv) > idx + 1 and sys.argv[idx + 1].startswith("http") else "http://127.0.0.1:8000"
    print(f"\n== 3. Running API at {base} ==")

    import time

    def get(path):
        return requests.get(base + path, timeout=60)

    r = get("/")
    check("GET /", r.status_code == 200)
    r = get("/health")
    check("GET /health", r.status_code == 200 and r.json() == {"status": "healthy"})

    started = time.time()
    r = get("/api/events")
    body = r.json() if r.ok else []
    print(f"     [INFO] first /api/events took {time.time() - started:.1f}s")
    check("GET /api/events -> 200 + array", r.ok and isinstance(body, list), f"{len(body)} events")
    check("X-Total-Count header present", "X-Total-Count" in r.headers, r.headers.get("X-Total-Count", ""))
    if body:
        need = {"id", "title", "summary", "url", "occurredAt", "source", "category", "severity", "countryId"}
        check("event has contract fields", need <= set(body[0]), f"missing: {need - set(body[0])}")
        check("every event has a source URL", all(e["url"] for e in body))
        check("no event has an invented country", all(e["countryId"] is None for e in body))

    r = get("/api/events?limit=5")
    check("limit=5", r.ok and len(r.json()) <= 5)
    r = get("/api/events?category=Environmental")
    check("category=Environmental", r.ok and all(e["category"] == "Environmental" for e in r.json()),
          f"{len(r.json())} events")
    r = get("/api/events?severity=High")
    check("severity=High", r.ok and all(e["severity"] == "high" for e in r.json()), f"{len(r.json())} events")
    check("category=Sports -> 422", get("/api/events?category=Sports").status_code == 422)
    check("limit=0 -> 422", get("/api/events?limit=0").status_code == 422)
    r = get("/api/events/status")
    check("GET /api/events/status", r.ok, str([(s["source"], s["status"]) for s in r.json()]))

    started = time.time()
    r = get("/api/countries")
    took = time.time() - started
    countries = r.json() if r.ok else []
    check("GET /api/countries -> list", r.ok and len(countries) >= 150, f"{len(countries)} countries, {took:.1f}s")
    if r.headers.get("X-Data-Warnings"):
        print(f"     [INFO] X-Data-Warnings: {r.headers['X-Data-Warnings']}")
    if countries:
        need = {"id", "code", "name", "region", "position", "populationM", "gdpB", "indicators", "dataYears", "flag"}
        check("country has frontend fields", need <= set(countries[0]), f"missing: {need - set(countries[0])}")
        check("countries have coordinates", sum(1 for c in countries if c["position"]) >= 0.9 * len(countries))
        check("all regions are the frontend's six", {c["region"] for c in countries} <= {
            "Asia", "Europe", "Africa", "North America", "South America", "Oceania", None})
        filled = sum(1 for c in countries if c["populationM"] is not None)
        check("population filled for most countries", filled >= 0.8 * len(countries), f"{filled}/{len(countries)}")
        india = next((c for c in countries if c["id"] == "IN"), None)
        if india:
            print(f"     India: pop {india['populationM']}M, GDP ${india['gdpB']}B, region {india['region']}, "
                  f"position {india['position']}")
    r = get("/api/countries?q=india")
    check("search q=india (India ranked first)", r.ok and bool(r.json()) and r.json()[0]["id"] == "IN",
          str([c["name"] for c in r.json()][:3]))
    check("search by alpha-3 q=USA", [c["id"] for c in get("/api/countries?q=USA").json()] == ["US"])
    check("region=Oceania filter", all(c["region"] == "Oceania" for c in get("/api/countries?region=Oceania").json()))
    check("region=Atlantis -> 422", get("/api/countries?region=Atlantis").status_code == 422)

    for code in ("IND", "USA"):
        started = time.time()
        r = get(f"/api/countries/{code}/profile")
        took = time.time() - started
        body = r.json() if r.ok else {}
        check(f"GET /api/countries/{code}/profile", r.ok and "indicators" in body, f"HTTP {r.status_code}, {took:.1f}s")
        if r.ok:
            avail = [k for k, v in body["indicators"].items() if v["status"] == "available"]
            check(f"{code}: at least 5 indicators available", len(avail) >= 5, f"{len(avail)}/{len(body['indicators'])}")
            for m in body["missing"]:
                print(f"     missing: {m['key']:<22} {m['status']:<8} {m['reason'] or ''}")
            print(f"     identity: {body['identity']['name']}, {body['identity']['region']} / "
                  f"{body['identity']['subregion']}, capital {body['identity']['capital']}")
    started = time.time()
    get("/api/countries/IND/profile")
    check("second profile call is fast (cached)", time.time() - started < 2.0, f"{time.time() - started:.2f}s")
    check("alpha-2 accepted: /api/countries/IN/profile", get("/api/countries/IN/profile").status_code == 200)
    check("invalid country code -> 404", get("/api/countries/XXX/profile").status_code == 404)
    check("unknown country -> 404 (was 200)", get("/api/countries/ZZZ").status_code == 404)

print(f"\n{sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
