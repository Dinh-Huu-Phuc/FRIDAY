from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from friday.app.power.window_manager import WindowRecord, WindowSleepManager


def _record(hwnd: int, pid: int, show_cmd: int = 3) -> WindowRecord:
    return WindowRecord(
        hwnd=hwnd,
        pid=pid,
        title=f"Window {hwnd}",
        class_name="TestWindow",
        placement={
            "flags": 0,
            "show_cmd": show_cmd,
            "min_position": {"x": 0, "y": 0},
            "max_position": {"x": 0, "y": 0},
            "normal_position": {"left": 10, "top": 20, "right": 800, "bottom": 600},
        },
    )


class FakeWindowBackend:
    def __init__(self) -> None:
        self.records = {101: _record(101, 1), 202: _record(202, 2, show_cmd=1)}
        self.minimized: list[int] = []
        self.restored: list[int] = []

    def list_windows(self) -> list[int]:
        return [101, 202, 303]

    def is_candidate(self, hwnd: int) -> bool:
        return hwnd in self.records

    def capture(self, hwnd: int) -> WindowRecord | None:
        return self.records.get(hwnd)

    def minimize(self, hwnd: int) -> bool:
        self.minimized.append(hwnd)
        return True

    def is_same_window(self, record: WindowRecord) -> bool:
        return record.hwnd in self.records and self.records[record.hwnd].pid == record.pid

    def restore(self, record: WindowRecord) -> bool:
        self.restored.append(record.hwnd)
        return True


class WindowSleepManagerTests(unittest.TestCase):
    def test_only_captured_windows_are_restored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            backend = FakeWindowBackend()
            snapshot = Path(directory) / "windows.json"
            manager = WindowSleepManager(
                backend=backend,
                snapshot_path=snapshot,
                transition_delay_seconds=0,
            )

            minimized = manager.minimize_all()
            restored = manager.restore_all()

            self.assertEqual(minimized.affected, 2)
            self.assertEqual(backend.minimized, [101, 202])
            self.assertEqual(restored.affected, 2)
            self.assertEqual(backend.restored, [202, 101])
            self.assertFalse(snapshot.exists())


if __name__ == "__main__":
    unittest.main()
