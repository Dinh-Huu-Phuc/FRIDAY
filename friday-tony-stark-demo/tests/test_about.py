from __future__ import annotations

import unittest

from friday.about import get_friday_self_intro, load_self_intro_document, match_about_response


class FridayAboutTests(unittest.TestCase):
    def test_current_markdown_headings_load_triggers_and_responses(self) -> None:
        document = load_self_intro_document()

        self.assertIn("introduce yourself", document.triggers)
        self.assertIn("short", document.responses)
        self.assertIn("full", document.responses)
        self.assertTrue(document.important_rule)

    def test_introduce_yourself_returns_a_non_empty_prepared_response(self) -> None:
        response = get_friday_self_intro("voice")
        match = match_about_response("Please introduce yourself", response_type="voice")

        self.assertTrue(match.matched)
        self.assertTrue(response)
        self.assertEqual(match.response, response)
        self.assertIn("I am FRIDAY", response)


if __name__ == "__main__":
    unittest.main()
