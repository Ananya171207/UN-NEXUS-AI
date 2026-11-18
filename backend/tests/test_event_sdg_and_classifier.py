"""Event->SDG rules and the WHO classifier fix."""
import unittest

from app.services import event_sdg
from app.services.classifier import classify_event


class EventSdgTests(unittest.TestCase):
    def test_health_outbreak_maps_to_sdg3_with_evidence(self):
        m = event_sdg.map_event_to_sdgs("Cholera outbreak spreads in camps")
        self.assertEqual([x["sdg"] for x in m], [3])
        self.assertEqual((m[0]["confidence"], m[0]["method"], m[0]["aiGenerated"]), ("medium", "rules", False))
        self.assertIn("cholera", m[0]["reason"].lower())
        self.assertTrue(m[0]["evidence"])

    def test_multiple_goals_and_max_three(self):
        m = event_sdg.map_event_to_sdgs("Airstrikes hit school in Gaza as famine looms and refugees flee floods")
        self.assertLessEqual(len(m), 3)
        self.assertTrue({x["sdg"] for x in m} & {4, 16, 2})

    def test_description_only_evidence_is_low_confidence(self):
        m = event_sdg.map_event_to_sdgs("Report released", "Millions face hunger this winter.")
        self.assertEqual((m[0]["sdg"], m[0]["confidence"]), (2, "low"))

    def test_no_match_gives_empty_list_not_a_guess(self):
        self.assertEqual(event_sdg.map_event_to_sdgs("Council holds routine meeting"), [])

    def test_names_come_from_the_goal_list(self):
        self.assertEqual(event_sdg.map_event_to_sdgs("Drought hits farms")[0]["name"], "Climate Action")


class WhoFixTests(unittest.TestCase):
    def test_pronoun_who_is_not_health(self):
        self.assertNotEqual(classify_event("Women who lead peace talks win award").category, "Health")
        self.assertNotEqual(classify_event("Those who flee face hardship").category, "Health")

    def test_the_organization_still_counts(self):
        self.assertEqual(classify_event("WHO warns of rising measles cases").category, "Health")
        self.assertEqual(classify_event("World Health Organization opens a new clinic").category, "Health")


if __name__ == "__main__":
    unittest.main()
