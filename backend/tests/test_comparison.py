"""India vs World: comparison service tests.

Everything external is mocked: REST Countries (`country_data.load_metadata`) and the World Bank
(either `worldbank.fetch_country_indicators`, or the HTTP layer `worldbank.requests.get` when the
real fetching, caching and stale-data code should run). No test needs the network.
"""
import math
import re
import threading
import unittest
from unittest import mock

import requests

from app.services import comparison as cmp
from app.services import country_data as cd
from app.services import worldbank as wb
from tests.test_country_data import rest, result
from tests.test_worldbank import FakeResponse, wb_payload

DEFAULT_VALUE = 10.0


def all_metadata():
    raw = [
        rest("IN", "IND", "India", "Asia", "Southern Asia", "New Delhi", [20.0, 77.0]),
        rest("US", "USA", "United States", "Americas", "North America", "Washington, D.C.", [38.0, -97.0]),
        rest("CN", "CHN", "China", "Asia", "Eastern Asia", "Beijing", [35.0, 105.0]),
        rest("BR", "BRA", "Brazil", "Americas", "South America", "Brasilia", [-10.0, -55.0]),
        rest("DE", "DEU", "Germany", "Europe", "Western Europe", "Berlin", [51.0, 9.0]),
        rest("JP", "JPN", "Japan", "Asia", "Eastern Asia", "Tokyo", [36.0, 138.0]),
    ]
    return [cd.normalize_rest_country(r) for r in raw]


def fake_fetch(table=None):
    """Stand-in for worldbank.fetch_country_indicators.

    table[iso3][indicator_key] may be: a number, a (value, year) tuple, a status string
    ("no_data" / "error" / "pending"), or a dict of fields overriding a normal result.
    """
    table = table or {}

    def fetch(code, indicators=wb.INDICATORS):
        spec = table.get(code, {})
        out = {}
        for indicator in indicators:
            spec_value = spec.get(indicator.key, DEFAULT_VALUE)
            if isinstance(spec_value, str):
                out[indicator.key] = result(indicator.key, spec_value, error=f"{spec_value} for test")
            elif isinstance(spec_value, tuple):
                out[indicator.key] = result(indicator.key, value=spec_value[0], year=spec_value[1])
            elif isinstance(spec_value, dict):
                out[indicator.key] = {**result(indicator.key), **spec_value}
            else:
                out[indicator.key] = result(indicator.key, value=spec_value)
        return out

    return fetch


def http_get(table=None, *, default=5.0, year="2024", fail=None):
    """Stand-in for requests.get inside the World Bank service."""
    table = table or {}

    def get(url, **kwargs):
        match = re.search(r"/country/([A-Z]{3})/indicator/([^?/]+)", url)
        iso3, code = match.group(1), match.group(2)
        if fail and fail(iso3, code):
            raise requests.Timeout("Read timed out")
        value = table.get((iso3, code), default)
        rows = [] if value is None else [(year, value)]
        return FakeResponse(payload=wb_payload(code, rows))

    return get


class Base(unittest.TestCase):
    def setUp(self):
        wb.reset_cache()
        self.addCleanup(wb.reset_cache)
        patch = mock.patch.object(cd, "load_metadata", return_value=all_metadata())
        patch.start()
        self.addCleanup(patch.stop)

    def compare(self, countries, table=None, baseline=None):
        with mock.patch.object(wb, "fetch_country_indicators", side_effect=fake_fetch(table)):
            return cmp.compare(countries, baseline)


class TwoToFiveCountryTests(Base):
    def test_india_vs_usa(self):
        r = self.compare("IND,USA", {"IND": {"gdp": 100.0}, "USA": {"gdp": 300.0}})
        self.assertEqual(r["countries"], ["IND", "USA"])
        self.assertEqual(r["source"], "World Bank Open Data")
        self.assertEqual(set(r["comparison"]), {"IND", "USA"})
        self.assertEqual(r["comparison"]["IND"]["gdp"]["value"], 100.0)
        self.assertEqual(r["comparison"]["USA"]["gdp"]["value"], 300.0)
        usa = next(v for v in r["analytics"]["gdp"]["values"] if v["country"] == "USA")
        self.assertEqual(usa["absoluteDifference"], 200.0)
        self.assertEqual(usa["percentDifference"], 200.0)

    def test_india_vs_usa_vs_china(self):
        r = self.compare("IND,USA,CHN", {"IND": {"gdp": 100.0}, "USA": {"gdp": 300.0}, "CHN": {"gdp": 250.0}})
        self.assertEqual(r["countries"], ["IND", "USA", "CHN"])
        self.assertEqual(r["analytics"]["gdp"]["orderedByValue"], ["USA", "CHN", "IND"])
        self.assertEqual(r["analytics"]["gdp"]["highest"]["country"], "USA")
        self.assertEqual(r["analytics"]["gdp"]["lowest"]["country"], "IND")

    def test_five_countries(self):
        r = self.compare("IND,USA,CHN,BRA,DEU")
        self.assertEqual(len(r["countries"]), 5)
        for code in r["countries"]:
            self.assertEqual(len(r["comparison"][code]), len(wb.INDICATORS))
            self.assertEqual(r["countryMetadata"][code]["alpha3"], code)
        self.assertEqual(r["analytics"]["gdp"]["coverage"]["available"], 5)

    def test_alpha2_input_is_normalised_to_alpha3_keys(self):
        r = self.compare("in,us")
        self.assertEqual(r["countries"], ["IND", "USA"])
        self.assertEqual(set(r["comparison"]), {"IND", "USA"})
        self.assertEqual(r["countryMetadata"]["IND"]["alpha2"], "IN")

    def test_alpha3_input(self):
        self.assertEqual(self.compare("ind, usa ,bra")["countries"], ["IND", "USA", "BRA"])

    def test_mixed_alpha2_and_alpha3(self):
        self.assertEqual(self.compare("IN,USA,BR")["countries"], ["IND", "USA", "BRA"])

    def test_duplicates_are_removed_including_alpha2_alpha3_pairs(self):
        r = self.compare("IND,IN,usa,USA,US")
        self.assertEqual(r["countries"], ["IND", "USA"])

    def test_only_duplicates_leaves_too_few(self):
        for raw in ("IND,IND", "IN,IND"):
            with self.assertRaises(cmp.InvalidRequest, msg=raw):
                self.compare(raw)

    def test_too_few_countries(self):
        for raw in ("IND", "", None, " , ,"):
            with self.assertRaises(cmp.InvalidRequest, msg=repr(raw)):
                self.compare(raw)

    def test_too_many_countries(self):
        with self.assertRaises(cmp.InvalidRequest) as ctx:
            self.compare("IND,USA,CHN,BRA,DEU,JPN")
        self.assertIn("between 2 and 5", str(ctx.exception))

    def test_far_too_many_codes_are_rejected_before_any_lookup(self):
        with mock.patch.object(cd, "find_country") as find:
            with self.assertRaises(cmp.InvalidRequest):
                cmp.resolve_countries(",".join(f"A{i}" for i in range(cmp.MAX_RAW_CODES + 1)))
        find.assert_not_called()

    def test_invalid_codes_are_listed(self):
        with self.assertRaises(cmp.UnknownCountry) as ctx:
            self.compare("IND,ZZZ,12,usa")
        self.assertEqual(ctx.exception.codes, ["ZZZ", "12"])
        self.assertTrue(str(ctx.exception).startswith("Invalid country code"))

    def test_invalid_code_does_not_fetch_anything(self):
        with mock.patch.object(wb, "fetch_country_indicators") as fetch:
            with self.assertRaises(cmp.UnknownCountry):
                cmp.compare("IND,XXX")
        fetch.assert_not_called()


class BaselineTests(Base):
    def test_india_is_the_default_baseline_wherever_it_is_listed(self):
        r = self.compare("USA,CHN,IND")
        self.assertEqual(r["baseline"], {"country": "IND", "name": "India", "basis": "default_india"})
        self.assertTrue(r["countryMetadata"]["IND"]["isBaseline"])
        self.assertFalse(r["countryMetadata"]["USA"]["isBaseline"])

    def test_first_country_is_the_baseline_without_india_and_this_is_said(self):
        r = self.compare("USA,CHN")
        self.assertEqual(r["baseline"]["country"], "USA")
        self.assertEqual(r["baseline"]["basis"], "first_country")
        self.assertTrue(any("India (IND) is not among the selected" in w for w in r["warnings"]))

    def test_explicit_baseline_in_either_code_format(self):
        r = self.compare("IND,USA,CHN", baseline="cn")
        self.assertEqual((r["baseline"]["country"], r["baseline"]["basis"]), ("CHN", "requested"))

    def test_baseline_must_be_selected(self):
        with self.assertRaises(cmp.InvalidRequest):
            self.compare("IND,USA", baseline="BRA")

    def test_unknown_baseline(self):
        with self.assertRaises(cmp.UnknownCountry):
            self.compare("IND,USA", baseline="ZZZ")

    def test_baseline_row_has_no_difference_from_itself(self):
        r = self.compare("IND,USA")
        india = next(v for v in r["analytics"]["gdp"]["values"] if v["country"] == "IND")
        self.assertTrue(india["isBaseline"])
        self.assertIsNone(india["absoluteDifference"])
        self.assertIsNone(india["percentDifference"])


class DifferenceCalculationTests(Base):
    def row(self, r, key, code):
        return next(v for v in r["analytics"][key]["values"] if v["country"] == code)

    def test_percentage_difference_relative_to_baseline(self):
        r = self.compare("IND,USA,CHN", {"IND": {"gdp": 100.0}, "USA": {"gdp": 250.0}, "CHN": {"gdp": 50.0}})
        self.assertEqual(self.row(r, "gdp", "USA")["percentDifference"], 150.0)
        self.assertEqual(self.row(r, "gdp", "USA")["absoluteDifference"], 150.0)
        self.assertEqual(self.row(r, "gdp", "CHN")["percentDifference"], -50.0)
        self.assertEqual(self.row(r, "gdp", "CHN")["absoluteDifference"], -50.0)

    def test_percentage_difference_is_rounded_to_two_decimals(self):
        r = self.compare("IND,USA", {"IND": {"gdp": 3.0}, "USA": {"gdp": 4.0}})
        self.assertEqual(self.row(r, "gdp", "USA")["percentDifference"], 33.33)

    def test_zero_baseline_gives_no_percentage_but_keeps_the_absolute_difference(self):
        r = self.compare("IND,USA", {"IND": {"inflation": 0.0}, "USA": {"inflation": 3.2}})
        usa = self.row(r, "inflation", "USA")
        self.assertIsNone(usa["percentDifference"])
        self.assertEqual(usa["percentDifferenceNote"], "baseline_is_zero")
        self.assertEqual(usa["absoluteDifference"], 3.2)
        self.assertTrue(any("zero" in n for n in r["analytics"]["inflation"]["notes"]))

    def test_zero_value_is_a_real_value_not_missing(self):
        r = self.compare("IND,USA", {"IND": {"inflation": 4.0}, "USA": {"inflation": 0.0}})
        usa = self.row(r, "inflation", "USA")
        self.assertTrue(usa["usable"])
        self.assertEqual(usa["value"], 0.0)
        self.assertEqual(usa["percentDifference"], -100.0)
        self.assertEqual(r["analytics"]["inflation"]["lowest"]["country"], "USA")
        self.assertEqual(r["analytics"]["inflation"]["coverage"]["available"], 2)

    def test_negative_values(self):
        r = self.compare("IND,USA,CHN", {"IND": {"gdp_growth": -2.0}, "USA": {"gdp_growth": 1.0}, "CHN": {"gdp_growth": -4.0}})
        usa, chn = self.row(r, "gdp_growth", "USA"), self.row(r, "gdp_growth", "CHN")
        self.assertEqual(usa["absoluteDifference"], 3.0)
        self.assertEqual(usa["percentDifference"], 150.0)  # above the baseline, so positive, despite the negative baseline
        self.assertEqual(chn["absoluteDifference"], -2.0)
        self.assertEqual(chn["percentDifference"], -100.0)  # below the baseline, so negative
        self.assertEqual(r["analytics"]["gdp_growth"]["orderedByValue"], ["USA", "IND", "CHN"])

    def test_missing_baseline_gives_no_differences_and_says_why(self):
        r = self.compare("IND,USA,CHN", {"IND": {"pm25": "no_data"}, "USA": {"pm25": 8.0}, "CHN": {"pm25": 30.0}})
        usa = self.row(r, "pm25", "USA")
        self.assertIsNone(usa["absoluteDifference"])
        self.assertIsNone(usa["percentDifference"])
        self.assertEqual(usa["percentDifferenceNote"], "baseline_unavailable")
        self.assertFalse(r["analytics"]["pm25"]["baseline"]["available"])
        self.assertEqual(r["analytics"]["pm25"]["highest"]["country"], "CHN")  # ordering still works without a baseline

    def test_float_noise_is_trimmed(self):
        r = self.compare("IND,USA", {"IND": {"inflation": 0.1}, "USA": {"inflation": 0.3}})
        self.assertEqual(self.row(r, "inflation", "USA")["absoluteDifference"], 0.2)

    def test_percent_indicators_are_differenced_in_percentage_points(self):
        r = self.compare("IND,USA", {"IND": {"internet_use": 40.0}, "USA": {"internet_use": 90.0}})
        self.assertEqual(r["analytics"]["internet_use"]["differenceUnit"], "percentage points")
        self.assertEqual(self.row(r, "internet_use", "USA")["absoluteDifference"], 50.0)
        self.assertEqual(r["analytics"]["gdp"]["differenceUnit"], "current US$")


class OrderingTests(Base):
    def test_higher_is_better_ordering_and_ranks(self):
        r = self.compare("IND,USA,CHN", {"IND": {"life_expectancy": 70.0}, "USA": {"life_expectancy": 79.0}, "CHN": {"life_expectancy": 78.0}})
        a = r["analytics"]["life_expectancy"]
        self.assertEqual(a["direction"], "higher_is_better")
        self.assertEqual(a["orderedBestToWorst"], ["USA", "CHN", "IND"])
        ranks = {v["country"]: v["performanceRank"] for v in a["values"]}
        self.assertEqual(ranks, {"IND": 3, "USA": 1, "CHN": 2})
        usa = next(v for v in a["values"] if v["country"] == "USA")
        self.assertEqual((usa["comparedWithBaseline"], usa["performanceVsBaseline"]), ("higher", "better"))

    def test_lower_is_better_ordering(self):
        r = self.compare("IND,USA,CHN", {"IND": {"pm25": 50.0}, "USA": {"pm25": 8.0}, "CHN": {"pm25": 30.0}})
        a = r["analytics"]["pm25"]
        self.assertEqual(a["direction"], "lower_is_better")
        self.assertEqual(a["orderedBestToWorst"], ["USA", "CHN", "IND"])  # lowest first
        self.assertEqual(a["orderedByValue"], ["IND", "CHN", "USA"])  # highest value first, regardless of direction
        usa = next(v for v in a["values"] if v["country"] == "USA")
        self.assertEqual((usa["comparedWithBaseline"], usa["performanceVsBaseline"]), ("lower", "better"))

    def test_contextual_indicators_have_no_best_or_worst(self):
        r = self.compare("IND,USA", {"IND": {"population": 1.4e9}, "USA": {"population": 3.4e8}})
        a = r["analytics"]["population"]
        self.assertEqual(a["direction"], "contextual")
        self.assertIsNone(a["orderedBestToWorst"])
        for v in a["values"]:
            self.assertIsNone(v["performanceRank"])
            self.assertIsNone(v["performanceVsBaseline"])
        self.assertEqual(a["orderedByValue"], ["IND", "USA"])

    def test_ties_share_a_rank_and_are_flagged(self):
        r = self.compare("IND,USA,CHN", {"IND": {"life_expectancy": 75.0}, "USA": {"life_expectancy": 75.0}, "CHN": {"life_expectancy": 70.0}})
        a = r["analytics"]["life_expectancy"]
        ranks = {v["country"]: v["valueRank"] for v in a["values"]}
        self.assertEqual(ranks, {"IND": 1, "USA": 1, "CHN": 3})
        self.assertTrue(a["highest"]["tie"])
        self.assertFalse(a["lowest"]["tie"])

    def test_no_overall_ranking_or_composite_score_anywhere(self):
        r = self.compare("IND,USA,CHN")
        forbidden = ("score", "overall", "index", "composite")
        def walk(node, path=""):
            if isinstance(node, dict):
                for k, v in node.items():
                    self.assertFalse(any(f in k.lower() for f in forbidden), f"unexpected key {path}/{k}")
                    walk(v, f"{path}/{k}")
            elif isinstance(node, list):
                for item in node:
                    walk(item, path)
        walk({k: v for k, v in r.items() if k != "indicatorMetadata"})

    def test_single_usable_value_is_not_a_comparison(self):
        r = self.compare("IND,USA", {"IND": {"pm25": 50.0}, "USA": {"pm25": "no_data"}})
        a = r["analytics"]["pm25"]
        self.assertFalse(a["comparable"])
        self.assertIsNone(a["highest"])
        self.assertIsNone(a["lowest"])
        self.assertEqual(a["orderedByValue"], ["IND"])


class ReportingYearTests(Base):
    def test_every_value_keeps_its_own_year(self):
        r = self.compare("IND,USA", {"IND": {"gdp": (100.0, "2023")}, "USA": {"gdp": (300.0, "2025")}})
        self.assertEqual(r["comparison"]["IND"]["gdp"]["year"], "2023")
        self.assertEqual(r["comparison"]["USA"]["gdp"]["year"], "2025")
        self.assertEqual(r["analytics"]["gdp"]["years"], {"IND": "2023", "USA": "2025"})

    def test_differing_years_are_flagged(self):
        r = self.compare("IND,USA", {"IND": {"gdp": (100.0, "2023")}, "USA": {"gdp": (300.0, "2025")}})
        a = r["analytics"]["gdp"]
        self.assertTrue(a["yearsDiffer"])
        usa = next(v for v in a["values"] if v["country"] == "USA")
        self.assertEqual(usa["yearDifference"], 2)
        self.assertTrue(any("Reporting years differ for GDP" in w and "IND 2023" in w and "USA 2025" in w for w in r["warnings"]))
        self.assertTrue(any("years differ" in n for n in a["notes"]))

    def test_same_years_raise_no_flag(self):
        r = self.compare("IND,USA")
        self.assertFalse(r["analytics"]["gdp"]["yearsDiffer"])
        self.assertFalse(any("Reporting years differ" in w for w in r["warnings"]))
        self.assertEqual(r["dataStatus"], "complete")
        self.assertEqual(r["warnings"], [])

    def test_unavailable_values_do_not_count_as_a_year_difference(self):
        r = self.compare("IND,USA,CHN", {"CHN": {"gdp": "error"}})
        self.assertFalse(r["analytics"]["gdp"]["yearsDiffer"])


class DataQualityTests(Base):
    def test_missing_indicators_keep_their_status_and_are_reported(self):
        r = self.compare("IND,USA", {"USA": {"poverty_rate": "no_data", "pm25": "error", "forest_area": "pending"}})
        usa = r["comparison"]["USA"]
        self.assertEqual(usa["poverty_rate"]["status"], "no_data")
        self.assertEqual(usa["pm25"]["status"], "error")
        self.assertEqual(usa["forest_area"]["status"], "pending")
        for key in ("poverty_rate", "pm25", "forest_area"):
            self.assertIsNone(usa[key]["value"])
        q = r["dataQuality"]["USA"]
        self.assertEqual((q["available"], q["noData"], q["error"], q["pending"]), (13, 1, 1, 1))
        self.assertFalse(q["complete"])
        self.assertEqual({m["key"]: m["status"] for m in q["missing"]}, {"poverty_rate": "no_data", "pm25": "error", "forest_area": "pending"})
        self.assertTrue(r["dataQuality"]["IND"]["complete"])
        self.assertEqual(r["dataStatus"], "partial")

    def test_missing_values_are_kept_in_analytics_not_discarded(self):
        r = self.compare("IND,USA,CHN", {"USA": {"poverty_rate": "no_data"}})
        a = r["analytics"]["poverty_rate"]
        self.assertEqual([v["country"] for v in a["values"]], ["IND", "USA", "CHN"])
        usa = a["values"][1]
        self.assertFalse(usa["usable"])
        self.assertEqual(usa["reason"], "no_data")
        self.assertEqual(a["coverage"]["available"], 2)
        self.assertEqual(a["coverage"]["requested"], 3)
        self.assertAlmostEqual(a["coverage"]["ratio"], 0.6667, places=4)
        self.assertEqual(a["coverage"]["countriesMissing"][0]["country"], "USA")
        self.assertEqual(a["coverage"]["countriesWithData"], ["IND", "CHN"])

    def test_warnings_describe_each_kind_of_gap(self):
        r = self.compare("IND,USA", {"USA": {"poverty_rate": "no_data", "pm25": "error", "forest_area": "pending"}})
        text = " | ".join(r["warnings"])
        self.assertIn("USA: 1 indicator(s) could not be loaded (pm25)", text)
        self.assertIn("USA: 1 indicator(s) still loading (forest_area)", text)
        self.assertIn("USA: the World Bank has no value for poverty_rate", text)

    def test_one_failed_country_is_partial_not_fatal(self):
        everything_failed = {i.key: "error" for i in wb.INDICATORS}
        r = self.compare("IND,USA,CHN", {"CHN": everything_failed})
        self.assertEqual(r["dataQuality"]["CHN"]["available"], 0)
        self.assertEqual(r["dataQuality"]["CHN"]["coverage"], 0.0)
        self.assertTrue(any("CHN: no indicator could be loaded" in w for w in r["warnings"]))
        self.assertEqual(r["analytics"]["gdp"]["coverage"]["countriesWithData"], ["IND", "USA"])

    def test_everything_failing_everywhere_is_an_error(self):
        everything_failed = {i.key: "error" for i in wb.INDICATORS}
        with self.assertRaises(cmp.NoDataAvailable):
            self.compare("IND,USA", {"IND": everything_failed, "USA": everything_failed})

    def test_everything_pending_everywhere_is_an_error(self):
        pending = {i.key: "pending" for i in wb.INDICATORS}
        with self.assertRaises(cmp.NoDataAvailable):
            self.compare("IND,USA", {"IND": pending, "USA": pending})

    def test_missing_environmental_indicators_do_not_fail_the_comparison(self):
        env = {i.key: "error" for i in wb.INDICATORS if i.group == "environmental"}
        r = self.compare("IND,USA", {"USA": env})
        self.assertEqual(r["comparison"]["USA"]["gdp"]["status"], "available")
        self.assertEqual(r["dataQuality"]["USA"]["error"], 4)
        self.assertEqual(r["analytics"]["gdp"]["coverage"]["available"], 2)

    def test_indicator_the_data_service_did_not_return_is_reported(self):
        def short_fetch(code, indicators=wb.INDICATORS):
            out = fake_fetch()(code)
            del out["pm25"]
            return out
        with mock.patch.object(wb, "fetch_country_indicators", side_effect=short_fetch):
            r = cmp.compare("IND,USA")
        self.assertEqual(r["comparison"]["USA"]["pm25"]["status"], "error")
        self.assertIn("not returned", r["comparison"]["USA"]["pm25"]["error"])

    def test_unexpected_exception_for_one_country_is_contained(self):
        base = fake_fetch()
        def flaky(code, indicators=wb.INDICATORS):
            if code == "CHN":
                raise RuntimeError("boom")
            return base(code)
        with mock.patch.object(wb, "fetch_country_indicators", side_effect=flaky):
            r = cmp.compare("IND,USA,CHN")
        self.assertEqual(r["dataQuality"]["CHN"]["error"], len(wb.INDICATORS))
        self.assertIn("boom", r["comparison"]["CHN"]["gdp"]["error"])
        self.assertEqual(r["dataQuality"]["IND"]["available"], len(wb.INDICATORS))


class InvalidAndIncompatibleDataTests(Base):
    def test_unit_mismatch_is_never_compared(self):
        r = self.compare("IND,USA", {"IND": {"gdp": 100.0}, "USA": {"gdp": {"value": 300.0, "unit": "constant 2015 US$"}}})
        a = r["analytics"]["gdp"]
        usa = next(v for v in a["values"] if v["country"] == "USA")
        self.assertFalse(usa["usable"])
        self.assertEqual(usa["reason"], "unit_mismatch")
        self.assertIsNone(usa["absoluteDifference"])
        self.assertIsNone(usa["percentDifference"])
        self.assertFalse(a["comparable"])
        self.assertTrue(any("USA: GDP has an unusable value (unit_mismatch)" in w for w in r["warnings"]))
        self.assertEqual(r["comparison"]["USA"]["gdp"]["unit"], "constant 2015 US$")  # reported as received

    def test_non_numeric_nan_infinite_and_boolean_values_become_errors(self):
        for bad in ("12.5", float("nan"), float("inf"), True, None, [1]):
            with self.subTest(bad=bad):
                r = self.compare("IND,USA", {"USA": {"gdp": {"value": bad}}})
                entry = r["comparison"]["USA"]["gdp"]
                self.assertEqual(entry["status"], "error")
                self.assertIsNone(entry["value"])
                self.assertIn("invalid value", entry["error"])
                usa = next(v for v in r["analytics"]["gdp"]["values"] if v["country"] == "USA")
                self.assertFalse(usa["usable"])
                self.assertIsNone(usa["percentDifference"])
                self.assertFalse(r["analytics"]["gdp"]["comparable"])
                self.assertEqual(r["dataQuality"]["USA"]["error"], 1)

    def test_analyse_indicator_rejects_invalid_values_directly(self):
        gdp = wb.BY_KEY["gdp"]
        entries = {"IND": result("gdp", value=1.0), "USA": {**result("gdp"), "value": float("nan")}, "CHN": {**result("gdp"), "value": "3"}}
        a = cmp.analyse_indicator(gdp, entries, "IND")
        self.assertEqual([v["reason"] for v in a["values"]], [None, "invalid_value", "invalid_value"])
        self.assertEqual(a["coverage"]["countriesWithData"], ["IND"])

    def test_nan_never_leaks_into_results(self):
        r = self.compare("IND,USA", {"USA": {"gdp": {"value": float("nan")}}})
        self.assertIsNone(r["comparison"]["USA"]["gdp"]["value"])
        for v in r["analytics"]["gdp"]["values"]:
            for field in ("absoluteDifference", "percentDifference", "value"):
                if v[field] is not None:
                    self.assertTrue(math.isfinite(v[field]))

    def test_unknown_status_is_treated_as_unusable(self):
        r = self.compare("IND,USA", {"USA": {"gdp": {"status": "weird"}}})
        usa = next(v for v in r["analytics"]["gdp"]["values"] if v["country"] == "USA")
        self.assertFalse(usa["usable"])
        self.assertEqual(usa["reason"], "error")


class CountryMetadataTests(Base):
    def test_every_country_carries_identity_flag_region_and_coordinates(self):
        r = self.compare("IND,USA")
        india = r["countryMetadata"]["IND"]
        self.assertEqual((india["name"], india["alpha2"], india["alpha3"]), ("India", "IN", "IND"))
        self.assertEqual((india["id"], india["code"]), ("IN", "IND"))
        self.assertEqual((india["region"], india["subregion"], india["capital"]), ("Asia", "Southern Asia", "New Delhi"))
        self.assertEqual((india["latitude"], india["longitude"]), (20.0, 77.0))
        self.assertEqual(india["position"], [20.0, 77.0])
        self.assertEqual(india["flag"], "https://flags/IN.svg")
        self.assertTrue(india["flagEmoji"])
        self.assertEqual(r["countryMetadata"]["USA"]["capital"], "Washington, D.C.")

    def test_countries_come_back_in_request_order(self):
        r = self.compare("CHN,USA,IND")
        self.assertEqual(list(r["countryMetadata"]), ["CHN", "USA", "IND"])
        self.assertEqual(list(r["comparison"]), ["CHN", "USA", "IND"])


class IndicatorFieldTests(Base):
    def test_every_indicator_keeps_the_full_set_of_fields(self):
        r = self.compare("IND,USA", {"USA": {"gdp": {"stale": True}}})
        entry = r["comparison"]["USA"]["gdp"]
        for field in ("key", "value", "year", "label", "unit", "group", "source", "sourceCode", "indicatorName",
                      "status", "stale", "error", "sourceLastUpdated", "fetchedAt"):
            self.assertIn(field, entry)
        self.assertEqual(entry["key"], "gdp")
        self.assertEqual(entry["sourceCode"], wb.BY_KEY["gdp"].code)
        self.assertEqual(entry["unit"], wb.BY_KEY["gdp"].unit)
        self.assertEqual(entry["source"], "World Bank Open Data")
        self.assertTrue(entry["stale"])

    def test_all_registry_indicators_in_all_three_groups(self):
        r = self.compare("IND,USA")
        self.assertEqual(list(r["comparison"]["IND"]), [i.key for i in wb.INDICATORS])
        groups = {v["group"] for v in r["comparison"]["IND"].values()}
        self.assertEqual(groups, {"economic", "social", "environmental"})
        self.assertEqual(list(r["analytics"]), [i.key for i in wb.INDICATORS])


class BackwardCompatibilityTests(Base):
    LEGACY_KEYS = ("gdp_per_capita", "population", "life_expectancy", "co2_emissions", "school_enrollment")

    def test_legacy_indicator_keys_and_year_value_shape_are_preserved(self):
        r = self.compare("IND,USA", {"IND": {"population": (1.45e9, "2024")}})
        self.assertEqual(set(r) & {"source", "comparison"}, {"source", "comparison"})
        for code in ("IND", "USA"):
            for key in self.LEGACY_KEYS:
                self.assertIn(key, r["comparison"][code])
                self.assertIn("year", r["comparison"][code][key])
                self.assertIn("value", r["comparison"][code][key])
        self.assertEqual(r["comparison"]["IND"]["population"]["value"], 1.45e9)
        self.assertEqual(r["comparison"]["IND"]["population"]["year"], "2024")

    def test_legacy_error_contract(self):
        with self.assertRaises(cmp.InvalidRequest) as few:
            self.compare("IND")
        self.assertTrue(str(few.exception).startswith("Please provide between 2 and 5 countries"))
        with self.assertRaises(cmp.UnknownCountry) as bad:
            self.compare("IND,ZZZ")
        self.assertTrue(str(bad.exception).startswith("Invalid country code"))


class IndicatorCatalogueTests(unittest.TestCase):
    def setUp(self):
        self.catalogue = cmp.get_indicator_catalogue()

    def test_catalogue_is_the_registry_with_nothing_added_or_dropped(self):
        self.assertEqual(self.catalogue["count"], len(wb.INDICATORS))
        self.assertEqual([i["key"] for i in self.catalogue["indicators"]], [i.key for i in wb.INDICATORS])
        for item in self.catalogue["indicators"]:
            source = wb.BY_KEY[item["key"]]
            self.assertEqual(item["label"], source.label)
            self.assertEqual(item["unit"], source.unit)
            self.assertEqual(item["category"], source.group)
            self.assertEqual(item["worldBankCode"], source.code)
            self.assertEqual(item["sdgs"], list(source.sdgs))
            self.assertEqual(item["source"], "World Bank Open Data")

    def test_requested_indicators_are_all_present_by_category(self):
        by_cat = {c["id"]: c["indicatorKeys"] for c in self.catalogue["categories"]}
        self.assertEqual(by_cat["economic"], ["gdp", "gdp_per_capita", "gdp_growth", "population", "inflation", "unemployment"])
        self.assertEqual(by_cat["social"], ["life_expectancy", "school_enrollment", "poverty_rate", "undernourishment", "drinking_water", "internet_use"])
        self.assertEqual(by_cat["environmental"], ["co2_emissions", "renewable_electricity", "pm25", "forest_area"])

    def test_every_registry_indicator_has_an_explicit_reading(self):
        self.assertEqual(set(cmp.INTERPRETATION), set(wb.BY_KEY))

    def test_directions(self):
        direction = {i["key"]: i["direction"] for i in self.catalogue["indicators"]}
        for key in ("life_expectancy", "internet_use", "drinking_water", "renewable_electricity", "gdp_per_capita"):
            self.assertEqual(direction[key], "higher_is_better", key)
        for key in ("unemployment", "poverty_rate", "undernourishment", "co2_emissions", "pm25"):
            self.assertEqual(direction[key], "lower_is_better", key)
        for key in ("gdp", "population", "gdp_growth", "inflation", "forest_area"):
            self.assertEqual(direction[key], "contextual", key)

    def test_gdp_and_population_are_never_presented_as_better_or_worse(self):
        for key in ("gdp", "population"):
            self.assertEqual(cmp.interpretation_for(key).direction, cmp.CONTEXTUAL)

    def test_unknown_future_indicator_defaults_to_contextual(self):
        self.assertEqual(cmp.interpretation_for("brand_new").direction, cmp.CONTEXTUAL)

    def test_formatting_hints(self):
        items = {i["key"]: i for i in self.catalogue["indicators"]}
        self.assertEqual(items["gdp"]["format"], {"kind": "currency", "decimals": 0, "prefix": "$", "suffix": "", "compact": True})
        self.assertFalse(items["gdp_per_capita"]["format"]["compact"])
        self.assertEqual(items["population"]["format"]["kind"], "count")
        self.assertEqual(items["internet_use"]["format"]["kind"], "percent")
        self.assertEqual(items["internet_use"]["format"]["suffix"], "%")
        self.assertEqual(items["life_expectancy"]["format"]["kind"], "years")
        self.assertEqual(items["pm25"]["format"]["kind"], "concentration")
        self.assertTrue(items["gdp_growth"]["chart"]["canBeNegative"])
        self.assertFalse(items["life_expectancy"]["chart"]["canBeNegative"])
        self.assertIn("Life expectancy", items["life_expectancy"]["chart"]["axisLabel"])

    def test_catalogue_needs_no_network(self):
        with mock.patch.object(wb.requests, "get", side_effect=AssertionError("network used")):
            cmp.get_indicator_catalogue()

    def test_comparison_embeds_the_same_catalogue(self):
        wb.reset_cache()
        with mock.patch.object(cd, "load_metadata", return_value=all_metadata()), \
                mock.patch.object(wb, "fetch_country_indicators", side_effect=fake_fetch()):
            r = cmp.compare("IND,USA")
        self.assertEqual(r["indicatorMetadata"], self.catalogue["indicators"])


class WorldBankIntegrationTests(Base):
    """Runs the real World Bank service (cache, retries, stale fallback) with only HTTP mocked."""

    def test_one_indicator_timing_out_leaves_everything_else_intact(self):
        fail = lambda iso3, code: code == wb.BY_KEY["pm25"].code and iso3 == "USA"
        with mock.patch.object(wb.requests, "get", side_effect=http_get(fail=fail)):
            r = cmp.compare("IND,USA,CHN")
        self.assertEqual(r["comparison"]["USA"]["pm25"]["status"], "error")
        self.assertIn("Timeout", r["comparison"]["USA"]["pm25"]["error"])
        self.assertEqual(r["comparison"]["IND"]["pm25"]["status"], "available")
        self.assertEqual(r["comparison"]["CHN"]["pm25"]["status"], "available")
        self.assertEqual(r["comparison"]["USA"]["gdp"]["status"], "available")
        self.assertEqual(r["dataQuality"]["USA"]["error"], 1)
        self.assertEqual(r["dataStatus"], "partial")
        self.assertEqual(r["analytics"]["pm25"]["coverage"]["countriesWithData"], ["IND", "CHN"])

    def test_one_country_with_stale_cached_values(self):
        with mock.patch.object(wb.requests, "get", side_effect=http_get({("USA", wb.BY_KEY["gdp"].code): 777.0})):
            cmp.compare("IND,USA")
        for key in list(wb._cache._items):  # expire USA's cached values so a refresh is attempted
            if key.startswith("USA:"):
                wb._cache._items[key] = (-1e9, wb._cache._items[key][1])
        fail = lambda iso3, code: iso3 == "USA"
        with mock.patch.object(wb.requests, "get", side_effect=http_get(fail=fail)):
            r = cmp.compare("IND,USA")
        usa_gdp = r["comparison"]["USA"]["gdp"]
        self.assertEqual((usa_gdp["status"], usa_gdp["value"], usa_gdp["stale"]), ("available", 777.0, True))
        self.assertFalse(r["comparison"]["IND"]["gdp"]["stale"])
        self.assertEqual(r["dataQuality"]["USA"]["stale"], len(wb.INDICATORS))
        self.assertFalse(r["dataQuality"]["USA"]["complete"])
        self.assertEqual(r["dataStatus"], "partial")
        self.assertTrue(any("USA: showing stale cached values" in w for w in r["warnings"]))
        self.assertTrue(any("stale" in n for n in r["analytics"]["gdp"]["notes"]))
        usa_row = next(v for v in r["analytics"]["gdp"]["values"] if v["country"] == "USA")
        self.assertTrue(usa_row["stale"])
        self.assertTrue(usa_row["usable"])  # a stale value is still a value, and is flagged as such

    def test_missing_world_bank_value_is_no_data_not_zero(self):
        table = {("USA", wb.BY_KEY["poverty_rate"].code): None}
        with mock.patch.object(wb.requests, "get", side_effect=http_get(table)):
            r = cmp.compare("IND,USA")
        usa = r["comparison"]["USA"]["poverty_rate"]
        self.assertEqual(usa["status"], "no_data")
        self.assertIsNone(usa["value"])

    def test_world_bank_down_completely_is_a_clean_error(self):
        with mock.patch.object(wb.requests, "get", side_effect=requests.ConnectionError("down")):
            with self.assertRaises(cmp.NoDataAvailable):
                cmp.compare("IND,USA")

    def test_a_repeated_comparison_makes_no_new_world_bank_calls(self):
        with mock.patch.object(wb.requests, "get", side_effect=http_get()) as get:
            cmp.compare("IND,USA,CHN")
            first = get.call_count
            cmp.compare("CHN,IND,USA")
            cmp.compare("IND,USA")
        self.assertEqual(first, 3 * len(wb.INDICATORS))
        self.assertEqual(get.call_count, first)

    def test_overlapping_countries_reuse_the_profile_cache(self):
        with mock.patch.object(wb.requests, "get", side_effect=http_get()) as get:
            cmp.compare("IND,USA")
            before = get.call_count
            cmp.compare("IND,USA,BRA")  # only Brazil is new
        self.assertEqual(get.call_count - before, len(wb.INDICATORS))

    def test_errors_are_not_cached_so_the_next_comparison_recovers(self):
        fail = lambda iso3, code: code == wb.BY_KEY["pm25"].code
        with mock.patch.object(wb.requests, "get", side_effect=http_get(fail=fail)):
            first = cmp.compare("IND,USA")
        self.assertEqual(first["comparison"]["IND"]["pm25"]["status"], "error")
        with mock.patch.object(wb.requests, "get", side_effect=http_get()):
            second = cmp.compare("IND,USA")
        self.assertEqual(second["comparison"]["IND"]["pm25"]["status"], "available")
        self.assertEqual(second["dataStatus"], "complete")

    def test_default_reliability_settings_are_not_weakened(self):
        self.assertLessEqual(wb.settings.worldbank_timeout, 5)
        self.assertGreaterEqual(wb.settings.worldbank_retries, 2)
        self.assertLessEqual(wb.settings.worldbank_profile_deadline, 15)


class ConcurrencyTests(Base):
    def test_countries_are_fetched_concurrently_but_never_more_than_the_limit(self):
        lock, state = threading.Lock(), {"now": 0, "peak": 0}
        overlapped = threading.Event()  # set once two fetches have been in flight together
        base = fake_fetch()

        def slow(code, indicators=wb.INDICATORS):
            with lock:
                state["now"] += 1
                state["peak"] = max(state["peak"], state["now"])
                if state["peak"] >= 2:
                    overlapped.set()
            try:
                overlapped.wait(timeout=5)  # a sequential implementation would sit here for the full 5 s
                return base(code)
            finally:
                with lock:
                    state["now"] -= 1

        with mock.patch.object(wb, "fetch_country_indicators", side_effect=slow):
            r = cmp.compare("IND,USA,CHN,BRA,DEU")
        self.assertEqual(len(r["countries"]), 5)
        self.assertTrue(overlapped.is_set(), "countries were fetched one after another")
        self.assertLessEqual(state["peak"], cmp.MAX_COUNTRIES)

    def test_pending_indicators_from_the_deadline_are_reported(self):
        results = fake_fetch({"USA": {"pm25": "pending"}})
        with mock.patch.object(wb, "fetch_country_indicators", side_effect=results):
            r = cmp.compare("IND,USA")
        self.assertEqual(r["comparison"]["USA"]["pm25"]["status"], "pending")
        self.assertTrue(any("still loading (pm25)" in w for w in r["warnings"]))


class ParsingTests(unittest.TestCase):
    def test_parse_codes(self):
        self.assertEqual(cmp.parse_codes(" in, usa ,IN,,"), ["IN", "USA"])
        self.assertEqual(cmp.parse_codes(None), [])
        self.assertEqual(cmp.parse_codes(""), [])


if __name__ == "__main__":
    unittest.main()
