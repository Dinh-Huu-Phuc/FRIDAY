from __future__ import annotations

import unittest

from friday.about import get_friday_self_intro, load_self_intro_document, match_about_response


class FridayAboutTests(unittest.TestCase):
    def test_current_markdown_headings_load_triggers_and_responses(self) -> None:
        document = load_self_intro_document()

        self.assertIn("introduce yourself", document.triggers)
        self.assertIn("developer", document.trigger_groups)
        self.assertIn("birthday", document.trigger_groups)
        self.assertIn("capability", document.trigger_groups)
        self.assertIn("short", document.responses)
        self.assertIn("full", document.responses)
        self.assertIn("developer_en_short", document.responses)
        self.assertIn("birthday_vi_full", document.responses)
        self.assertIn("architecture_en_full", document.responses)
        self.assertTrue(document.important_rule)

    def test_introduce_yourself_returns_a_non_empty_prepared_response(self) -> None:
        response = get_friday_self_intro("voice")
        match = match_about_response("Please introduce yourself", response_type="voice")

        self.assertTrue(match.matched)
        self.assertTrue(response)
        self.assertEqual(match.response, response)
        self.assertIn("I am FRIDAY", response)

    def test_about_topics_select_their_own_markdown_response(self) -> None:
        cases = (
            ("Who created you?", "developer", "DINH HUU PHUC"),
            ("When is your birthday?", "birthday", "April 15, 2026"),
            ("What can you do?", "capability", "voice and text"),
            ("How are you built?", "architecture", "native desktop interface"),
        )

        for question, topic, expected in cases:
            with self.subTest(question=question):
                match = match_about_response(question, response_type="voice")
                self.assertTrue(match.matched)
                self.assertEqual(match.trigger, topic)
                self.assertIn(expected, match.response)

    def test_vietnamese_intro_uses_the_vietnamese_markdown_response(self) -> None:
        match = match_about_response(
            "Hãy giới thiệu bản thân",
            response_type="voice",
        )

        self.assertTrue(match.matched)
        self.assertEqual(match.trigger, "introduction")
        self.assertIn("Tôi là FRIDAY", match.response)
        self.assertIn("DINH HUU PHUC", match.response)

    def test_age_is_calculated_instead_of_hardcoded(self) -> None:
        match = match_about_response("How old are you?", response_type="voice")

        self.assertTrue(match.matched)
        self.assertEqual(match.trigger, "age")
        self.assertIn("April 15, 2026", match.response)
        self.assertIn("As of today", match.response)


if __name__ == "__main__":
    unittest.main()
