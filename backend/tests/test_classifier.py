import unittest

from app.services.classifier import (
    CATEGORIES,
    classify_event,
    normalize_category,
    normalize_severity,
)


class CategoryTests(unittest.TestCase):
    def test_conflict_headline_is_security(self):
        c = classify_event("Airstrikes hit residential area as fighting intensifies")
        self.assertEqual(c.category, "Security")

    def test_outbreak_is_health(self):
        c = classify_event("Cholera outbreak spreads across three provinces")
        self.assertEqual(c.category, "Health")

    def test_climate_talks_are_environmental(self):
        c = classify_event("Climate talks open with call for faster emissions cuts")
        self.assertEqual(c.category, "Environmental")

    def test_unrelated_text_is_other(self):
        self.assertEqual(classify_event("").category, "Other")
        self.assertEqual(classify_event("Weekly bulletin").category, "Other")

    def test_single_weak_description_hit_is_not_enough(self):
        c = classify_event("Weekly bulletin", "A note about aid.")
        self.assertEqual(c.category, "Other")

    def test_category_is_always_a_known_value(self):
        for title in ["x", "Famine in region", "GDP growth slows", "Election results"]:
            self.assertIn(classify_event(title).category, CATEGORIES)

    def test_topic_tags_count_as_text_evidence(self):
        c = classify_event("Update from the region", "", ["Peace and Security", "Violence"])
        self.assertEqual(c.category, "Security")


class SeverityTests(unittest.TestCase):
    def test_routine_observance_is_low_even_with_scary_words(self):
        c = classify_event("International Day of Remembrance for victims of genocide")
        self.assertEqual(c.severity, "low")

    def test_climate_headline_is_not_automatically_critical(self):
        for title in [
            "Climate change threatens food systems, report says",
            "UN climate summit opens in Baku",
            "Rising sea levels pose long-term risk to coastal cities",
        ]:
            self.assertIn(classify_event(title).severity, ("low", "moderate"), title)

    def test_conflict_word_alone_is_not_high(self):
        c = classify_event("Conflict resolution training held for mediators")
        self.assertEqual(c.severity, "moderate")  # "conflict" is a moderate term, never high

    def test_large_title_toll_is_critical(self):
        c = classify_event("Airstrikes kill more than 100 civilians in northern town")
        self.assertEqual(c.severity, "critical")
        c = classify_event("Over 250 killed in flooding")
        self.assertEqual(c.severity, "critical")

    def test_mid_size_toll_is_high(self):
        self.assertEqual(classify_event("Severe flooding kills 45 in river basin").severity, "high")
        self.assertEqual(classify_event("Dozens killed in market attack").severity, "high")

    def test_small_toll_is_moderate(self):
        self.assertEqual(classify_event("Three killed in road collapse").severity, "moderate")

    def test_unnumbered_killed_is_only_moderate(self):
        self.assertEqual(classify_event("Civilians killed, UN says").severity, "moderate")

    def test_genocide_in_news_title_is_critical(self):
        self.assertEqual(classify_event("UN investigators warn of genocide risk").severity, "critical")

    def test_famine_declared_is_critical_but_famine_risk_is_high(self):
        self.assertEqual(classify_event("Famine declared in northern region").severity, "critical")
        self.assertEqual(classify_event("Famine risk grows in the region").severity, "high")

    def test_evidence_only_in_description_is_demoted(self):
        c = classify_event(
            "Security Council discusses regional situation",
            "Heavy shelling and fighting were reported overnight.",
        )
        self.assertEqual(c.severity, "moderate")  # high terms in text -> one tier lower

    def test_genocide_only_in_description_is_at_most_high(self):
        c = classify_event("Council hears briefing", "A speaker referred to genocide.")
        self.assertEqual(c.severity, "high")

    def test_large_toll_only_in_description_is_at_most_high(self):
        c = classify_event("Briefing on the region", "More than 300 people were killed last week.")
        self.assertEqual(c.severity, "high")

    def test_empty_input_is_low(self):
        self.assertEqual(classify_event("").severity, "low")

    def test_years_are_not_mistaken_for_tolls(self):
        c = classify_event("Report on 2025 deaths data released")
        self.assertNotEqual(c.severity, "critical")
        self.assertEqual(classify_event("2024 fatalities figures published").severity, "low")

    def test_comma_formatted_tolls_still_count(self):
        self.assertEqual(classify_event("2,500 killed in earthquake").severity, "critical")


class RealHeadlineRegressionTests(unittest.TestCase):
    """Headlines seen in the first live UN News run."""

    def test_strikes_on_power_grid_is_high_severity(self):
        c = classify_event("Security Council LIVE: Strikes on Ukraine's power grid, as peace talks loom")
        self.assertEqual(c.severity, "high")
        self.assertTrue(any("strikes on" in s for s in c.signals))
        # Category is genuinely ambiguous (Security Council meeting about strikes):
        # Security and International relations are both defensible, so it is not pinned here.
        self.assertIn(c.category, ("Security", "International relations"))

    def test_plain_strikes_on_in_security_headline_is_security(self):
        self.assertEqual(classify_event("Strikes on hospitals condemned").category, "Security")

    def test_extreme_temperatures_report_is_environmental(self):
        c = classify_event("'Exceptional' extreme temperatures to continue into next year, UN report")
        self.assertEqual(c.category, "Environmental")
        self.assertIn(c.severity, ("low", "moderate"))

    def test_labour_strike_is_not_treated_as_an_attack(self):
        self.assertNotEqual(classify_event("Dockworkers strike over pay").severity, "high")


class TransparencyTests(unittest.TestCase):
    def test_signals_explain_the_decision(self):
        c = classify_event("Airstrikes kill 120 civilians")
        self.assertTrue(any("airstrike" in s for s in c.signals))
        self.assertTrue(any("toll 120" in s for s in c.signals))
        self.assertEqual(c.method, "rules")
        self.assertFalse(c.ai_generated)


class NormalizerTests(unittest.TestCase):
    def test_severity_aliases(self):
        self.assertEqual(normalize_severity("Medium"), "moderate")
        self.assertEqual(normalize_severity("HIGH"), "high")
        self.assertIsNone(normalize_severity("extreme"))

    def test_category_aliases_and_case(self):
        self.assertEqual(normalize_category("environmental"), "Environmental")
        self.assertEqual(normalize_category("Conflict / Security"), "Security")
        self.assertEqual(normalize_category("international relations"), "International relations")
        self.assertIsNone(normalize_category("sports"))


if __name__ == "__main__":
    unittest.main()
