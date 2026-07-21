from __future__ import annotations

import pytest

from friday.src.config.settings import normalize_database_url


def test_normalize_supabase_postgresql_url_for_psycopg() -> None:
    url = "postgresql://user:password@example.com:5432/postgres"

    assert normalize_database_url(url) == (
        "postgresql+psycopg://user:password@example.com:5432/postgres"
    )


def test_normalize_legacy_postgres_scheme_for_psycopg() -> None:
    url = "postgres://user:password@example.com:5432/postgres"

    assert normalize_database_url(url).startswith("postgresql+psycopg://")


def test_normalize_keeps_psycopg_url() -> None:
    url = "postgresql+psycopg://user:password@example.com:5432/postgres"

    assert normalize_database_url(url) == url


def test_normalize_rejects_non_postgresql_database() -> None:
    with pytest.raises(ValueError, match="PostgreSQL"):
        normalize_database_url("mssql+pyodbc://example")
