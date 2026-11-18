import threading
import time
import unittest
from dataclasses import replace
from unittest import mock

import requests

from app.services import event_sources as es


class FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None, content=b"", json_error=False):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.content = content
        self._json_error = json_error

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        if self._json_error:
            raise ValueError("not json")
        return self._payload


UN_ENTRIES = [
    {
        "title": "UN chief urges ceasefire",
        "summary": "<p>The Secretary-General &amp; envoys met.</p>",
        "link": "https://news.un.org/en/story/2026/11/1001",
        "published": "Sun, 08 Nov 2026 10:00:00 +0000",
        "tags": [{"term": "Peace and Security"}],
    },
    {
        "title": "Older UN story",
        "summary": "",
        "link": "https://news.un.org/en/story/2026/11/1000",
        "published": "Sat, 07 Nov 2026 09:00:00 +0000",
    },
]

GDELT_PAYLOAD = {
    "articles": [
        {"url": "https://example.com/a", "title": "Floods displace thousands", "seendate": "20261108T120000Z",
         "domain": "example.com", "sourcecountry": "France"},
        {"url": "https://example.com/b", "title": "Markets steady", "seendate": "20261106T080000Z",
         "domain": "example.com", "sourcecountry": "India"},
    ]
}


class HelperTests(unittest.TestCase):
    def test_clean_text_strips_html_and_entities(self):
        self.assertEqual(es.clean_text("<p>Hello &amp;  <b>world</b></p>"), "Hello & world")
        self.assertEqual(es.clean_text(None), "")

    def test_parse_datetime_formats(self):
        self.assertEqual(es.parse_datetime("Sun, 08 Nov 2026 10:00:00 +0000"), "2026-11-08T10:00:00Z")
        self.assertEqual(es.parse_datetime("Sun, 08 Nov 2026 15:30:00 +0530"), "2026-11-08T10:00:00Z")
        self.assertEqual(es.parse_datetime("20261108T101500Z"), "2026-11-08T10:15:00Z")
        self.assertEqual(es.parse_datetime("2026-11-08T10:15:00+00:00"), "2026-11-08T10:15:00Z")
        self.assertEqual(es.parse_datetime("2026-11-08T10:15:00Z"), "2026-11-08T10:15:00Z")

    def test_parse_datetime_never_guesses(self):
        self.assertIsNone(es.parse_datetime(""))
        self.assertIsNone(es.parse_datetime(None))
        self.assertIsNone(es.parse_datetime("yesterday-ish"))

    def test_normalize_url_ignores_tracking_scheme_www_and_slash(self):
        a = es.normalize_url("https://www.Example.com/story/1/?utm_source=x&id=7#top")
        b = es.normalize_url("http://example.com/story/1?id=7")
        self.assertEqual(a, b)

    def test_dedupe_by_url_and_by_long_title_prefers_first(self):
        un = {"title": "Same long headline about a very specific event", "url": "https://news.un.org/a", "source": "UN News"}
        dup_url = {"title": "Different", "url": "https://www.news.un.org/a/", "source": "GDELT"}
        dup_title = {"title": "SAME long headline about a very specific event!", "url": "https://other.com/x", "source": "GDELT"}
        short_a = {"title": "Talks", "url": "https://a.com/1", "source": "GDELT"}
        short_b = {"title": "Talks", "url": "https://b.com/2", "source": "GDELT"}
        out = es.dedupe_articles([un, dup_url, dup_title, short_a, short_b])
        self.assertEqual([a["url"] for a in out], ["https://news.un.org/a", "https://a.com/1", "https://b.com/2"])
        self.assertEqual(out[0]["source"], "UN News")

    def test_entry_to_article(self):
        article = es.entry_to_article(UN_ENTRIES[0])
        self.assertEqual(article["description"], "The Secretary-General & envoys met.")
        self.assertEqual(article["published"], "2026-11-08T10:00:00Z")
        self.assertEqual(article["source"], "UN News")
        self.assertEqual(article["topics"], ["Peace and Security"])
        self.assertIsNone(article["source_country"])

    def test_entry_without_link_or_title_is_dropped(self):
        self.assertIsNone(es.entry_to_article({"title": "No link"}))
        self.assertIsNone(es.entry_to_article({"link": "https://x.org"}))

    def test_gdelt_country_is_kept_only_as_publisher_country(self):
        article = es.gdelt_entry_to_article(GDELT_PAYLOAD["articles"][0])
        self.assertEqual(article["source_country"], "France")
        self.assertNotIn("country", article)


class SourceTestCase(unittest.TestCase):
    def setUp(self):
        es.reset_state()
        self.addCleanup(es.reset_state)


class UnNewsTests(SourceTestCase):
    def test_success_is_cached_and_does_not_refetch(self):
        with mock.patch.object(es.requests, "get", return_value=FakeResponse()) as get, \
             mock.patch.object(es, "_parse_feed", return_value=UN_ENTRIES):
            self.assertEqual(len(es.fetch_un_news(10)), 2)
            self.assertEqual(len(es.fetch_un_news(1)), 1)
            self.assertEqual(get.call_count, 1)
        status = es.get_source_status()[0]
        self.assertEqual(status["status"], "ok")
        self.assertEqual(status["articleCount"], 2)

    def test_network_failure_returns_empty_and_backs_off(self):
        with mock.patch.object(es.requests, "get", side_effect=requests.ConnectionError("down")) as get:
            self.assertEqual(es.fetch_un_news(10), [])
            self.assertEqual(es.fetch_un_news(10), [])  # second call must not hit the network
            self.assertEqual(get.call_count, 1)
        status = es.get_source_status()[0]
        self.assertEqual(status["status"], "error")
        self.assertGreater(status["cooldownRemainingSeconds"], 0)

    def test_failure_serves_last_good_result(self):
        with mock.patch.object(es.requests, "get", return_value=FakeResponse()), \
             mock.patch.object(es, "_parse_feed", return_value=UN_ENTRIES):
            es.fetch_un_news(10)
        es._cache._items["un_news"] = (-10_000.0, es._cache._items["un_news"][1])  # expire it
        with mock.patch.object(es.requests, "get", side_effect=requests.Timeout("slow")):
            self.assertEqual(len(es.fetch_un_news(10)), 2)

    def test_empty_feed_counts_as_failure_and_is_not_cached(self):
        with mock.patch.object(es.requests, "get", return_value=FakeResponse()), \
             mock.patch.object(es, "_parse_feed", return_value=[]):
            self.assertEqual(es.fetch_un_news(10), [])
        self.assertEqual(es.get_source_status()[0]["status"], "error")


class GdeltTests(SourceTestCase):
    def test_success(self):
        with mock.patch.object(es.requests, "get", return_value=FakeResponse(payload=GDELT_PAYLOAD)):
            articles = es.fetch_gdelt_news(5)
        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[0]["published"], "2026-11-08T12:00:00Z")
        self.assertEqual(es.get_source_status()[1]["status"], "ok")

    def test_query_wraps_or_terms_in_parentheses(self):
        with mock.patch.object(es.requests, "get", return_value=FakeResponse(payload={})) as get:
            es.fetch_gdelt_news(5)
        query = get.call_args.kwargs["params"]["query"]
        self.assertTrue(query.startswith("(") and ") " in query)

    def test_429_returns_empty_and_is_not_retried(self):
        with mock.patch.object(es.requests, "get", return_value=FakeResponse(status_code=429)) as get:
            self.assertEqual(es.fetch_gdelt_news(5), [])
            for _ in range(5):
                self.assertEqual(es.fetch_gdelt_news(5), [])
            self.assertEqual(get.call_count, 1, "GDELT must not be re-contacted while rate-limited")
        status = es.get_source_status()[1]
        self.assertEqual(status["status"], "rate_limited")
        self.assertGreater(status["cooldownRemainingSeconds"], 0)

    def test_429_honours_numeric_retry_after(self):
        with mock.patch.object(es.requests, "get", return_value=FakeResponse(status_code=429, headers={"Retry-After": "42"})):
            es.fetch_gdelt_news(5)
        self.assertLessEqual(es.get_source_status()[1]["cooldownRemainingSeconds"], 42)
        self.assertGreater(es.get_source_status()[1]["cooldownRemainingSeconds"], 30)

    def test_retried_after_cooldown_expires(self):
        clock = {"now": 1000.0}
        with mock.patch.object(es, "_monotonic", lambda: clock["now"]), \
             mock.patch.object(es.requests, "get", return_value=FakeResponse(status_code=429)) as get:
            es.fetch_gdelt_news(5)
            clock["now"] += es.settings.gdelt_cooldown_seconds + 1
            es.fetch_gdelt_news(5)
            self.assertEqual(get.call_count, 2)

    def test_non_json_body_is_handled(self):
        with mock.patch.object(es.requests, "get", return_value=FakeResponse(json_error=True)):
            self.assertEqual(es.fetch_gdelt_news(5), [])
        self.assertEqual(es.get_source_status()[1]["status"], "error")

    def test_server_error_and_timeout_are_handled(self):
        with mock.patch.object(es.requests, "get", return_value=FakeResponse(status_code=503)):
            self.assertEqual(es.fetch_gdelt_news(5), [])
        es.reset_state()
        with mock.patch.object(es.requests, "get", side_effect=requests.Timeout("slow")):
            self.assertEqual(es.fetch_gdelt_news(5), [])


class CombinedTests(SourceTestCase):
    def _get(self, url, **kwargs):
        return FakeResponse(payload=GDELT_PAYLOAD) if "gdelt" in url else FakeResponse()

    def test_both_sources_merge_sorted_newest_first(self):
        with mock.patch.object(es.requests, "get", side_effect=self._get), \
             mock.patch.object(es, "_parse_feed", return_value=UN_ENTRIES):
            articles = es.fetch_all_events(10)
        self.assertEqual(
            [a["published"] for a in articles],
            ["2026-11-08T12:00:00Z", "2026-11-08T10:00:00Z", "2026-11-07T09:00:00Z", "2026-11-06T08:00:00Z"],
        )

    def test_gdelt_not_crowded_out_by_un_news(self):
        # Old behaviour: UN items first, then slice -> GDELT vanished when UN had `limit` items.
        with mock.patch.object(es.requests, "get", side_effect=self._get), \
             mock.patch.object(es, "_parse_feed", return_value=UN_ENTRIES):
            articles = es.fetch_all_events(2)
        self.assertIn("GDELT", {a["source"] for a in articles})

    def test_gdelt_rate_limited_un_news_still_works(self):
        def get(url, **kwargs):
            return FakeResponse(status_code=429) if "gdelt" in url else FakeResponse()
        with mock.patch.object(es.requests, "get", side_effect=get), \
             mock.patch.object(es, "_parse_feed", return_value=UN_ENTRIES):
            articles = es.fetch_all_events(10)
        self.assertEqual({a["source"] for a in articles}, {"UN News"})
        self.assertEqual(len(articles), 2)

    def test_un_news_down_gdelt_still_works(self):
        def get(url, **kwargs):
            if "gdelt" in url:
                return FakeResponse(payload=GDELT_PAYLOAD)
            raise requests.ConnectionError("down")
        with mock.patch.object(es.requests, "get", side_effect=get):
            articles = es.fetch_all_events(10)
        self.assertEqual({a["source"] for a in articles}, {"GDELT"})

    def test_both_sources_down_returns_empty_list_not_an_exception(self):
        with mock.patch.object(es.requests, "get", side_effect=requests.ConnectionError("down")):
            self.assertEqual(es.fetch_all_events(10), [])

    def test_unexpected_exception_in_one_source_is_contained(self):
        with mock.patch.object(es, "fetch_gdelt_news", side_effect=RuntimeError("bug")), \
             mock.patch.object(es.requests, "get", return_value=FakeResponse()), \
             mock.patch.object(es, "_parse_feed", return_value=UN_ENTRIES):
            self.assertEqual(len(es.fetch_all_events(10)), 2)


class SlowSourceTests(SourceTestCase):
    """GDELT hung for 15s in your run and /api/events waited for it."""

    def test_slow_gdelt_does_not_delay_un_news(self):
        release = threading.Event()
        self.addCleanup(release.set)

        def slow_gdelt(limit):
            release.wait(10)
            return []

        quick = replace(es.settings, gdelt_wait_seconds=0.3)
        with mock.patch.object(es, "settings", quick), \
             mock.patch.object(es, "fetch_gdelt_news", slow_gdelt), \
             mock.patch.object(es.requests, "get", return_value=FakeResponse()), \
             mock.patch.object(es, "_parse_feed", return_value=UN_ENTRIES):
            started = time.time()
            articles = es.collect_articles(10, 10)
            elapsed = time.time() - started
        self.assertLess(elapsed, 3)
        self.assertEqual({a["source"] for a in articles}, {"UN News"})

    def test_second_gdelt_request_never_queues_behind_one_in_flight(self):
        es._gdelt_state.lock.acquire()  # simulate a slow call in progress
        self.addCleanup(es._gdelt_state.lock.release)
        with mock.patch.object(es.requests, "get") as get:
            self.assertEqual(es.fetch_gdelt_news(5), [])
        get.assert_not_called()

    def test_in_flight_gdelt_serves_last_good_result(self):
        with mock.patch.object(es.requests, "get", return_value=FakeResponse(payload=GDELT_PAYLOAD)):
            es.fetch_gdelt_news(5)
        es._cache._items["gdelt"] = (-1e9, es._cache._items["gdelt"][1])  # expire
        es._gdelt_state.lock.acquire()
        self.addCleanup(es._gdelt_state.lock.release)
        self.assertEqual(len(es.fetch_gdelt_news(5)), 2)


if __name__ == "__main__":
    unittest.main()
