"""HTTP tests for GET /api/countries/{code}/events. Need fastapi + httpx."""
import unittest
from unittest import mock

try:
    from fastapi.testclient import TestClient
    from app.main import app
    HAVE_FASTAPI = True
except Exception:  # pragma: no cover - environment without fastapi/httpx
    HAVE_FASTAPI = False

from app.services import country_data as cd
from app.services import event_sources as es
from app.services import events as svc
from tests.fixtures_countries import COUNTRIES


def art(n, title, published, description="", source="UN News", source_country=None):
    return {"title": title, "description": description, "url": f"https://example.com/{n}",
            "published": published, "source": source, "domain": "example.com",
            "source_country": source_country, "topics": []}


ARTICLES = [
    art(1, "Airstrikes kill more than 100 civilians in Sudan", "2026-11-08T12:00:00Z"),
    art(2, "Cholera outbreak spreads in Sudan", "2026-11-07T12:00:00Z"),
    art(3, "Climate talks open in Sudan", "2026-11-06T12:00:00Z"),
    art(4, "Ukraine war pushes up grain prices", "2026-11-05T12:00:00Z"),
    art(5, "US imposes sanctions on Iran", "2026-11-04T12:00:00Z"),
    art(6, "Global food prices fall", "2026-11-03T12:00:00Z", source="GDELT", source_country="France"),
]


@unittest.skipUnless(HAVE_FASTAPI, "fastapi/httpx not installed")
class CountryEventsApiTests(unittest.TestCase):
    def setUp(self):
        svc.clear_cache()
        es.reset_state()
        self.client = TestClient(app)
        for p in (mock.patch.object(svc, "collect_articles", return_value=ARTICLES),
                  mock.patch.object(cd, "load_metadata", return_value=COUNTRIES)):
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(svc.clear_cache)
        self.addCleanup(es.reset_state)

    def test_valid_country_returns_envelope(self):
        r = self.client.get("/api/countries/SD/events")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual((body["countryId"], body["countryCode"], body["countryName"]), ("SD", "SDN", "Sudan"))
        self.assertEqual(body["total"], 3)
        self.assertEqual(len(body["events"]), 3)
        self.assertEqual(r.headers["X-Total-Count"], "3")
        self.assertEqual({e["countryId"] for e in body["events"]}, {"SD"})
        self.assertEqual(body["events"][0]["url"], "https://example.com/1")  # newest first, original URL kept
        self.assertIn("location", body["events"][0])

    def test_alpha3_and_lowercase_codes_work(self):
        self.assertEqual(self.client.get("/api/countries/sdn/events").json()["countryId"], "SD")
        self.assertEqual(self.client.get("/api/countries/sd/events").json()["total"], 3)

    def test_unknown_country_is_404(self):
        self.assertEqual(self.client.get("/api/countries/ZZ/events").status_code, 404)
        self.assertEqual(self.client.get("/api/countries/NOTACODE/events").status_code, 404)

    def test_known_country_without_events_is_200_and_empty(self):
        r = self.client.get("/api/countries/FR/events")  # only the publisher is French
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.json()["total"], r.json()["events"]), (0, []))

    def test_ambiguous_events_are_not_attributed_to_either_country(self):
        for code in ("US", "IR"):
            self.assertEqual(self.client.get(f"/api/countries/{code}/events").json()["total"], 0)

    def test_pagination(self):
        page1 = self.client.get("/api/countries/SD/events?limit=2").json()
        page2 = self.client.get("/api/countries/SD/events?limit=2&offset=2").json()
        self.assertEqual((page1["total"], len(page1["events"])), (3, 2))
        self.assertEqual((page2["total"], len(page2["events"])), (3, 1))
        self.assertEqual(len({e["id"] for e in page1["events"] + page2["events"]}), 3)

    def test_filters(self):
        r = self.client.get("/api/countries/SD/events?category=Health").json()
        self.assertEqual([e["category"] for e in r["events"]], ["Health"])
        self.assertEqual(self.client.get("/api/countries/SD/events?severity=critical").json()["total"], 1)
        self.assertEqual(self.client.get("/api/countries/SD/events?min_severity=high").json()["total"], 1)
        self.assertEqual(self.client.get("/api/countries/UA/events?min_confidence=high").json()["total"], 0)
        self.assertEqual(self.client.get("/api/countries/UA/events?min_confidence=medium").json()["total"], 1)

    def test_invalid_parameters_give_422(self):
        for q in ("limit=0", "limit=500", "offset=-1", "category=Sports", "severity=extreme",
                  "min_severity=x", "min_confidence=low"):
            self.assertEqual(self.client.get(f"/api/countries/SD/events?{q}").status_code, 422, q)

    def test_global_feed_country_filter_agrees_with_country_endpoint(self):
        feed = self.client.get("/api/events?country=SD")
        self.assertEqual(int(feed.headers["X-Total-Count"]), self.client.get("/api/countries/SD/events").json()["total"])

    def test_both_sources_down_gives_empty_list_not_error(self):
        svc.clear_cache()
        with mock.patch.object(svc, "collect_articles", return_value=[]):
            r = self.client.get("/api/countries/SD/events")
        self.assertEqual((r.status_code, r.json()["total"]), (200, 0))


if __name__ == "__main__":
    unittest.main()
