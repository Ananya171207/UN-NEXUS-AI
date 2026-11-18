"""Live check of the World Bank + country-metadata integration (real network).

    python scripts/check_worldbank.py [COUNTRY]      (default IND)

Runs the SAME code the API uses and prints what actually came back, so you can see
which indicator codes work from this machine, how long they take, and whether the
bulk 'all countries' request behaves as expected.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import country_data, worldbank  # noqa: E402

country = (sys.argv[1] if len(sys.argv) > 1 else "IND").upper()

print(f"\n== 1. Profile indicators for {country} (parallel, as the API does) ==")
started = time.time()
results = worldbank.fetch_country_indicators(country)
print(f"   finished in {time.time() - started:.1f}s\n")
print(f"   {'key':<22} {'code':<24} {'status':<10} {'value':>16}  year  note")
for key, r in results.items():
    value = "" if r["value"] is None else f"{r['value']:,.2f}"
    note = r["error"] or (r["indicatorName"] or "")[:45]
    print(f"   {key:<22} {r['sourceCode']:<24} {r['status']:<10} {value:>16}  {r['year'] or '':<5} {note}")
ok = sum(r["status"] == "available" for r in results.values())
print(f"\n   {ok}/{len(results)} indicators available")
bad = [k for k, r in results.items() if r["status"] != "available"]
if bad:
    print(f"   not available: {', '.join(bad)}  (no_data = World Bank has none; error = fetch failed)")

print("\n== 2. Bulk request (one call for all countries) ==")
started = time.time()
data, error = worldbank.fetch_bulk(worldbank.BY_KEY["population"])
print(f"   {len(data)} entities with a population value in {time.time() - started:.1f}s"
      + (f"   ERROR: {error}" if error else ""))
print("   (expect roughly 200-270, including World Bank aggregates such as WLD)")
if country in data:
    print(f"   {country}: {data[country]}")

print("\n== 3. Country metadata (REST Countries) ==")
started = time.time()
countries = country_data.load_metadata()
print(f"   {len(countries)} countries in {time.time() - started:.1f}s; source = {countries[0]['metadataSource']}")
found = country_data.find_country(country)
if found:
    print(f"   {found['name']}: region={found['region']}, subregion={found['subregion']}, "
          f"capital={found['capital']}, position={found['position']}, flag={found['flag']}")

print("\n== 4. Raw REST Countries response (diagnostic) ==")
import requests  # noqa: E402

try:
    r = requests.get(country_data.REST_COUNTRIES_URL, params={"fields": country_data.REST_FIELDS}, timeout=15,
                     headers={"User-Agent": "UN-NEXUS-AI/1.0"})
    print(f"   HTTP {r.status_code}, content-type: {r.headers.get('content-type')}, {len(r.content)} bytes")
    body = r.json()
    print(f"   JSON is a {type(body).__name__}" + (f" of {len(body)} items" if isinstance(body, (list, dict)) else ""))
    first = body[0] if isinstance(body, list) and body else body
    print(f"   first item ({type(first).__name__}): {str(first)[:600]}")
except Exception as error:
    print(f"   ERROR {type(error).__name__}: {error}")
