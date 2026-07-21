# FRIDAY sleep and wake phrases

Power commands use an exact allowlist. Letter case, punctuation, and repeated
spaces are ignored, but extra or missing words will prevent activation.

## Sleep

- `FRIDAY sleep`
- `Sleep FRIDAY`
- `FRIDAY go to sleep`
- `FRIDAY, you can sleep now`
- `FRIDAY off`
- `FRIDAY stand by`
- `FRIDAY standby`
- `FRIDAY power down`
- `Okay FRIDAY, good night`
- `OK FRIDAY, good night`
- `Okay, thank you FRIDAY, goodbye`
- `OK, thank you FRIDAY, goodbye`
- `That will be all, FRIDAY`
- `You can rest now, FRIDAY`

## Wake

- `FRIDAY wake up`
- `FRIDAY wakeup`
- `Wake up FRIDAY`
- `Wakeup FRIDAY`
- `FRIDAY online`
- `FRIDAY come online`
- `FRIDAY resume`
- `FRIDAY come back`
- `FRIDAY, I need you`
- `Hey FRIDAY`
- `FRIDAY`
- `FRIDAY, are you there?`
- `Are you there, FRIDAY?`

For example, `FRIDAY, are you there?` is accepted, while `Are you there?` and
`FRIDAY, wake up the computer` are not power commands.

## Automatic sleep

FRIDAY automatically enters sleep mode after five minutes without a user
command. Commands received from Web UI and LiveKit reset the same shared timer.
Background speech is ignored while FRIDAY is already sleeping.

The timeout can be configured in the project `.env`:

```env
FRIDAY_AUTO_SLEEP_ENABLED=true
FRIDAY_AUTO_SLEEP_MINUTES=5
FRIDAY_AUTO_SLEEP_POLL_SECONDS=5
```
