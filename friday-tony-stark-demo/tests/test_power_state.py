from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from friday.app.power import (
    PowerIntent,
    detect_power_intent,
    handle_power_message,
    initialize_power_state,
    match_power_intent,
)
from friday.app.power.name.aliases import PHRASE_SPECS
from friday.app.power.name.responses import (
    POWER_RESPONSES,
    _reset_response_rotation_for_tests,
    select_power_response,
)


class PowerStateTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_response_rotation_for_tests()

    def test_power_intents_are_exact(self) -> None:
        self.assertEqual(detect_power_intent("FRIDAY sleep!"), PowerIntent.SLEEP)
        self.assertEqual(detect_power_intent("Friday wake up"), PowerIntent.WAKE)
        self.assertEqual(detect_power_intent("Friday wakeup"), PowerIntent.WAKE)
        self.assertEqual(detect_power_intent("tell me about sleep"), PowerIntent.NONE)

    def test_every_allowlisted_phrase_is_recognized(self) -> None:
        for spec in PHRASE_SPECS:
            with self.subTest(phrase=spec.phrase):
                match = match_power_intent(spec.phrase)
                self.assertEqual(match.intent, spec.intent)
                self.assertEqual(match.trigger_id, spec.trigger_id)
                self.assertEqual(match.response_group, spec.response_group)

    def test_similar_unlisted_phrases_do_not_change_power_state(self) -> None:
        unlisted = (
            "please sleep",
            "tell Friday about sleep mode",
            "Friday wake up the computer",
            "Friday is online today",
            "goodbye",
            "are you there",
            "could you wake up Friday",
        )
        for phrase in unlisted:
            with self.subTest(phrase=phrase):
                self.assertEqual(detect_power_intent(phrase), PowerIntent.NONE)

    def test_responses_rotate_within_the_selected_group(self) -> None:
        first = select_power_response("wake_presence")
        second = select_power_response("wake_presence")

        self.assertEqual(first, "I'm here, Boss. What do you need help with?")
        self.assertNotEqual(first, second)
        self.assertIn(second, POWER_RESPONSES["wake_presence"])

    def test_sleep_blocks_work_until_wake(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_path = str(Path(directory) / "power-state.json")
            env = {
                "FRIDAY_POWER_STATE_PATH": state_path,
                "FRIDAY_INITIAL_STATE": "active",
            }
            with patch.dict(os.environ, env, clear=False):
                initialize_power_state(source="test")
                sleeping = handle_power_message("friday sleep", source="test")
                blocked = handle_power_message("open youtube", source="test")
                silent = handle_power_message(
                    "background speech",
                    source="microphone",
                    silent_when_sleeping=True,
                )
                awake = handle_power_message("friday wake up", source="test")

            self.assertTrue(sleeping.snapshot.sleeping)
            self.assertTrue(blocked.handled)
            self.assertTrue(silent.handled)
            self.assertEqual(silent.reply, "")
            self.assertEqual(awake.snapshot.state, "active")

    def test_presence_question_wakes_friday_with_matching_reply(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_path = str(Path(directory) / "power-state.json")
            env = {
                "FRIDAY_POWER_STATE_PATH": state_path,
                "FRIDAY_INITIAL_STATE": "sleeping",
            }
            with patch.dict(os.environ, env, clear=False):
                initialize_power_state(source="test")
                result = handle_power_message("FRIDAY, are you there?", source="test")

            self.assertEqual(result.snapshot.state, "active")
            self.assertEqual(result.reply, "I'm here, Boss. What do you need help with?")


if __name__ == "__main__":
    unittest.main()
