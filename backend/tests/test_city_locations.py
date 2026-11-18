"""City-level coordinates: only for a named city after a place word. No guessing."""
import unittest

from app.services import locations as loc
from tests.fixtures_countries import provider
from tests.helpers import article


class CityTests(unittest.TestCase):
    def setUp(self):
        loc.set_country_provider(provider)
        self.addCleanup(loc.set_country_provider, None)

    def where(self, title, description=""):
        return loc.locate(article(title, description))

    def test_city_after_place_word_gets_coordinates(self):
        r = self.where("Shelling in Kyiv wounds dozens")
        self.assertEqual((r["countryId"], r["latitude"], r["longitude"]), ("UA", 50.4501, 30.5234))
        self.assertEqual((r["location"]["precision"], r["location"]["city"], r["location"]["confidence"]), ("city", "Kyiv", "high"))
        self.assertEqual(r["location"]["evidence"][0]["rule"], "city_place_word")

    def test_bare_city_mention_gives_country_but_no_coordinates(self):
        r = self.where("Kyiv says talks are possible")
        self.assertEqual(r["countryId"], "UA")
        self.assertEqual(r["location"]["confidence"], "medium")
        self.assertIsNone(r["latitude"])
        self.assertEqual(r["location"]["precision"], "country")

    def test_country_only_event_has_no_coordinates(self):
        r = self.where("Fighting in Sudan")
        self.assertEqual((r["latitude"], r["longitude"], r["location"]["precision"]), (None, None, "country"))

    def test_cued_city_beats_an_uncued_actor_country(self):
        r = self.where("Strikes in Kyiv as Russia denies role")
        self.assertEqual((r["countryId"], r["location"]["city"], r["location"]["confidence"]), ("UA", "Kyiv", "high"))

    def test_city_and_its_own_country_give_one_pin(self):
        r = self.where("Floods in Khartoum, Sudan")
        self.assertEqual((r["countryId"], r["location"]["city"]), ("SD", "Khartoum"))

    def test_two_different_cities_in_one_country_get_no_pin(self):
        r = self.where("Fighting in Kyiv and in Kharkiv")
        self.assertEqual(r["countryId"], "UA")
        self.assertIsNone(r["latitude"])

    def test_cities_of_two_countries_are_ambiguous(self):
        r = self.where("Kyiv and Moscow exchange accusations")
        self.assertIsNone(r["countryId"])
        self.assertEqual(r["location"]["status"], "ambiguous")

    def test_gaza_city_is_not_double_counted_with_gaza(self):
        r = self.where("Hospital hit in Gaza City")
        self.assertEqual((r["countryId"], r["location"]["city"]), ("PS", "Gaza City"))
        self.assertEqual(len(r["location"]["evidence"]), 1)

    def test_ambiguous_city_names_are_not_in_the_list(self):
        for name in ("Tripoli", "Jerusalem", "Victoria", "Washington", "Paris"):
            self.assertNotIn(name, loc.CITIES)

    def test_every_city_coordinate_is_valid(self):
        for name, (code, lat, lon) in loc.CITIES.items():
            self.assertTrue(loc.valid_coordinates(lat, lon), name)

    def test_city_whose_country_is_unknown_is_ignored(self):
        loc.set_country_provider(lambda: [c for c in provider() if c["id"] != "UA"])
        self.assertIsNone(self.where("Shelling in Kyiv")["countryId"])

    def test_valid_coordinates(self):
        self.assertTrue(loc.valid_coordinates(0, 0))
        for bad in ((91, 0), (0, 181), (None, 5), ("x", 1), (float("nan"), 0), (float("inf"), 0)):
            self.assertFalse(loc.valid_coordinates(*bad), bad)


if __name__ == "__main__":
    unittest.main()
