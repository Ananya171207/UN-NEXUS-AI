"""HTTP-level tests for /api/compare and /api/compare/indicators. Need fastapi + httpx.

World Bank and REST Countries are mocked; no test touches the network.
"""
import unittest
from unittest import mock

import requests

try:
    from fastapi.testclient import TestClient
    from app.main import app
    HAVE_FASTAPI = True
except Exception:  # pragma: no cover
    HAVE_FASTAPI = False

from app.services import country_data as cd
from app.services import worldbank as wb
from tests.test_comparison import all_metadata, fake_fetch, http_get

EVERYTHING_FAILED = {i.key: "error" for i in wb.INDICATORS}


@unittest.skipUnless(HAVE_FASTAPI, "fastapi/httpx not installed")
class CompareApiTests(unittest.TestCase):
    def setUp(self):
        wb.reset_cache()
        self.addCleanup(wb.reset_cache)
        self.client = TestClient(app)
        self.table = {}
        patch = mock.patch.object(cd, "load_metadata", return_value=all_metadata())
        patch.start()
        self.addCleanup(patch.stop)
        self.use_fake_world_bank()

    def use_fake_world_bank(self):
        patch = mock.patch.object(wb, "fetch_country_indicators",
                                  side_effect=lambda code, indicators=wb.INDICATORS: fake_fetch(self.table)(code, indicators))
        patch.start()
        self.addCleanup(patch.stop)

    # --- the comparison itself -------------------------------------------------

    def test_india_vs_usa(self):
        self.table = {"IND": {"gdp": 100.0}, "USA": {"gdp": 300.0}}
        r = self.client.get("/api/compare?countries=IND,USA")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["source"], "World Bank Open Data")
        self.assertEqual(set(body["comparison"]), {"IND", "USA"})
        self.assertEqual(body["comparison"]["USA"]["gdp"]["value"], 300.0)
        self.assertEqual(body["baseline"]["country"], "IND")
        usa = next(v for v in body["analytics"]["gdp"]["values"] if v["country"] == "USA")
        self.assertEqual((usa["absoluteDifference"], usa["percentDifference"]), (200.0, 200.0))
        self.assertEqual(body["warnings"], [])
        self.assertEqual(body["dataStatus"], "complete")
        self.assertNotIn("X-Data-Warnings", r.headers)
        self.assertNotIn("X-Data-Status", r.headers)

    def test_india_vs_usa_vs_china(self):
        body = self.client.get("/api/compare?countries=IND,USA,CHN").json()
        self.assertEqual(body["countries"], ["IND", "USA", "CHN"])

    def test_five_countries(self):
        r = self.client.get("/api/compare?countries=IND,USA,CHN,BRA,DEU")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["comparison"]), 5)

    def test_alpha2_alpha3_and_mixed_case(self):
        for query in ("IN,US", "ind,usa", "In, uSA"):
            body = self.client.get("/api/compare", params={"countries": query}).json()
            self.assertEqual(body["countries"], ["IND", "USA"], query)
            self.assertEqual(set(body["comparison"]), {"IND", "USA"}, query)

    def test_duplicates_are_removed(self):
        body = self.client.get("/api/compare?countries=IND,IN,USA,usa").json()
        self.assertEqual(body["countries"], ["IND", "USA"])

    def test_response_model_keeps_every_field(self):
        self.table = {"IND": {"population": 1450000000}, "USA": {"gdp": {"stale": True}}}
        body = self.client.get("/api/compare?countries=IND,USA").json()
        entry = body["comparison"]["USA"]["gdp"]
        for field in ("key", "value", "year", "label", "unit", "group", "source", "sourceCode", "indicatorName",
                      "status", "stale", "error", "sourceLastUpdated", "fetchedAt"):
            self.assertIn(field, entry)
        self.assertTrue(entry["stale"])
        self.assertEqual(body["comparison"]["IND"]["population"]["value"], 1450000000)
        self.assertIsInstance(body["comparison"]["IND"]["population"]["value"], int)
        row = body["analytics"]["gdp"]["values"][0]
        for field in ("country", "value", "year", "status", "stale", "usable", "reason", "isBaseline", "absoluteDifference",
                      "percentDifference", "percentDifferenceNote", "yearDifference", "comparedWithBaseline",
                      "performanceVsBaseline", "valueRank", "performanceRank"):
            self.assertIn(field, row)
        for field in ("comparable", "baseline", "orderedByValue", "orderedBestToWorst", "highest", "lowest",
                      "coverage", "years", "yearsDiffer", "notes", "direction", "differenceUnit"):
            self.assertIn(field, body["analytics"]["gdp"])
        self.assertEqual(set(body["dataQuality"]["IND"]), {"total", "available", "noData", "error", "pending", "stale",
                                                           "coverage", "complete", "staleIndicators", "missing"})
        self.assertEqual(len(body["indicatorMetadata"]), len(wb.INDICATORS))
        self.assertIn("lastUpdated", body)

    def test_country_metadata(self):
        india = self.client.get("/api/compare?countries=IND,USA").json()["countryMetadata"]["IND"]
        self.assertEqual((india["name"], india["alpha2"], india["alpha3"]), ("India", "IN", "IND"))
        self.assertEqual((india["region"], india["subregion"], india["capital"]), ("Asia", "Southern Asia", "New Delhi"))
        self.assertEqual((india["latitude"], india["longitude"]), (20.0, 77.0))
        self.assertEqual(india["flag"], "https://flags/IN.svg")
        self.assertTrue(india["flagEmoji"])
        self.assertTrue(india["isBaseline"])

    # --- backward compatibility -------------------------------------------------

    def test_legacy_consumers_still_find_what_they_read(self):
        body = self.client.get("/api/compare?countries=IND,USA").json()
        self.assertIn("source", body)
        for code in ("IND", "USA"):
            for key in ("gdp_per_capita", "population", "life_expectancy", "co2_emissions", "school_enrollment"):
                self.assertIn("year", body["comparison"][code][key])
                self.assertIn("value", body["comparison"][code][key])

    def test_legacy_status_codes_and_messages(self):
        few = self.client.get("/api/compare?countries=IND")
        self.assertEqual(few.status_code, 400)
        self.assertTrue(few.json()["detail"].startswith("Please provide between 2 and 5 countries"))
        many = self.client.get("/api/compare?countries=IND,USA,CHN,BRA,DEU,JPN")
        self.assertEqual(many.status_code, 400)
        bad = self.client.get("/api/compare?countries=IND,ZZZ")
        self.assertEqual(bad.status_code, 404)
        self.assertTrue(bad.json()["detail"].startswith("Invalid country code"))


    def test_the_old_implementation_is_gone_and_there_is_one_compare_route(self):
        from app.routes import countries

        for name in (
            "PROFILE_CACHE",
            "fetch_latest_indicator",
            "compare_countries",
            "validate_country_code",
        ):
            self.assertFalse(hasattr(countries, name), name)

        # Check the public FastAPI route specification rather than
        # app.routes internals, which differ across FastAPI versions.
        paths = app.openapi()["paths"]

        self.assertIn("/api/compare", paths)
        self.assertIn("get", paths["/api/compare"])

        self.assertIn("/api/compare/indicators", paths)
        self.assertIn("get", paths["/api/compare/indicators"])

        self.assertIn("/api/countries/{country_code}/profile", paths)
        self.assertIn(
            "/api/countries/{country_code}/indicators/{indicator_code}",
            paths,
        )


    # --- validation -------------------------------------------------------------

    def test_invalid_and_malformed_codes_are_404_and_listed(self):
        r = self.client.get("/api/compare?countries=IND,ZZZ,12")
        self.assertEqual(r.status_code, 404)
        self.assertIn("ZZZ", r.json()["detail"])
        self.assertIn("12", r.json()["detail"])

    def test_too_few_and_only_duplicates(self):
        for query in ("IND", "IND,IND", "IN,IND", ",,,"):
            self.assertEqual(self.client.get("/api/compare", params={"countries": query}).status_code, 400, query)

    def test_missing_query_parameter_is_422(self):
        self.assertEqual(self.client.get("/api/compare").status_code, 422)

    def test_explicit_baseline(self):
        body = self.client.get("/api/compare?countries=IND,USA,CHN&baseline=CN").json()
        self.assertEqual(body["baseline"]["country"], "CHN")
        self.assertEqual(body["baseline"]["basis"], "requested")

    def test_baseline_outside_the_selection_is_400_and_unknown_is_404(self):
        self.assertEqual(self.client.get("/api/compare?countries=IND,USA&baseline=BRA").status_code, 400)
        self.assertEqual(self.client.get("/api/compare?countries=IND,USA&baseline=ZZZ").status_code, 404)

    def test_no_india_means_first_country_baseline_with_a_warning(self):
        r = self.client.get("/api/compare?countries=USA,CHN")
        body = r.json()
        self.assertEqual(body["baseline"]["basis"], "first_country")
        self.assertTrue(any("not among the selected" in w for w in body["warnings"]))
        self.assertIn("X-Data-Warnings", r.headers)

    # --- partial data -----------------------------------------------------------

    def test_partial_data_is_200_with_statuses_warnings_and_headers(self):
        self.table = {"USA": {"poverty_rate": "no_data", "pm25": "error", "forest_area": "pending"}}
        r = self.client.get("/api/compare?countries=IND,USA")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["dataStatus"], "partial")
        usa = body["comparison"]["USA"]
        self.assertEqual((usa["poverty_rate"]["status"], usa["pm25"]["status"], usa["forest_area"]["status"]),
                         ("no_data", "error", "pending"))
        self.assertEqual(usa["gdp"]["status"], "available")
        self.assertTrue(body["warnings"])
        self.assertIn("pm25", r.headers["X-Data-Warnings"])
        self.assertTrue(r.headers["X-Data-Status"].startswith("partial"))
        self.assertEqual(body["dataQuality"]["USA"]["missing"][0]["key"], "poverty_rate")

    def test_headers_are_ascii_safe(self):
        self.table = {"USA": {"pm25": "error"}}
        r = self.client.get("/api/compare?countries=IND,USA")
        r.headers["X-Data-Warnings"].encode("ascii")
        self.assertLessEqual(len(r.headers["X-Data-Warnings"]), 1000)

    def test_everything_failing_is_502(self):
        self.table = {"IND": EVERYTHING_FAILED, "USA": EVERYTHING_FAILED}
        r = self.client.get("/api/compare?countries=IND,USA")
        self.assertEqual(r.status_code, 502)
        self.assertIn("Retry", r.json()["detail"])

    def test_one_country_failing_completely_is_still_200(self):
        self.table = {"CHN": EVERYTHING_FAILED}
        r = self.client.get("/api/compare?countries=IND,USA,CHN")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["dataQuality"]["CHN"]["available"], 0)

    def test_malformed_upstream_value_does_not_break_the_response(self):
        self.table = {"USA": {"gdp": {"value": float("nan")}, "population": {"value": "12"}}}
        r = self.client.get("/api/compare?countries=IND,USA")
        self.assertEqual(r.status_code, 200)
        usa = r.json()["comparison"]["USA"]
        self.assertEqual((usa["gdp"]["status"], usa["gdp"]["value"]), ("error", None))
        self.assertEqual((usa["population"]["status"], usa["population"]["value"]), ("error", None))

    def test_different_reporting_years_are_flagged(self):
        self.table = {"IND": {"gdp": (100.0, "2023")}, "USA": {"gdp": (300.0, "2025")}}
        body = self.client.get("/api/compare?countries=IND,USA").json()
        self.assertTrue(body["analytics"]["gdp"]["yearsDiffer"])
        self.assertEqual(body["comparison"]["IND"]["gdp"]["year"], "2023")
        self.assertTrue(any("Reporting years differ for GDP" in w for w in body["warnings"]))

    def test_zero_baseline_gives_null_percentage(self):
        self.table = {"IND": {"inflation": 0.0}, "USA": {"inflation": 3.0}}
        body = self.client.get("/api/compare?countries=IND,USA").json()
        usa = next(v for v in body["analytics"]["inflation"]["values"] if v["country"] == "USA")
        self.assertIsNone(usa["percentDifference"])
        self.assertEqual(usa["percentDifferenceNote"], "baseline_is_zero")
        self.assertEqual(usa["absoluteDifference"], 3.0)


@unittest.skipUnless(HAVE_FASTAPI, "fastapi/httpx not installed")
class CompareWithRealWorldBankServiceTests(unittest.TestCase):
    """The real World Bank service (cache, retries, stale fallback); only its HTTP call is mocked."""

    def setUp(self):
        wb.reset_cache()
        self.addCleanup(wb.reset_cache)
        self.client = TestClient(app)
        patch = mock.patch.object(cd, "load_metadata", return_value=all_metadata())
        patch.start()
        self.addCleanup(patch.stop)

    def test_one_indicator_timing_out_is_partial_not_fatal(self):
        fail = lambda iso3, code: iso3 == "USA" and code == wb.BY_KEY["pm25"].code
        with mock.patch.object(wb.requests, "get", side_effect=http_get(fail=fail)):
            r = self.client.get("/api/compare?countries=IND,USA,CHN")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["comparison"]["USA"]["pm25"]["status"], "error")
        self.assertEqual(body["comparison"]["IND"]["pm25"]["status"], "available")
        self.assertEqual(body["dataStatus"], "partial")

    def test_stale_values_are_served_and_flagged(self):
        with mock.patch.object(wb.requests, "get", side_effect=http_get({("USA", wb.BY_KEY["gdp"].code): 777.0})):
            self.client.get("/api/compare?countries=IND,USA")
        for key in list(wb._cache._items):
            if key.startswith("USA:"):
                wb._cache._items[key] = (-1e9, wb._cache._items[key][1])
        with mock.patch.object(wb.requests, "get", side_effect=http_get(fail=lambda iso3, code: iso3 == "USA")):
            body = self.client.get("/api/compare?countries=IND,USA").json()
        gdp = body["comparison"]["USA"]["gdp"]
        self.assertEqual((gdp["value"], gdp["stale"], gdp["status"]), (777.0, True, "available"))
        self.assertFalse(body["comparison"]["IND"]["gdp"]["stale"])
        self.assertTrue(any("stale" in w for w in body["warnings"]))

    def test_world_bank_down_is_502_and_recovers(self):
        with mock.patch.object(wb.requests, "get", side_effect=requests.ConnectionError("down")):
            self.assertEqual(self.client.get("/api/compare?countries=IND,USA").status_code, 502)
        with mock.patch.object(wb.requests, "get", side_effect=http_get()):
            self.assertEqual(self.client.get("/api/compare?countries=IND,USA").status_code, 200)

    def test_second_request_uses_the_cache(self):
        with mock.patch.object(wb.requests, "get", side_effect=http_get()) as get:
            self.client.get("/api/compare?countries=IND,USA")
            calls = get.call_count
            self.client.get("/api/compare?countries=USA,IND")
        self.assertEqual(get.call_count, calls)


@unittest.skipUnless(HAVE_FASTAPI, "fastapi/httpx not installed")
class IndicatorCatalogueApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_catalogue(self):
        with mock.patch.object(wb.requests, "get", side_effect=AssertionError("catalogue must not call the World Bank")):
            r = self.client.get("/api/compare/indicators")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["source"], "World Bank Open Data")
        self.assertEqual(body["count"], len(wb.INDICATORS))
        self.assertEqual([i["key"] for i in body["indicators"]], [i.key for i in wb.INDICATORS])
        gdp = next(i for i in body["indicators"] if i["key"] == "gdp")
        self.assertEqual(gdp["worldBankCode"], "NY.GDP.MKTP.CD")
        self.assertEqual(gdp["unit"], "current US$")
        self.assertEqual(gdp["category"], "economic")
        self.assertEqual(gdp["sdgs"], [8])
        self.assertEqual(gdp["direction"], "contextual")
        self.assertEqual(gdp["format"]["kind"], "currency")
        self.assertIn("axisLabel", gdp["chart"])
        self.assertEqual([c["id"] for c in body["categories"]], ["economic", "social", "environmental"])
        self.assertEqual([len(c["indicatorKeys"]) for c in body["categories"]], [6, 6, 4])

    def test_catalogue_is_not_swallowed_by_the_compare_route(self):
        self.assertIn("indicators", self.client.get("/api/compare/indicators").json())


if __name__ == "__main__":
    unittest.main()
