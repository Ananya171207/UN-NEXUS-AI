"""HTTP tests for the Situation Room endpoints. Need fastapi + httpx."""
import unittest
from types import SimpleNamespace
from unittest import mock

try:
    from fastapi.testclient import TestClient
    from app.main import app
    HAVE_FASTAPI = True
except Exception:  # pragma: no cover
    HAVE_FASTAPI = False

from app.services import ai_common, ai_events, llm
from app.services import country_data as cd
from app.services import event_sources as es
from app.services import events as svc
from app.services import worldbank as wb
from tests.fixtures_countries import COUNTRIES
from tests.helpers import article
from tests.test_sdg import results as wb_results

ARTICLES = [
    article("Airstrikes kill more than 100 civilians in Sudan", n=1, published="2026-11-08T12:00:00Z"),
    article("Cholera outbreak spreads in Sudan", "Health officials report a rapid rise in cases across several camps.", n=2, published="2026-11-07T12:00:00Z"),
    article("Floods displace thousands in Egypt", n=3, published="2026-11-06T12:00:00Z"),
    article("Fighting in Kyiv wounds dozens", n=4, published="2026-11-05T12:00:00Z"),
    article("US imposes sanctions on Iran", n=5, published="2026-11-04T12:00:00Z"),
    article("Global food prices fall", n=6, published="2026-11-03T12:00:00Z", source="GDELT", source_country="France"),
]


@unittest.skipUnless(HAVE_FASTAPI, "fastapi/httpx not installed")
class SituationApiTests(unittest.TestCase):
    def setUp(self):
        svc.clear_cache()
        es.reset_state()
        llm.reset_state()
        ai_common.set_cache(ai_common.AICache(":memory:"))
        self.client = TestClient(app)
        for p in (mock.patch.object(svc, "collect_articles", return_value=ARTICLES),
                  mock.patch.object(cd, "load_metadata", return_value=COUNTRIES),
                  mock.patch.object(wb, "fetch_country_indicators", return_value=wb_results()),
                  mock.patch.object(llm, "is_configured", return_value=False)):
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(svc.clear_cache)
        self.addCleanup(es.reset_state)
        self.addCleanup(ai_common.set_cache, ai_common.AICache(":memory:"))

    def get(self, url):
        return self.client.get(url)

    # ----- SDG signals
    def test_sdg_signals_valid_country(self):
        r = self.get("/api/countries/SD/sdg-signals")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual((body["countryId"], body["countryCode"], body["aiGenerated"]), ("SD", "SDN", False))
        g1 = next(g for g in body["goals"] if g["sdg"] == 1)
        self.assertEqual(g1["signals"][0]["indicatorCode"], "SI.POV.DDAY")
        self.assertEqual(g1["signals"][0]["source"], "World Bank Open Data")

    def test_sdg_signals_unknown_country_and_bad_filter(self):
        self.assertEqual(self.get("/api/countries/ZZ/sdg-signals").status_code, 404)
        self.assertEqual(self.get("/api/countries/SD/sdg-signals?sdg=abc").status_code, 422)
        self.assertEqual(self.get("/api/countries/SD/sdg-signals?sdg=99").status_code, 422)

    def test_sdg_signals_goal_filter(self):
        goals = self.get("/api/countries/SD/sdg-signals?sdg=3,7").json()["goals"]
        self.assertEqual([g["sdg"] for g in goals], [3, 7])

    def test_sdg_signals_missing_values_are_null(self):
        missing = wb_results(life_expectancy={"status": "no_data"})
        with mock.patch.object(wb, "fetch_country_indicators", return_value=missing):
            s = next(g for g in self.get("/api/countries/SD/sdg-signals").json()["goals"] if g["sdg"] == 3)["signals"][0]
        self.assertEqual((s["availability"], s["value"]), ("no_data", None))

    def test_sdg_signals_502_only_when_everything_failed(self):
        bad = {k: {**v, "status": "error"} for k, v in wb_results().items()}
        with mock.patch.object(wb, "fetch_country_indicators", return_value=bad):
            self.assertEqual(self.get("/api/countries/SD/sdg-signals").status_code, 502)

    # ----- regions / summary / map
    def test_regions(self):
        r = self.get("/api/events/regions")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(len(body["regions"]), 7)
        by = {x["region"]: x for x in body["regions"]}
        self.assertEqual((by["Africa"]["total"], by["Middle East"]["total"], by["Europe"]["total"]), (2, 1, 1))
        self.assertEqual(body["totals"]["withoutRegion"], 2)

    def test_regions_filters(self):
        body = self.get("/api/events/regions?category=Health").json()
        self.assertEqual(body["totals"]["events"], 1)
        self.assertEqual(self.get("/api/events/regions?severity=nonsense").status_code, 422)

    def test_summary_matches_feed_and_regions(self):
        s = self.get("/api/situation-room/summary").json()
        feed = self.get("/api/events")
        regions = self.get("/api/events/regions").json()
        self.assertEqual(s["eventsShown"], int(feed.headers["X-Total-Count"]))
        self.assertEqual(s["regionsWithEvents"], {"value": regions["totals"]["regionsWithEvents"], "of": 7})
        self.assertEqual(s["countriesInView"]["of"], len(COUNTRIES))
        self.assertEqual(s["unmappedEvents"], 2)
        self.assertEqual(s["highCriticalEvents"], s["severityBreakdown"]["critical"] + s["severityBreakdown"]["high"])

    def test_summary_filtered_and_empty(self):
        s = self.get("/api/situation-room/summary?region=Africa").json()
        self.assertEqual((s["eventsShown"], s["filters"]["region"]), (2, "Africa"))
        self.assertEqual(self.get("/api/situation-room/summary?country=sd").json()["countriesInView"]["value"], 1)
        empty = self.get("/api/situation-room/summary?country=FR").json()
        self.assertEqual((empty["eventsShown"], empty["regionsWithEvents"]["value"]), (0, 0))
        self.assertEqual(self.get("/api/situation-room/summary?region=Atlantis").status_code, 422)

    def test_summary_with_no_events_at_all(self):
        svc.clear_cache()
        with mock.patch.object(svc, "collect_articles", return_value=[]):
            r = self.get("/api/situation-room/summary")
        self.assertEqual((r.status_code, r.json()["eventsShown"]), (200, 0))

    def test_map(self):
        body = self.get("/api/events/map").json()
        self.assertEqual([m["city"] for m in body["markers"]], ["Kyiv"])
        self.assertEqual(body["markers"][0]["url"], "https://example.com/4")
        self.assertTrue(all(c["coordinatesMean"] == "country_centre" for c in body["countryMarkers"]))
        self.assertEqual(body["totals"]["eventsWithoutCountry"], 2)

    def test_map_filter_and_empty(self):
        self.assertEqual(self.get("/api/events/map?region=Africa").json()["markers"], [])
        self.assertEqual(self.get("/api/events/map?min_confidence=bad").status_code, 422)

    # ----- AI endpoints (no LLM configured: fallbacks)
    def test_event_insights_fallback(self):
        event_id = next(e["id"] for e in svc.get_events() if e["url"].endswith("/2"))
        r = self.get(f"/api/events/{event_id}/insights")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual((body["aiStatus"], body["sdgMethod"], body["summary"]["aiGenerated"]), ("disabled", "rules", False))
        self.assertEqual(body["sdgs"][0]["sdg"], 3)
        self.assertEqual(self.get("/api/events/does-not-exist/insights").status_code, 404)

    def test_enrich_disabled_and_admin_token(self):
        r = self.client.post("/api/events/enrich")
        self.assertEqual((r.status_code, r.json()["status"], r.json()["llmConfigured"]), (200, "disabled", False))
        with mock.patch("app.routes.ai.settings", SimpleNamespace(admin_token="secret")):
            self.assertEqual(self.client.post("/api/events/enrich").status_code, 403)
            self.assertEqual(self.client.post("/api/events/enrich", headers={"X-Admin-Token": "wrong"}).status_code, 403)
            self.assertEqual(self.client.post("/api/events/enrich", headers={"X-Admin-Token": "secret"}).status_code, 200)

    def test_country_insights_without_llm_returns_facts(self):
        body = self.get("/api/countries/SD/insights").json()
        self.assertEqual((body["dataType"], body["interpretation"]["status"]), ("facts", "disabled"))
        self.assertTrue(any(f["type"] == "event" for f in body["facts"]))
        self.assertEqual(self.get("/api/countries/ZZ/insights").status_code, 404)

    def test_region_intelligence(self):
        r = self.get("/api/events/regions/Africa/intelligence")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["development"]["total"], 2)
        self.assertEqual(r.json()["narrative"]["status"], "insufficient_data")
        self.assertEqual(self.get("/api/events/regions/Atlantis/intelligence").status_code, 422)

    # ----- contract / docs
    def test_swagger_lists_every_new_endpoint(self):
        paths = self.get("/openapi.json").json()["paths"]
        for path in ("/api/countries/{country_code}/events", "/api/countries/{country_code}/sdg-signals",
                     "/api/countries/{country_code}/insights", "/api/events/regions", "/api/events/map",
                     "/api/situation-room/summary", "/api/events/{event_id}/insights",
                     "/api/events/regions/{region}/intelligence", "/api/events/enrich", "/api/events"):
            self.assertIn(path, paths)

    def test_static_event_routes_are_not_shadowed(self):
        self.assertEqual(self.get("/api/events/status").status_code, 200)
        self.assertEqual(self.get("/api/events/regions").status_code, 200)
        self.assertEqual(self.get("/api/events/map").status_code, 200)

    def test_existing_contracts_unchanged(self):
        r = self.get("/api/events?limit=2")
        self.assertIsInstance(r.json(), list)
        self.assertIn("X-Total-Count", r.headers)
        for key in ("id", "title", "category", "severity", "countryId", "region", "latitude", "longitude", "classification"):
            self.assertIn(key, r.json()[0])

    def test_cors_exposes_new_header(self):
        r = self.client.get("/api/events", headers={"Origin": "http://localhost:5173"})
        self.assertIn("x-data-status", r.headers["access-control-expose-headers"].lower())


if __name__ == "__main__":
    unittest.main()
