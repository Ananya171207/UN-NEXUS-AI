import threading
import time
import unittest
from dataclasses import replace
from unittest import mock

import requests

from app.services import worldbank as wb


class FakeResponse:
    def __init__(self, status_code=200, payload=None, json_error=False):
        self.status_code, self._payload, self._json_error = status_code, payload, json_error

    def json(self):
        if self._json_error:
            raise ValueError("bad json")
        return self._payload


def wb_payload(code, rows, lastupdated="2026-10-08", name="Some indicator"):
    """Shape the World Bank returns: [meta, records]."""
    meta = {"page": 1, "pages": 1, "per_page": 60, "total": len(rows), "lastupdated": lastupdated}
    records = [
        {"indicator": {"id": code, "value": name}, "country": {"id": "IN", "value": "India"},
         "countryiso3code": "IND", "date": year, "value": value}
        for year, value in rows
    ]
    return [meta, records] if rows else [meta, None]


class Base(unittest.TestCase):
    def setUp(self):
        wb.reset_cache()
        self.addCleanup(wb.reset_cache)


class SingleIndicatorTests(Base):
    def test_picks_latest_non_null_value(self):
        payload = wb_payload("SP.POP.TOTL", [("2025", None), ("2024", 1450.0), ("2023", 1430.0)])
        with mock.patch.object(wb.requests, "get", return_value=FakeResponse(payload=payload)):
            r = wb.fetch_indicator("IND", wb.BY_KEY["population"])
        self.assertEqual((r["status"], r["value"], r["year"]), ("available", 1450.0, "2024"))
        self.assertEqual(r["source"], "World Bank Open Data")
        self.assertEqual(r["unit"], "people")
        self.assertEqual(r["sourceLastUpdated"], "2026-10-08")
        self.assertEqual(r["indicatorName"], "Some indicator")
        self.assertFalse(r["stale"])

    def test_years_can_differ_between_indicators(self):
        def get(url, **kw):
            year = "2022" if "SI.POV" in url else "2024"
            return FakeResponse(payload=wb_payload("X", [(year, 5.0)]))
        with mock.patch.object(wb.requests, "get", side_effect=get):
            res = wb.fetch_country_indicators("IND")
        self.assertEqual(res["poverty_rate"]["year"], "2022")
        self.assertEqual(res["population"]["year"], "2024")

    def test_all_null_values_is_no_data_not_zero(self):
        payload = wb_payload("SI.POV.DDAY", [("2024", None), ("2023", None)])
        with mock.patch.object(wb.requests, "get", return_value=FakeResponse(payload=payload)):
            r = wb.fetch_indicator("IND", wb.BY_KEY["poverty_rate"])
        self.assertEqual(r["status"], "no_data")
        self.assertIsNone(r["value"])

    def test_empty_answer_is_no_data(self):
        with mock.patch.object(wb.requests, "get", return_value=FakeResponse(payload=wb_payload("X", []))):
            self.assertEqual(wb.fetch_indicator("IND", wb.BY_KEY["pm25"])["status"], "no_data")

    def test_world_bank_error_message_is_an_error_not_a_crash(self):
        payload = [{"message": [{"id": "175", "key": "Invalid format", "value": "The indicator was not found."}]}]
        with mock.patch.object(wb.requests, "get", return_value=FakeResponse(payload=payload)):
            r = wb.fetch_indicator("IND", wb.BY_KEY["pm25"])
        self.assertEqual(r["status"], "error")
        self.assertIn("not found", r["error"])

    def test_cached_result_is_reused(self):
        payload = wb_payload("SP.POP.TOTL", [("2024", 1.0)])
        with mock.patch.object(wb.requests, "get", return_value=FakeResponse(payload=payload)) as get:
            wb.fetch_indicator("IND", wb.BY_KEY["population"])
            wb.fetch_indicator("IND", wb.BY_KEY["population"])
        self.assertEqual(get.call_count, 1)

    def test_errors_are_not_cached(self):
        with mock.patch.object(wb.requests, "get", side_effect=requests.ConnectionError("down")):
            self.assertEqual(wb.fetch_indicator("IND", wb.BY_KEY["population"])["status"], "error")
        payload = wb_payload("SP.POP.TOTL", [("2024", 1.0)])
        with mock.patch.object(wb.requests, "get", return_value=FakeResponse(payload=payload)):
            self.assertEqual(wb.fetch_indicator("IND", wb.BY_KEY["population"])["status"], "available")

    def test_timeout_is_retried_once_then_succeeds(self):
        payload = wb_payload("SP.POP.TOTL", [("2024", 1.0)])
        with mock.patch.object(wb.requests, "get", side_effect=[requests.Timeout("slow"), FakeResponse(payload=payload)]) as get:
            r = wb.fetch_indicator("IND", wb.BY_KEY["population"])
        self.assertEqual(r["status"], "available")
        self.assertEqual(get.call_count, 2)

    def test_repeated_timeouts_give_error_after_bounded_attempts(self):
        with mock.patch.object(wb.requests, "get", side_effect=requests.Timeout("slow")) as get:
            r = wb.fetch_indicator("IND", wb.BY_KEY["population"])
        self.assertEqual(r["status"], "error")
        self.assertEqual(get.call_count, wb.settings.worldbank_retries + 1)

    def test_client_error_is_not_retried(self):
        with mock.patch.object(wb.requests, "get", return_value=FakeResponse(status_code=404)) as get:
            r = wb.fetch_indicator("IND", wb.BY_KEY["population"])
        self.assertEqual((r["status"], get.call_count), ("error", 1))

    def test_server_error_is_retried(self):
        with mock.patch.object(wb.requests, "get", return_value=FakeResponse(status_code=503)) as get:
            wb.fetch_indicator("IND", wb.BY_KEY["population"])
        self.assertEqual(get.call_count, wb.settings.worldbank_retries + 1)

    def test_invalid_json_is_an_error(self):
        with mock.patch.object(wb.requests, "get", return_value=FakeResponse(json_error=True)):
            self.assertEqual(wb.fetch_indicator("IND", wb.BY_KEY["population"])["status"], "error")

    def test_stale_value_served_when_refresh_fails(self):
        payload = wb_payload("SP.POP.TOTL", [("2024", 7.0)])
        with mock.patch.object(wb.requests, "get", return_value=FakeResponse(payload=payload)):
            wb.fetch_indicator("IND", wb.BY_KEY["population"])
        wb._cache._items["IND:population"] = (-1e9, wb._cache._items["IND:population"][1])  # expire it
        with mock.patch.object(wb.requests, "get", side_effect=requests.Timeout("slow")):
            r = wb.fetch_indicator("IND", wb.BY_KEY["population"])
        self.assertEqual((r["status"], r["value"], r["stale"]), ("available", 7.0, True))


class ProfileIsolationTests(Base):
    """The failure you hit: one indicator timing out must not break the others."""

    def test_one_timing_out_indicator_does_not_affect_the_rest(self):
        def get(url, **kw):
            if "SE.SEC.ENRR" in url:
                raise requests.Timeout("Read timed out")
            return FakeResponse(payload=wb_payload("X", [("2024", 1.0)]))
        with mock.patch.object(wb.requests, "get", side_effect=get):
            res = wb.fetch_country_indicators("IND")
        self.assertEqual(res["school_enrollment"]["status"], "error")
        others = [r for k, r in res.items() if k != "school_enrollment"]
        self.assertTrue(others and all(r["status"] == "available" for r in others))

    def test_every_registry_indicator_is_returned_in_order(self):
        with mock.patch.object(wb.requests, "get", return_value=FakeResponse(payload=wb_payload("X", [("2024", 1.0)]))):
            res = wb.fetch_country_indicators("IND")
        self.assertEqual(list(res), [i.key for i in wb.INDICATORS])

    def test_requests_run_in_parallel(self):
        barrier = threading.Barrier(4, timeout=5)  # only passes if 4 calls are in flight together
        def get(url, **kw):
            barrier.wait()
            return FakeResponse(payload=wb_payload("X", [("2024", 1.0)]))
        subset = wb.INDICATORS[:4]
        with mock.patch.object(wb.requests, "get", side_effect=get):
            res = wb.fetch_country_indicators("IND", subset)
        self.assertEqual(len(res), 4)

    def test_registry_keeps_the_original_five_keys(self):
        for key in ("gdp_per_capita", "population", "life_expectancy", "co2_emissions", "school_enrollment"):
            self.assertIn(key, wb.BY_KEY)

    def test_registry_has_no_duplicate_keys_or_codes(self):
        self.assertEqual(len({i.key for i in wb.INDICATORS}), len(wb.INDICATORS))
        self.assertEqual(len({i.code for i in wb.INDICATORS}), len(wb.INDICATORS))


class DeadlineTests(Base):
    """A slow indicator must not make the whole profile slow (your 32-second USA profile)."""

    def test_slow_indicator_is_pending_and_the_rest_still_return_quickly(self):
        release = threading.Event()
        self.addCleanup(release.set)

        def get(url, **kw):
            if "SE.SEC.ENRR" in url:
                release.wait(10)  # simulates a World Bank request that hangs
            return FakeResponse(payload=wb_payload("X", [("2024", 1.0)]))

        fast = replace(wb.settings, worldbank_profile_deadline=0.5)
        with mock.patch.object(wb, "settings", fast), mock.patch.object(wb.requests, "get", side_effect=get):
            started = time.time()
            res = wb.fetch_country_indicators("IND")
            elapsed = time.time() - started
        self.assertLess(elapsed, 3)
        self.assertEqual(res["school_enrollment"]["status"], "pending")
        self.assertIn("retry", res["school_enrollment"]["error"].lower())
        self.assertTrue(all(r["status"] == "available" for k, r in res.items() if k != "school_enrollment"))

    def test_pending_indicator_finishes_in_background_and_is_cached(self):
        release = threading.Event()

        def get(url, **kw):
            if "SE.SEC.ENRR" in url:
                release.wait(10)
            return FakeResponse(payload=wb_payload("X", [("2024", 5.0)]))

        fast = replace(wb.settings, worldbank_profile_deadline=0.3)
        with mock.patch.object(wb, "settings", fast), mock.patch.object(wb.requests, "get", side_effect=get):
            first = wb.fetch_country_indicators("IND")
            self.assertEqual(first["school_enrollment"]["status"], "pending")
            release.set()
            for _ in range(50):  # wait for the background fetch to land in the cache
                if wb._cache.get_stale("IND:school_enrollment") is not wb.MISSING:
                    break
                time.sleep(0.05)
            second = wb.fetch_country_indicators("IND")
        self.assertEqual(second["school_enrollment"]["status"], "available")

    def test_default_timeouts_are_short_enough_to_recover_from_a_hang(self):
        self.assertLessEqual(wb.settings.worldbank_timeout, 5)
        self.assertGreaterEqual(wb.settings.worldbank_retries, 2)
        self.assertLessEqual(wb.settings.worldbank_profile_deadline, 15)


class BulkTests(Base):
    def _records(self):
        def rec(iso3, year, value):
            return {"countryiso3code": iso3, "date": year, "value": value, "indicator": {"id": "X", "value": "x"}}
        return [rec("IND", "2024", 1450.0), rec("FRA", "2024", None), rec("", "2024", 5.0), rec("WLD", "2024", 8000.0)]

    def test_bulk_keeps_valid_iso3_rows_and_skips_nulls(self):
        payload = [{"page": 1, "pages": 1}, self._records()]
        with mock.patch.object(wb.requests, "get", return_value=FakeResponse(payload=payload)):
            data, error = wb.fetch_bulk(wb.BY_KEY["population"])
        self.assertIsNone(error)
        self.assertEqual(data["IND"], {"value": 1450.0, "year": "2024"})
        self.assertNotIn("FRA", data)  # null value
        self.assertIn("WLD", data)  # aggregates are kept here and ignored by the list builder

    def test_bulk_follows_pages(self):
        p1 = [{"page": 1, "pages": 2}, [{"countryiso3code": "IND", "date": "2024", "value": 1.0}]]
        p2 = [{"page": 2, "pages": 2}, [{"countryiso3code": "FRA", "date": "2024", "value": 2.0}]]
        with mock.patch.object(wb.requests, "get", side_effect=[FakeResponse(payload=p1), FakeResponse(payload=p2)]):
            data, _ = wb.fetch_bulk(wb.BY_KEY["population"])
        self.assertEqual(set(data), {"IND", "FRA"})

    def test_bulk_keeps_latest_year_if_several_rows(self):
        payload = [{"pages": 1}, [
            {"countryiso3code": "IND", "date": "2020", "value": 1.0},
            {"countryiso3code": "IND", "date": "2024", "value": 4.0},
        ]]
        with mock.patch.object(wb.requests, "get", return_value=FakeResponse(payload=payload)):
            data, _ = wb.fetch_bulk(wb.BY_KEY["population"])
        self.assertEqual(data["IND"]["year"], "2024")

    def test_bulk_failure_reports_error_and_empty_data(self):
        with mock.patch.object(wb.requests, "get", side_effect=requests.ConnectionError("down")):
            data, error = wb.fetch_bulk(wb.BY_KEY["population"])
        self.assertEqual(data, {})
        self.assertIn("down", error)

    def test_bulk_many_isolates_failures(self):
        def get(url, **kw):
            if "SP.POP.TOTL" in url:
                raise requests.ConnectionError("down")
            return FakeResponse(payload=[{"pages": 1}, [{"countryiso3code": "IND", "date": "2024", "value": 3.0}]])
        with mock.patch.object(wb.requests, "get", side_effect=get):
            data, errors = wb.fetch_bulk_many(["population", "gdp"])
        self.assertEqual(set(errors), {"population"})
        self.assertEqual(data["gdp"]["IND"]["value"], 3.0)


if __name__ == "__main__":
    unittest.main()
