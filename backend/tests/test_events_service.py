import unittest
from unittest import mock

from app.services import event_sources as es
from app.services import events as svc

ARTICLES = [
    {"title": "Airstrikes kill more than 100 civilians", "description": "Fighting continued.",
     "url": "https://news.un.org/a", "published": "2026-11-08T12:00:00Z", "source": "UN News",
     "domain": "news.un.org", "source_country": None, "topics": ["Peace and Security"]},
    {"title": "Climate talks open", "description": "", "url": "https://example.com/b",
     "published": "2026-11-08T09:00:00Z", "source": "GDELT", "domain": "example.com",
     "source_country": "France", "topics": []},
    {"title": "Undated item", "description": "", "url": "https://example.com/c",
     "published": None, "source": "GDELT", "domain": None, "source_country": None, "topics": []},
]


class BuildEventTests(unittest.TestCase):
    def test_event_matches_frontend_contract(self):
        event = svc.build_event(ARTICLES[0])
        for key in ("id", "title", "summary", "severity", "category", "occurredAt", "countryId"):
            self.assertIn(key, event)
        self.assertEqual(event["occurredAt"], "2026-11-08T12:00:00Z")
        self.assertEqual(event["severity"], "critical")
        self.assertEqual(event["category"], "Security")
        self.assertEqual(event["url"], "https://news.un.org/a")
        self.assertEqual(event["source"], "UN News")
        self.assertFalse(event["isSample"])

    def test_ai_flag_is_false_for_rule_based_labels(self):
        self.assertFalse(svc.build_event(ARTICLES[0])["classification"]["aiGenerated"])
        self.assertEqual(svc.build_event(ARTICLES[0])["classification"]["method"], "rules")

    def test_event_is_never_given_a_location_it_cannot_justify(self):
        # GDELT's publisher country is France; the event location must stay unknown.
        event = svc.build_event(ARTICLES[1])
        self.assertEqual(event["sourceCountry"], "France")
        for key in ("countryId", "countryCode3", "countryName", "region", "latitude", "longitude", "locationMethod"):
            self.assertIsNone(event[key], key)

    def test_undated_article_is_dropped_not_given_an_invented_date(self):
        self.assertIsNone(svc.build_event(ARTICLES[2]))

    def test_empty_summary_becomes_null(self):
        self.assertIsNone(svc.build_event(ARTICLES[1])["summary"])

    def test_id_is_stable_and_ignores_tracking_params(self):
        a = dict(ARTICLES[0], url="https://news.un.org/a?utm_source=x")
        self.assertEqual(svc.make_event_id(a), svc.make_event_id(ARTICLES[0]))
        self.assertNotEqual(svc.make_event_id(ARTICLES[0]), svc.make_event_id(ARTICLES[1]))


class GetEventsTests(unittest.TestCase):
    def setUp(self):
        svc.clear_cache()
        es.reset_state()
        self.addCleanup(svc.clear_cache)
        self.addCleanup(es.reset_state)

    def test_pipeline_drops_undated_and_sorts(self):
        with mock.patch.object(svc, "collect_articles", return_value=ARTICLES):
            events = svc.get_events()
        self.assertEqual([e["title"] for e in events], ["Airstrikes kill more than 100 civilians", "Climate talks open"])

    def test_result_is_cached(self):
        with mock.patch.object(svc, "collect_articles", return_value=ARTICLES) as collect:
            svc.get_events()
            svc.get_events()
        self.assertEqual(collect.call_count, 1)

    def test_empty_result_is_not_cached_and_stale_is_served(self):
        with mock.patch.object(svc, "collect_articles", return_value=ARTICLES):
            good = svc.get_events(force_refresh=True)
        with mock.patch.object(svc, "collect_articles", return_value=[]):
            self.assertEqual(svc.get_events(force_refresh=True), good)

    def test_empty_with_nothing_cached_returns_empty_list(self):
        with mock.patch.object(svc, "collect_articles", return_value=[]):
            self.assertEqual(svc.get_events(), [])


class FilterTests(unittest.TestCase):
    def setUp(self):
        self.events = [svc.build_event(a) for a in ARTICLES[:2]]

    def test_category(self):
        self.assertEqual(len(svc.filter_events(self.events, categories={"Environmental"})), 1)
        self.assertEqual(len(svc.filter_events(self.events, categories={"Environmental", "Security"})), 2)

    def test_exact_severity(self):
        self.assertEqual([e["severity"] for e in svc.filter_events(self.events, severities={"critical"})], ["critical"])

    def test_min_severity(self):
        self.assertEqual(len(svc.filter_events(self.events, min_severity="high")), 1)
        self.assertEqual(len(svc.filter_events(self.events, min_severity="low")), 2)

    def test_country_filter_only_matches_reliably_mapped_events(self):
        self.assertEqual(svc.filter_events(self.events, country="FR"), [])  # publisher country must not match
        mapped = dict(self.events[0], countryId="SD", countryCode3="SDN")
        self.assertEqual(len(svc.filter_events([mapped], country="sd")), 1)
        self.assertEqual(len(svc.filter_events([mapped], country="SDN")), 1)
        self.assertEqual(svc.filter_events([mapped], country="IN"), [])


if __name__ == "__main__":
    unittest.main()
