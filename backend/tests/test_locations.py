"""Event location extraction: evidence-based, never guessed. No network."""
import unittest

from app.services import events as svc
from app.services import locations as loc
from tests.fixtures_countries import provider


def article(title, description="", source="UN News", source_country=None):
    return {"title": title, "description": description, "url": "https://example.com/" + str(abs(hash(title))),
            "published": "2026-11-08T12:00:00Z", "source": source, "domain": "example.com",
            "source_country": source_country, "topics": []}


class LocateTestBase(unittest.TestCase):
    def setUp(self):
        loc.set_country_provider(provider)
        self.addCleanup(loc.set_country_provider, None)

    def where(self, title, description="", **kw):
        return loc.locate(article(title, description, **kw))


class AssignmentTests(LocateTestBase):
    def test_place_word_gives_high_confidence(self):
        r = self.where("Airstrikes kill civilians in Sudan")
        self.assertEqual((r["countryId"], r["countryCode3"], r["countryName"]), ("SD", "SDN", "Sudan"))
        self.assertEqual(r["location"]["confidence"], "high")
        self.assertEqual(r["location"]["evidence"], [{"field": "title", "match": "Sudan", "rule": "place_word"}])
        self.assertEqual(r["region"], "Africa")
        self.assertEqual(r["locationMethod"], "gazetteer-title")

    def test_headline_prefix_is_high_confidence(self):
        r = self.where("Sudan: aid convoys blocked")
        self.assertEqual((r["countryId"], r["location"]["confidence"]), ("SD", "high"))
        self.assertEqual(r["location"]["evidence"][0]["rule"], "headline_prefix")

    def test_single_bare_mention_is_medium_confidence(self):
        r = self.where("Ukraine war pushes up grain prices")
        self.assertEqual((r["countryId"], r["location"]["confidence"]), ("UA", "medium"))
        self.assertEqual(r["location"]["evidence"][0]["rule"], "single_mention")

    def test_direction_words_before_the_name_still_count_as_a_place_word(self):
        r = self.where("Floods displace thousands in northern Nigeria")
        self.assertEqual((r["countryId"], r["location"]["confidence"]), ("NG", "high"))

    def test_alias_names(self):
        self.assertEqual(self.where("Fighting in the Democratic Republic of the Congo")["countryId"], "CD")
        self.assertEqual(self.where("Attack on a convoy in Gaza")["countryId"], "PS")
        self.assertEqual(self.where("US tariffs hit exporters")["countryId"], "US")

    def test_no_coordinates_are_invented(self):
        r = self.where("Fighting in Sudan")
        self.assertIsNone(r["latitude"])
        self.assertIsNone(r["longitude"])


class NoFalseAssociationTests(LocateTestBase):
    def test_publisher_country_is_never_used(self):
        r = self.where("Climate talks open", source="GDELT", source_country="France")
        self.assertIsNone(r["countryId"])
        self.assertIsNone(r["location"])

    def test_no_country_named_means_unmapped(self):
        r = self.where("Global food prices fall")
        self.assertIsNone(r["countryId"])
        self.assertIsNone(r["location"])

    def test_two_countries_without_a_place_word_are_ambiguous(self):
        r = self.where("US imposes sanctions on Iran")
        self.assertIsNone(r["countryId"])
        self.assertEqual(r["location"]["status"], "ambiguous")
        self.assertEqual(r["location"]["candidates"], ["IR", "US"])
        self.assertIsNone(r["location"]["confidence"])

    def test_one_place_word_among_several_countries_picks_that_one(self):
        r = self.where("Fighting in Sudan as the US urges talks")
        self.assertEqual((r["countryId"], r["location"]["confidence"]), ("SD", "high"))
        self.assertIn("US", r["location"]["candidates"])

    def test_two_place_words_are_ambiguous(self):
        r = self.where("Refugees cross from Sudan, aid arrives in Egypt and in Chad")
        self.assertIsNone(r["countryId"])
        self.assertEqual(r["location"]["status"], "ambiguous")

    def test_longest_name_wins(self):
        self.assertEqual(self.where("Famine warning in South Sudan")["countryId"], "SS")
        self.assertEqual(self.where("Quake hits Papua New Guinea")["countryId"], "PG")
        self.assertEqual(self.where("Oil spill off Equatorial Guinea")["countryId"], "GQ")

    def test_similar_names_do_not_match_inside_other_words(self):
        self.assertEqual(self.where("Coup attempt in Niger")["countryId"], "NE")
        self.assertEqual(self.where("Election day in Nigeria")["countryId"], "NG")
        self.assertEqual(self.where("Storm batters Dominica")["countryId"], "DM")
        self.assertEqual(self.where("Storm batters the Dominican Republic")["countryId"], "DO")

    def test_new_mexico_is_not_mexico(self):
        self.assertIsNone(self.where("Wildfire spreads in New Mexico")["countryId"])
        self.assertEqual(self.where("Wildfire spreads in Mexico")["countryId"], "MX")

    def test_words_that_are_also_names_need_a_place_word(self):
        self.assertIsNone(self.where("Michael Jordan donates to charity")["countryId"])
        self.assertIsNone(self.where("Thanksgiving turkey prices rise")["countryId"])
        self.assertEqual(self.where("Floods in Jordan")["countryId"], "JO")
        self.assertEqual(self.where("Drought in Chad")["countryId"], "TD")

    def test_georgia_congo_and_korea_are_never_assigned(self):
        for title in ("Vote counting in Georgia", "Fighting in Congo", "Talks on Korea"):
            r = self.where(title)
            self.assertIsNone(r["countryId"], title)
            self.assertEqual(r["location"]["status"], "ambiguous", title)
        self.assertEqual(self.where("Fighting in Congo")["location"]["candidates"], ["CD", "CG"])

    def test_demonyms_are_not_locations(self):
        self.assertIsNone(self.where("Russian missiles hit a hospital")["countryId"])

    def test_all_caps_text_is_not_analysed(self):
        self.assertIsNone(self.where("US AND IRAN HOLD TALKS")["countryId"])


class DescriptionTests(LocateTestBase):
    def test_description_with_one_place_word_country_is_used_when_title_names_none(self):
        r = self.where("UN chief warns of worsening hunger", "Millions face hunger in Sudan, officials said.")
        self.assertEqual((r["countryId"], r["locationMethod"]), ("SD", "gazetteer-description"))
        self.assertEqual(r["location"]["evidence"][0]["field"], "description")

    def test_bare_description_mention_is_not_enough(self):
        r = self.where("UN chief warns of worsening hunger", "Sudan was discussed.")
        self.assertIsNone(r["countryId"])
        self.assertEqual(r["location"]["status"], "ambiguous")

    def test_title_wins_over_description(self):
        r = self.where("Floods in Nigeria", "Neighbouring Niger in Niger also affected.")
        self.assertEqual(r["countryId"], "NG")

    def test_only_the_lead_of_the_description_is_read(self):
        r = self.where("Report released", ("x " * 300) + "in Sudan")
        self.assertIsNone(r["countryId"])


class RobustnessTests(unittest.TestCase):
    def tearDown(self):
        loc.set_country_provider(None)

    def test_provider_failure_leaves_event_unmapped_not_broken(self):
        def boom():
            raise RuntimeError("no network")
        loc.set_country_provider(boom)
        r = loc.locate(article("Fighting in Sudan"))
        self.assertIsNone(r["countryId"])

    def test_empty_country_list_leaves_event_unmapped(self):
        loc.set_country_provider(lambda: [])
        self.assertIsNone(loc.locate(article("Fighting in Sudan"))["countryId"])

    def test_missing_title_and_description(self):
        loc.set_country_provider(provider)
        self.assertIsNone(loc.locate({})["countryId"])


class PipelineIntegrationTests(LocateTestBase):
    def test_build_event_carries_the_location(self):
        event = svc.build_event(article("Airstrikes kill 120 civilians in Sudan"))
        self.assertEqual((event["countryId"], event["region"], event["countryName"]), ("SD", "Africa", "Sudan"))
        self.assertEqual(event["location"]["confidence"], "high")

    def test_country_and_confidence_filters(self):
        events = [
            svc.build_event(article("Fighting in Sudan")),
            svc.build_event(article("Ukraine war pushes up grain prices")),
            svc.build_event(article("US imposes sanctions on Iran")),
            svc.build_event(article("Global food prices fall")),
        ]
        self.assertEqual([e["countryId"] for e in svc.filter_events(events, country="SD")], ["SD"])
        self.assertEqual([e["countryId"] for e in svc.filter_events(events, country="UKR")], ["UA"])
        self.assertEqual(len(svc.filter_events(events, min_location_confidence="medium")), 2)
        high = svc.filter_events(events, min_location_confidence="high")
        self.assertEqual([e["countryId"] for e in high], ["SD"])  # unmapped events never pass a confidence filter

    def test_publisher_country_still_does_not_match_a_country_filter(self):
        events = [svc.build_event(article("Climate talks open", source="GDELT", source_country="France"))]
        self.assertEqual(svc.filter_events(events, country="FR"), [])


if __name__ == "__main__":
    unittest.main()
