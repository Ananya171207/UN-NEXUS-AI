"""HTTP-level tests. Need fastapi + httpx (pip install -r requirements-dev.txt)."""
import unittest
from unittest import mock

try:
    from fastapi.testclient import TestClient
    from app.main import app
    HAVE_FASTAPI = True
except Exception:  # pragma: no cover - environment without fastapi/httpx
    HAVE_FASTAPI = False

from app.services import event_sources as es
from app.services import events as svc

ARTICLES = [
    {"title": "Airstrikes kill more than 100 civilians", "description": "Fighting continued.",
     "url": "https://news.un.org/a", "published": "2026-11-08T12:00:00Z", "source": "UN News",
     "domain": "news.un.org", "source_country": None, "topics": []},
    {"title": "Climate talks open", "description": "", "url": "https://example.com/b",
     "published": "2026-11-08T09:00:00Z", "source": "GDELT", "domain": "example.com",
     "source_country": "France", "topics": []},
    {"title": "Cholera outbreak spreads", "description": "", "url": "https://example.com/c",
     "published": "2026-11-07T09:00:00Z", "source": "GDELT", "domain": "example.com",
     "source_country": None, "topics": []},
]


@unittest.skipUnless(HAVE_FASTAPI, "fastapi/httpx not installed")
class EventsApiTests(unittest.TestCase):
    def setUp(self):
        svc.clear_cache()
        es.reset_state()
        self.client = TestClient(app)
        patcher = mock.patch.object(svc, "collect_articles", return_value=ARTICLES)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(svc.clear_cache)
        self.addCleanup(es.reset_state)

    def test_root_and_health_preserved(self):
        self.assertEqual(self.client.get("/").json()["status"], "Backend is running")
        self.assertEqual(self.client.get("/health").json(), {"status": "healthy"})

    def test_events_returns_plain_array_with_total_header(self):
        r = self.client.get("/api/events")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIsInstance(body, list)
        self.assertEqual(len(body), 3)
        self.assertEqual(r.headers["X-Total-Count"], "3")
        for key in ("id", "title", "summary", "url", "occurredAt", "source", "category", "severity", "countryId"):
            self.assertIn(key, body[0])

    def test_limit_and_offset(self):
        r = self.client.get("/api/events?limit=2")
        self.assertEqual(len(r.json()), 2)
        self.assertEqual(r.headers["X-Total-Count"], "3")
        self.assertEqual(len(self.client.get("/api/events?limit=2&offset=2").json()), 1)

    def test_category_filter(self):
        body = self.client.get("/api/events?category=Environmental").json()
        self.assertEqual([e["category"] for e in body], ["Environmental"])

    def test_severity_filters_including_medium_alias(self):
        self.assertEqual({e["severity"] for e in self.client.get("/api/events?severity=critical").json()}, {"critical"})
        self.assertEqual(self.client.get("/api/events?severity=Medium").status_code, 200)
        self.assertEqual(len(self.client.get("/api/events?min_severity=high").json()), 1)

    def test_country_filter_returns_empty_when_no_reliable_mapping(self):
        r = self.client.get("/api/events?country=FR")
        self.assertEqual(r.json(), [])

    def test_invalid_parameters_give_422(self):
        for q in ("limit=0", "limit=9999", "offset=-1", "category=Sports", "severity=extreme", "min_severity=x"):
            self.assertEqual(self.client.get(f"/api/events?{q}").status_code, 422, q)

    def test_status_endpoint(self):
        r = self.client.get("/api/events/status")
        self.assertEqual(r.status_code, 200)
        self.assertEqual({s["source"] for s in r.json()}, {"UN News", "GDELT"})

    def test_both_sources_down_returns_200_and_empty_list(self):
        svc.clear_cache()
        with mock.patch.object(svc, "collect_articles", return_value=[]):
            r = self.client.get("/api/events")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), [])

    def test_cors_allows_vite_dev_server(self):
        r = self.client.get("/api/events", headers={"Origin": "http://localhost:5173"})
        self.assertEqual(r.headers.get("access-control-allow-origin"), "http://localhost:5173")


if __name__ == "__main__":
    unittest.main()
