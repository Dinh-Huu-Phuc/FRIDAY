"""Allowlisted phrases that may change FRIDAY's power state."""

from __future__ import annotations

from dataclasses import dataclass

from ..types import PowerIntent


@dataclass(frozen=True, slots=True)
class PhraseSpec:
    phrase: str
    intent: PowerIntent
    trigger_id: str
    response_group: str


PHRASE_SPECS: tuple[PhraseSpec, ...] = (
    PhraseSpec("friday sleep", PowerIntent.SLEEP, "sleep_default", "sleep_direct"),
    PhraseSpec("sleep friday", PowerIntent.SLEEP, "sleep_reversed", "sleep_direct"),
    PhraseSpec("friday go to sleep", PowerIntent.SLEEP, "sleep_go", "sleep_direct"),
    PhraseSpec(
        "friday you can sleep now",
        PowerIntent.SLEEP,
        "sleep_permission",
        "sleep_direct",
    ),
    PhraseSpec("friday off", PowerIntent.SLEEP, "sleep_off", "sleep_standby"),
    PhraseSpec("friday stand by", PowerIntent.SLEEP, "sleep_stand_by", "sleep_standby"),
    PhraseSpec("friday standby", PowerIntent.SLEEP, "sleep_standby", "sleep_standby"),
    PhraseSpec("friday power down", PowerIntent.SLEEP, "sleep_power_down", "sleep_standby"),
    PhraseSpec(
        "okay friday good night",
        PowerIntent.SLEEP,
        "sleep_good_night",
        "sleep_goodbye",
    ),
    PhraseSpec(
        "ok friday good night",
        PowerIntent.SLEEP,
        "sleep_good_night_short",
        "sleep_goodbye",
    ),
    PhraseSpec(
        "okay thank you friday goodbye",
        PowerIntent.SLEEP,
        "sleep_thanks_goodbye",
        "sleep_thanks",
    ),
    PhraseSpec(
        "ok thank you friday goodbye",
        PowerIntent.SLEEP,
        "sleep_thanks_goodbye_short",
        "sleep_thanks",
    ),
    PhraseSpec(
        "that will be all friday",
        PowerIntent.SLEEP,
        "sleep_all_done",
        "sleep_thanks",
    ),
    PhraseSpec(
        "you can rest now friday",
        PowerIntent.SLEEP,
        "sleep_rest",
        "sleep_goodbye",
    ),
    PhraseSpec("friday wake up", PowerIntent.WAKE, "wake_default", "wake_time"),
    PhraseSpec("friday wakeup", PowerIntent.WAKE, "wake_compact", "wake_time"),
    PhraseSpec("wake up friday", PowerIntent.WAKE, "wake_reversed", "wake_time"),
    PhraseSpec("wakeup friday", PowerIntent.WAKE, "wake_compact_reversed", "wake_time"),
    PhraseSpec("friday online", PowerIntent.WAKE, "wake_online", "wake_online"),
    PhraseSpec(
        "friday come online",
        PowerIntent.WAKE,
        "wake_come_online",
        "wake_online",
    ),
    PhraseSpec("friday resume", PowerIntent.WAKE, "wake_resume", "wake_resume"),
    PhraseSpec("friday come back", PowerIntent.WAKE, "wake_return", "wake_resume"),
    PhraseSpec("friday i need you", PowerIntent.WAKE, "wake_needed", "wake_summon"),
    PhraseSpec("hey friday", PowerIntent.WAKE, "wake_hey", "wake_summon"),
    PhraseSpec("friday", PowerIntent.WAKE, "wake_name", "wake_summon"),
    PhraseSpec(
        "friday are you there",
        PowerIntent.WAKE,
        "wake_presence",
        "wake_presence",
    ),
    PhraseSpec(
        "are you there friday",
        PowerIntent.WAKE,
        "wake_presence_reversed",
        "wake_presence",
    ),
)
