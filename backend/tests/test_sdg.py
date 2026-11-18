"""Country SDG signals: real indicator data, no progress claims. No network."""
import unittest
from unittest import mock

from app.services import sdg
from app.services import worldbank as wb

COUNTRY = {"id": "SD", "code": "SDN", "name": "Sudan"}


def results(**overrides):
    """A full result set. overrides: key -> dict(status=..., value=..., year=...)"""
    out = {}
    for i in wb.INDICATORS:
        spec = overrides.get(i.key, {"status": "available", "value": 10.5, "year": "2023"})
        spec = dict(spec)
        status = spec.pop("status")
        out[i.key] = wb._result(i, status, name=f"WB name of {i.key}", **spec)
    return out


class SignalTests(unittest.TestCase):
    def build(self, **kw):
        only = kw.pop("only", None)
        return sdg.build_signals(COUNTRY, results(**kw), only=only, now_year=2026)

    def goal(self, data, number):
        return next(g for g in data["goals"] if g["sdg"] == number)

    def test_requested_goals_are_present(self):
        numbers = {g["sdg"] for g in self.build()["goals"]}
        self.assertTrue({1, 2, 3, 4, 6, 7, 8, 9, 11, 13} <= numbers)

    def test_signal_fields(self):
        s = self.goal(self.build(poverty_rate={"status": "available", "value": 12.3, "year": "2021"}), 1)["signals"][0]
        self.assertEqual((s["indicatorCode"], s["value"], s["year"], s["unit"], s["source"], s["availability"]),
                         ("SI.POV.DDAY", 12.3, "2021", "% of population", "World Bank Open Data", "available"))
        self.assertEqual((s["relation"], s["sdgIndicator"]), ("matches_sdg_indicator", "1.1.1"))
        self.assertTrue(s["explanation"])

    def test_multiple_indicators_for_one_goal(self):
        g = self.goal(self.build(), 8)
        self.assertEqual({s["indicatorKey"] for s in g["signals"]},
                         {"gdp", "gdp_per_capita", "gdp_growth", "inflation", "unemployment"})
        self.assertEqual((g["availableCount"], g["totalCount"]), (5, 5))

    def test_related_context_is_not_labelled_as_official(self):
        s = next(x for x in self.goal(self.build(), 7)["signals"])
        self.assertEqual((s["relation"], s["sdgIndicator"]), ("related_context", None))

    def test_missing_value_is_null_never_zero_or_invented(self):
        data = self.build(life_expectancy={"status": "no_data"})
        s = self.goal(data, 3)["signals"][0]
        self.assertEqual((s["availability"], s["value"], s["year"]), ("no_data", None, None))
        self.assertFalse(self.goal(data, 3)["hasData"])

    def test_error_and_pending_are_reported(self):
        data = self.build(drinking_water={"status": "error", "error": "timeout"}, pm25={"status": "pending"})
        self.assertEqual(self.goal(data, 6)["signals"][0]["availability"], "error")
        self.assertEqual(self.goal(data, 6)["signals"][0]["error"], "timeout")
        self.assertEqual(self.goal(data, 11)["signals"][0]["availability"], "pending")

    def test_outdated_flag_uses_threshold(self):
        data = self.build(poverty_rate={"status": "available", "value": 5, "year": "2015"},
                          undernourishment={"status": "available", "value": 5, "year": "2022"})
        self.assertTrue(self.goal(data, 1)["signals"][0]["outdated"])
        self.assertFalse(self.goal(data, 2)["signals"][0]["outdated"])

    def test_different_years_are_kept_per_indicator(self):
        data = self.build(life_expectancy={"status": "available", "value": 66, "year": "2022"},
                          school_enrollment={"status": "available", "value": 40, "year": "2018"})
        self.assertEqual(self.goal(data, 3)["signals"][0]["year"], "2022")
        self.assertEqual(self.goal(data, 4)["signals"][0]["year"], "2018")

    def test_stale_value_is_flagged(self):
        r = results()
        r["internet_use"] = {**r["internet_use"], "stale": True}
        data = sdg.build_signals(COUNTRY, r, now_year=2026)
        self.assertTrue(self.goal(data, 9)["signals"][0]["stale"])

    def test_goal_filter(self):
        data = self.build(only={3, 7})
        self.assertEqual([g["sdg"] for g in data["goals"]], [3, 7])
        self.assertEqual(data["goalsWithoutIndicators"], [])

    def test_goals_without_indicators_are_listed_not_scored(self):
        data = self.build()
        self.assertIn(5, data["goalsWithoutIndicators"])
        self.assertNotIn(1, data["goalsWithoutIndicators"])

    def test_no_progress_claims_and_not_ai(self):
        text = repr(self.build()).lower()
        for banned in ("on track", "off track", "on_track", "progress score", "percent_complete"):
            self.assertNotIn(banned, text.replace("not an sdg progress score", "").replace("does not say whether a country is on track", ""))
        data = self.build()
        self.assertFalse(data["aiGenerated"])
        self.assertEqual(data["dataType"], "indicator_values")
        self.assertIn("not combined into scores", data["methodology"])

    def test_population_has_no_goal(self):
        keys = {s["indicatorKey"] for g in self.build()["goals"] for s in g["signals"]}
        self.assertNotIn("population", keys)

    def test_all_unavailable(self):
        bad = {k: {**v, "status": "error"} for k, v in results().items()}
        self.assertTrue(sdg.all_unavailable(sdg.build_signals(COUNTRY, bad, now_year=2026)))
        self.assertFalse(sdg.all_unavailable(self.build()))

    def test_get_signals_uses_alpha3_and_world_bank(self):
        with mock.patch.object(wb, "fetch_country_indicators", return_value=results()) as fetch:
            data = sdg.get_signals(COUNTRY)
        fetch.assert_called_once_with("SDN")
        self.assertEqual(data["countryCode"], "SDN")

    def test_every_registry_indicator_has_an_explanation(self):
        for i in wb.INDICATORS:
            if i.sdgs:
                self.assertIn(i.key, sdg.INDICATOR_INFO)


if __name__ == "__main__":
    unittest.main()
