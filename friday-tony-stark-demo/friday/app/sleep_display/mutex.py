from __future__ import annotations

import ctypes
import os
from contextlib import contextmanager
from ctypes import wintypes
from typing import Iterator


WAIT_OBJECT_0 = 0
WAIT_ABANDONED = 0x00000080


@contextmanager
def named_mutex(name: str, *, timeout_ms: int = 15_000) -> Iterator[None]:
    if os.name != "nt":
        yield
        return

    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.ReleaseMutex.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

    handle = kernel32.CreateMutexW(None, False, f"Local\\{name}")
    if not handle:
        raise OSError("Could not create the FRIDAY lifecycle mutex.")
    acquired = False
    try:
        status = int(kernel32.WaitForSingleObject(handle, timeout_ms))
        acquired = status in {WAIT_OBJECT_0, WAIT_ABANDONED}
        if not acquired:
            raise TimeoutError(f"Timed out waiting for mutex {name}.")
        yield
    finally:
        if acquired:
            kernel32.ReleaseMutex(handle)
        kernel32.CloseHandle(handle)
