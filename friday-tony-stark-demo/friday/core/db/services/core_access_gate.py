from __future__ import annotations

import secrets
import threading
from functools import lru_cache

from friday.core.db.repositories import CoreCredentialStore


MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128


class InvalidPasswordError(ValueError):
    pass


class PasswordConfirmationError(ValueError):
    pass


class CoreAccessGate:
    def __init__(self, store: CoreCredentialStore | None = None) -> None:
        self._store = store or CoreCredentialStore()
        self._sessions: set[str] = set()
        self._lock = threading.RLock()

    def is_configured(self) -> bool:
        return self._store.is_configured()

    def setup(self, password: str, confirmation: str) -> str:
        self._validate_new_password(password, confirmation)
        self._store.create(password)
        return self._issue_session()

    def unlock(self, password: str) -> str:
        if not self._store.verify(password):
            raise InvalidPasswordError("Incorrect password.")
        return self._issue_session()

    def is_unlocked(self, token: str | None) -> bool:
        if not token:
            return False
        with self._lock:
            return token in self._sessions

    def _issue_session(self) -> str:
        token = secrets.token_urlsafe(48)
        with self._lock:
            self._sessions.add(token)
        return token

    @staticmethod
    def _validate_new_password(password: str, confirmation: str) -> None:
        if not secrets.compare_digest(password, confirmation):
            raise PasswordConfirmationError("Passwords do not match.")
        if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
            raise InvalidPasswordError(
                f"Password must contain {MIN_PASSWORD_LENGTH} to "
                f"{MAX_PASSWORD_LENGTH} characters."
            )


@lru_cache
def get_core_access_gate() -> CoreAccessGate:
    return CoreAccessGate()
