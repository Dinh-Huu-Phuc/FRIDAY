from __future__ import annotations

import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory

from friday.app.messenger import is_messenger_latest_request
from friday.app.messenger.bridge import MessengerExtensionBridge
from friday.app.messenger.chrome_profile import ChromeProfileLauncher
from friday.app.messenger.reader import parse_conversation_row
from friday.app.messenger.schemas import MessengerConversationPreview
from friday.app.messenger.reader import ChromeProfileMessengerReader
from friday.app.messenger.service import _configured_reader, check_latest_messenger_message


class FakeReader:
    def __init__(self, result: MessengerConversationPreview | None) -> None:
        self.result = result

    def read_latest(self) -> MessengerConversationPreview | None:
        return self.result


class MessengerIntentTests(unittest.TestCase):
    def test_detects_latest_message_requests(self) -> None:
        samples = (
            "FRIDAY, check my Messenger",
            "read my latest Messenger message",
            "do I have any unread Facebook Messenger messages",
            "check new Facebook messages",
        )
        for sample in samples:
            with self.subTest(sample=sample):
                self.assertTrue(is_messenger_latest_request(sample))

    def test_does_not_capture_general_facebook_search(self) -> None:
        self.assertFalse(is_messenger_latest_request("open Facebook and search for Tony Stark"))


class MessengerReaderTests(unittest.TestCase):
    def test_existing_chrome_profile_is_the_default_mode(self) -> None:
        with patch.dict("os.environ", {"FRIDAY_MESSENGER_MODE": ""}):
            self.assertIsInstance(_configured_reader(), ChromeProfileMessengerReader)

    def test_launcher_opens_messenger_in_configured_profile(self) -> None:
        chrome_path = Path(__file__)
        launcher = ChromeProfileLauncher(
            profile_directory="Default",
            chrome_path=chrome_path,
        )
        with patch("friday.app.messenger.chrome_profile.subprocess.Popen") as popen:
            launcher.open_messenger()
        command = popen.call_args.args[0]
        self.assertIn("--profile-directory=Default", command)
        self.assertEqual(command[-1], "https://www.messenger.com/")

    def test_parses_unread_conversation_row(self) -> None:
        result = parse_conversation_row(
            "Hoanh Hoang\nAre you free tonight?\n5m",
            labels=["Mark as read"],
            url="https://www.messenger.com/t/123",
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.sender, "Hoanh Hoang")
        self.assertEqual(result.preview, "Are you free tonight?")
        self.assertEqual(result.timestamp, "5m")
        self.assertTrue(result.unread)

    def test_formats_latest_message_for_voice(self) -> None:
        conversation = MessengerConversationPreview(
            sender="Pepper",
            preview="The meeting starts at nine.",
            timestamp="2m",
            unread=True,
        )
        result = check_latest_messenger_message(reader=FakeReader(conversation))
        self.assertTrue(result.ok)
        self.assertIn("new Messenger message from Pepper at 2m", result.message)
        self.assertIn("The meeting starts at nine.", result.message)

    def test_parses_vietnamese_unread_labels_and_time(self) -> None:
        result = parse_conversation_row(
            "Hoanh Hoang\nBạn có rảnh không?\n5 phút",
            labels=["Đánh dấu là đã đọc"],
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.preview, "Bạn có rảnh không?")
        self.assertEqual(result.timestamp, "5 phút")
        self.assertTrue(result.unread)

    def test_handles_empty_conversation_list(self) -> None:
        result = check_latest_messenger_message(reader=FakeReader(None))
        self.assertTrue(result.ok)
        self.assertIn("could not find", result.message)


class MessengerBridgeTests(unittest.TestCase):
    def test_round_trip_prefers_unread_conversation(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            bridge = MessengerExtensionBridge(
                command_path=root / "command.json",
                snapshot_path=root / "snapshot.json",
            )
            request_id = bridge.request_scan()
            command = bridge.pending_command()
            self.assertIsNotNone(command)
            assert command is not None
            self.assertEqual(command["request_id"], request_id)

            accepted = bridge.submit_snapshot(
                request_id=request_id,
                conversations=[
                    {"sender": "Pepper", "preview": "Seen message", "unread": False},
                    {"sender": "Rhodey", "preview": "New message", "unread": True},
                ],
                page_url="https://www.facebook.com/messages/",
            )
            self.assertTrue(accepted)
            latest = bridge.wait_for_latest(request_id, timeout_seconds=0.1)
            self.assertIsNotNone(latest)
            assert latest is not None
            self.assertEqual(latest.sender, "Rhodey")

    def test_rejects_snapshot_for_unknown_request(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            bridge = MessengerExtensionBridge(
                command_path=root / "command.json",
                snapshot_path=root / "snapshot.json",
            )
            bridge.request_scan()
            accepted = bridge.submit_snapshot(
                request_id="wrong-request",
                conversations=[{"sender": "Pepper", "preview": "Hello"}],
            )
            self.assertFalse(accepted)


if __name__ == "__main__":
    unittest.main()
