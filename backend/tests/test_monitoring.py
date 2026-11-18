"""Regions, dashboard summary and map: one event list, consistent numbers. No network."""
import unittest

from app.services import locations as loc
from app.services import monitoring as mon
from app.services import regions as reg
from app.services import country_data as cd
from tests.fixtures_countries import COUNTRIES, provider
from tests.helpers import event


class Base(unittest.TestCase):
    def setUp(self):
        loc.set_country_provider(provider)
        self.addCleanup(loc.set_country_provider, None)

    def sample(self):
        return [
            event("Airstrikes kill more than 100 civilians in Sudan", n=1),       # Africa, critical
            event("Cholera outbreak spreads in Sudan", n=2),                      # Africa
            event("Floods displace thousands in Egypt", n=3),                     # Middle East
            event("Fighting in Kyiv wounds dozens", n=4),                         # Europe, city pin
            event("Ukraine war pushes up grain prices", n=5),                     # Europe, country only
            event("US imposes sanctions on Iran", n=6),                           # ambiguous -> none
            event("Global food prices fall", n=7),                                # none
            event("Wildfires burn across Australia", n=8),                        # Oceania
        ]


class RegionAssignmentTests(Base):
    def by_id(self, code):
        return next(c for c in COUNTRIES if c["id"] == code)

    def test_regions_and_middle_east(self):
        expect = {"SD": "Africa", "IN": "Asia", "UA": "Europe", "US": "North America", "MX": "North America",
                  "BR": "South America", "AU": "Oceania", "EG": "Middle East", "TR": "Middle East",
                  "IR": "Middle East", "IL": "Middle East", "PS": "Middle East", "JO": "Middle East"}
        for code, region in expect.items():
            self.assertEqual(reg.monitoring_region(self.by_id(code)), region, code)

    def test_middle_east_is_exclusive(self):
        egypt = self.by_id("EG")
        self.assertEqual(egypt["region"], "Africa")           # old 6-region field untouched
        self.assertEqual(reg.monitoring_region(egypt), "Middle East")

    def test_unknown_region_gives_none_not_a_guess(self):
        self.assertIsNone(reg.monitoring_region({"id": "XX", "region": None}))
        self.assertIsNone(reg.monitoring_region({"id": "XX", "region": "Antarctica"}))
        self.assertIsNone(reg.monitoring_region(None))

    def test_normalize_region(self):
        self.assertEqual(reg.normalize_region(" middle east "), "Middle East")
        self.assertIsNone(reg.normalize_region("Atlantis"))

    def test_event_carries_both_region_fields(self):
        e = event("Floods in Egypt")
        self.assertEqual((e["region"], e["monitoringRegion"]), ("Africa", "Middle East"))


class AggregateTests(Base):
    def test_counts_per_region(self):
        data = mon.aggregate_regions(self.sample())
        self.assertEqual([r["region"] for r in data["regions"]], list(reg.MONITORING_REGIONS))
        by = {r["region"]: r for r in data["regions"]}
        self.assertEqual(by["Africa"]["total"], 2)
        self.assertEqual(by["Middle East"]["total"], 1)
        self.assertEqual(by["Europe"]["total"], 2)
        self.assertEqual(by["Oceania"]["total"], 1)
        self.assertEqual((by["Asia"]["total"], by["North America"]["total"], by["South America"]["total"]), (0, 0, 0))

    def test_egypt_not_double_counted_in_africa(self):
        by = {r["region"]: r for r in mon.aggregate_regions([event("Floods in Egypt", n=1)])["regions"]}
        self.assertEqual((by["Middle East"]["total"], by["Africa"]["total"]), (1, 0))

    def test_severity_aggregation(self):
        by = {r["region"]: r for r in mon.aggregate_regions(self.sample())["regions"]}
        a = by["Africa"]
        self.assertEqual(a["critical"] + a["high"] + a["moderate"] + a["low"], a["total"])
        self.assertEqual(a["critical"], 1)
        self.assertEqual(a["highestSeverity"], "critical")
        self.assertIsNone(by["Asia"]["highestSeverity"])

    def test_country_counts_and_codes(self):
        by = {r["region"]: r for r in mon.aggregate_regions(self.sample())["regions"]}
        self.assertEqual((by["Africa"]["countryCount"], by["Africa"]["countryCodes"]), (1, ["SD"]))
        self.assertEqual(by["Europe"]["countryCodes"], ["UA"])

    def test_duplicates_are_counted_once(self):
        e = event("Fighting in Sudan", n=1)
        data = mon.aggregate_regions([e, dict(e), dict(e)])
        self.assertEqual(data["totals"]["events"], 1)
        self.assertEqual({r["region"]: r["total"] for r in data["regions"]}["Africa"], 1)

    def test_events_without_location_belong_to_no_region(self):
        data = mon.aggregate_regions(self.sample())
        self.assertEqual(data["totals"], {"events": 8, "withRegion": 6, "withoutRegion": 2, "regionsWithEvents": 4})
        self.assertEqual(sum(r["total"] for r in data["regions"]), 6)

    def test_empty_feed(self):
        data = mon.aggregate_regions([])
        self.assertEqual(len(data["regions"]), 7)
        self.assertTrue(all(r["total"] == 0 and r["topEvents"] == [] for r in data["regions"]))
        self.assertEqual(data["totals"]["events"], 0)

    def test_top_events_most_severe_first_max_three(self):
        evs = [event(f"Cholera outbreak in Sudan {i}", n=i) for i in range(5)] + [event("Airstrikes kill 200 civilians in Sudan", n=99)]
        top = {r["region"]: r for r in mon.aggregate_regions(evs)["regions"]}["Africa"]["topEvents"]
        self.assertEqual(len(top), 3)
        self.assertEqual(top[0]["severity"], "critical")

    def test_assignment_rule_is_documented(self):
        self.assertIn("reliably places", mon.aggregate_regions([])["assignmentRule"])


class SummaryTests(Base):
    def summary(self, events, **kw):
        return mon.build_summary(events, COUNTRIES, **kw)

    def test_cards(self):
        s = self.summary(self.sample())
        self.assertEqual(s["eventsShown"], 8)
        self.assertEqual(s["regionsWithEvents"], {"value": 4, "of": 7})
        self.assertEqual(s["countriesInView"], {"value": len(COUNTRIES), "of": len(COUNTRIES)})
        sev = s["severityBreakdown"]
        self.assertEqual(sum(sev.values()), 8)
        self.assertEqual(s["highCriticalEvents"], sev["critical"] + sev["high"])
        self.assertGreaterEqual(s["highCriticalEvents"], 1)
        self.assertEqual(s["unmappedEvents"], 2)
        self.assertEqual(sum(s["categoryBreakdown"].values()), 8)

    def test_unique_event_counting(self):
        e = event("Fighting in Sudan", n=1)
        self.assertEqual(self.summary([e, dict(e)])["eventsShown"], 1)

    def test_empty_feed(self):
        s = self.summary([])
        self.assertEqual((s["eventsShown"], s["highCriticalEvents"], s["unmappedEvents"]), (0, 0, 0))
        self.assertEqual(s["regionsWithEvents"], {"value": 0, "of": 7})
        self.assertEqual(s["severityBreakdown"], {"critical": 0, "high": 0, "moderate": 0, "low": 0})

    def test_countries_in_view_follows_region_and_country(self):
        me = sum(1 for c in COUNTRIES if reg.monitoring_region(c) == "Middle East")
        self.assertEqual(self.summary([], region="Middle East")["countriesInView"]["value"], me)
        self.assertEqual(self.summary([], country_id="SD")["countriesInView"]["value"], 1)
        self.assertEqual(self.summary([], country_id="ZZ")["countriesInView"]["value"], 0)

    def test_filtered_results_match_the_other_endpoints(self):
        # the same list feeds all three, so the numbers must agree
        from app.services import events as svc
        filtered = svc.filter_events(self.sample(), region="Africa")
        s, r, m = self.summary(filtered), mon.aggregate_regions(filtered), mon.build_map(filtered, COUNTRIES)
        self.assertEqual(s["eventsShown"], r["totals"]["events"])
        self.assertEqual(s["eventsShown"], m["totals"]["events"])
        self.assertEqual(s["eventsShown"], 2)
        self.assertEqual(s["regionsWithEvents"]["value"], r["totals"]["regionsWithEvents"])

    def test_warning_when_country_metadata_has_no_regions(self):
        limited = [{**c, "region": None} for c in COUNTRIES]
        s = mon.build_summary([], limited, region="Asia")
        self.assertTrue(s["warnings"])

    def test_definitions_are_returned(self):
        self.assertEqual(set(self.summary([])["definitions"]), {"eventsShown", "highCriticalEvents", "regionsWithEvents", "countriesInView"})


class MapTests(Base):
    def test_city_event_gets_a_marker_with_original_fields(self):
        m = mon.build_map(self.sample(), COUNTRIES)
        self.assertEqual(len(m["markers"]), 1)
        marker = m["markers"][0]
        self.assertEqual((marker["city"], marker["latitude"], marker["longitude"], marker["precision"]), ("Kyiv", 50.4501, 30.5234, "city"))
        self.assertEqual((marker["countryId"], marker["monitoringRegion"], marker["url"]), ("UA", "Europe", "https://example.com/4"))
        self.assertTrue(marker["evidence"])

    def test_country_level_events_never_get_event_markers(self):
        m = mon.build_map([event("Fighting in Sudan", n=1)], COUNTRIES)
        self.assertEqual(m["markers"], [])
        self.assertEqual(m["countryMarkers"][0]["countryId"], "SD")
        self.assertEqual(m["countryMarkers"][0]["coordinatesMean"], "country_centre")

    def test_country_marker_uses_dataset_position_and_counts(self):
        m = mon.build_map(self.sample(), COUNTRIES)
        sd = next(c for c in m["countryMarkers"] if c["countryId"] == "SD")
        self.assertEqual((sd["latitude"], sd["longitude"], sd["eventCount"], sd["highestSeverity"]), (15.0, 30.0, 2, "critical"))
        self.assertEqual(len(sd["eventIds"]), 2)

    def test_events_without_country_are_not_pinned_anywhere(self):
        m = mon.build_map([event("Global food prices fall", n=1), event("US imposes sanctions on Iran", n=2)], COUNTRIES)
        self.assertEqual((m["markers"], m["countryMarkers"]), ([], []))
        self.assertEqual(m["totals"]["eventsWithoutCountry"], 2)

    def test_missing_coordinates_are_counted_not_faked(self):
        m = mon.build_map(self.sample(), COUNTRIES)
        t = m["totals"]
        self.assertEqual((t["events"], t["eventMarkers"], t["eventsWithoutCountry"]), (8, 1, 2))
        self.assertEqual(t["eventsWithoutCoordinates"], 5)

    def test_invalid_coordinates_are_dropped(self):
        bad = event("Fighting in Kyiv", n=1)
        for lat, lon in ((95.0, 30.0), (50.0, 200.0), (float("nan"), 30.0)):
            m = mon.build_map([{**bad, "latitude": lat, "longitude": lon}], COUNTRIES)
            self.assertEqual(m["markers"], [])
            self.assertEqual(m["totals"]["invalidCoordinatesDropped"], 1)

    def test_country_without_position_is_not_pinned(self):
        no_pos = [{**c, "position": None} if c["id"] == "SD" else c for c in COUNTRIES]
        m = mon.build_map([event("Fighting in Sudan", n=1)], no_pos)
        self.assertEqual(m["countryMarkers"], [])
        self.assertEqual(m["totals"]["countriesWithoutPosition"], 1)

    def test_empty(self):
        m = mon.build_map([], COUNTRIES)
        self.assertEqual((m["markers"], m["countryMarkers"], m["totals"]["events"]), ([], [], 0))

    def test_duplicate_events_give_one_marker(self):
        e = event("Fighting in Kyiv", n=1)
        self.assertEqual(len(mon.build_map([e, dict(e)], COUNTRIES)["markers"]), 1)


if __name__ == "__main__":
    unittest.main()
