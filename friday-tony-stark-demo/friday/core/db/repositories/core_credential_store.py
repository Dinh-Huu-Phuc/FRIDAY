from __future__ import annotations

from sqlalchemy import insert, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from friday.core.db.models import CoreAccessCredential
from friday.src.common.security import hash_password, verify_password
from friday.src.db.database import get_engine


class CredentialAlreadyConfiguredError(RuntimeError):
    pass


class CoreCredentialStore:
    def __init__(self, engine: Engine | None = None) -> None:
        self._engine = engine or get_engine()

    def is_configured(self) -> bool:
        statement = select(CoreAccessCredential.id).where(CoreAccessCredential.id == 1)
        with self._engine.connect() as connection:
            return connection.execute(statement).scalar_one_or_none() is not None

    def create(self, password: str) -> None:
        statement = insert(CoreAccessCredential).values(
            id=1,
            password_hash=hash_password(password),
        )
        try:
            with self._engine.begin() as connection:
                connection.execute(statement)
        except IntegrityError as exc:
            raise CredentialAlreadyConfiguredError(
                "The FRIDAY core password has already been configured."
            ) from exc

    def verify(self, password: str) -> bool:
        statement = select(CoreAccessCredential.password_hash).where(
            CoreAccessCredential.id == 1
        )
        with self._engine.connect() as connection:
            password_hash = connection.execute(statement).scalar_one_or_none()
        return bool(password_hash and verify_password(password, password_hash))
